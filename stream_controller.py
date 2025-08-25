# Standard library imports.
import threading
import subprocess
import os
import sys
import io
import time
import textwrap
import traceback
import logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.setLevel(logging.DEBUG)
#formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
formatter = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

import configparser

# Related third party imports.
import usb.core
import usb.util
import usb.backend.libusb1
from PIL import Image, ImageFont, ImageDraw

# Local application/library specific imports.

"""
set_state_path = os.path.expanduser("~/grrchen/git/pngtuber/set_state.py")

obs_logo = "~/grrchen/images/OBS_Studio_Logo.png"

keys = {"355499441494": (
    ("~/grrchen/git/pngtuber/default/eo_mo.png", "Default", ("python3", set_state_path, "0")),
    ("~/grrchen/git/pngtuber/controller/eo_mo.png", "Controller", ("python3", set_state_path, "2")),
    ("~/grrchen/git/pngtuber/keyboard/eo_mo.png", "Keyboard", ("python3", set_state_path, "1")),
    ("~/grrchen/git/pngtuber/weapon_gun/eo_mo.png", "Weapon", ("python3", set_state_path, "3")),
    ("~/grrchen/git/pngtuber/AFK.apng", "AFK", ("python3", set_state_path, "4")),
    (obs_logo, "Start", ("obs-cli", "scene", "switch", "Startscreen")),
    (obs_logo, "Pause", ("obs-cli", "scene", "switch", "Pause")),
    (obs_logo, "Ende", ("obs-cli", "scene", "switch", "Ende")),
    (obs_logo, "Gaming", ("obs-cli", "scene", "switch", "Gaming")),
    (obs_logo, "Coworking", ("obs-cli", "scene", "switch", "Coworking")),
    (obs_logo, "OnlyHands", ("obs-cli", "scene", "switch", "OnlyHands")),
    ("~/grrchen/git/pngtuber/default/eo_mo.png", "Stream Setup", ("/usr/bin/konsole", "--tabs-from-file", os.path.expanduser("~/grrchen/commands/stream_tabs"))),
    (obs_logo, "Start OBS", ("/opt/bin/obs",))),
"0300D078472F": (
    ("~/grrchen/git/pngtuber/default/eo_mo.png", "Default", ("python3", set_state_path, "0")),
    ("~/grrchen/git/pngtuber/controller/eo_mo.png", "Controller", ("python3", set_state_path, "2")),
    ("~/grrchen/git/pngtuber/keyboard/eo_mo.png", "Keyboard", ("python3", set_state_path, "1")),
    ("~/grrchen/git/pngtuber/weapon_gun/eo_mo.png", "Weapon", ("python3", set_state_path, "3")),
    ("~/grrchen/git/pngtuber/AFK.apng", "AFK", ("python3", set_state_path, "4")),
    (obs_logo, "Start", ("obs-cli", "scene", "switch", "Startscreen")),
    (obs_logo, "Pause", ("obs-cli", "scene", "switch", "Pause")),
    (obs_logo, "Ende", ("obs-cli", "scene", "switch", "Ende")),
    (obs_logo, "Gaming", ("obs-cli", "scene", "switch", "Gaming")),
    (obs_logo, "Coworking", ("obs-cli", "scene", "switch", "Coworking")),
    (obs_logo, "OnlyHands", ("obs-cli", "scene", "switch", "OnlyHands")),
    ("~/grrchen/git/pngtuber/default/eo_mo.png", "Stream Setup", ("/usr/bin/konsole", "--tabs-from-file", os.path.expanduser("~/grrchen/commands/stream_tabs"))),
    (obs_logo, "Start OBS", ("/opt/bin/obs",))
)}
"""


class Device(threading.Thread):
    _vendor_id = 0x5548
    _product_id = 0x6670

    _package_size: int = 512

    # vvvv - commands
    _cmd_prefix: bytes = b"\x43\x52\x54\x00\x00"
    _cmd_refresh: bytes = b"\x53\x54\x50\x00\x00"
    _cmd_set_key_image: bytes = b"\x42\x41\x54"
    _cmd_wake_screen: bytes = b"\x44\x49\x53\x00\x00"
    _cmd_cls: bytes = b"\x43\x4c\x45\x00\x00\x00\xff"
    _cmd_brightness: bytes = b"\x4c\x49\x47\x00\x00"
    # ^^^^

    _package_size_mapping: dict = {_cmd_set_key_image: 512}
    _img_rotation: int = 90
    _img_width: int = 85
    _img_height: int = 85
    _key_count: int = 15
    _keys: list = None
    _cmds: dict = None
    _read: bool = False

    def __init__(self, device, load_config: bool=True):
        self._device = device
        self._stop_event = threading.Event()
        super().__init__()
        if load_config:
            self._cmds = {}

    def load_config(self, file_path=None) -> None:
        serial_number = self.serial_number
        if file_path is None:
            file_path: str = os.path.join("config", f"{serial_number}.ini")
        if os.path.exists(file_path):
            self._config = config = configparser.ConfigParser()
            config.read(file_path)
            for i in range(self._key_count):
                key_name: str = f"key{i}"
                try:
                    key_config = config[key_name]
                except KeyError:
                    continue
                image_path: str = key_config.get("image", None)
                caption: str = key_config.get("caption", None)
                cmd: str = key_config.get("cmd", "")
                self.set_key_config(i, image_path, caption, cmd)
        else:
            logger.info(f"No configuration for device {serial_number} was found")

    @classmethod
    def set_key_mapping(cls, key_mapping):
        cls._KEY_MAPPING = key_mapping
        cls._KEY_MAPPING2 = KEY_MAPPING2 = {}

        for k, v in key_mapping.items():
            KEY_MAPPING2[v] = k

    @property
    def intf(self):
        # Get an endpoint instance
        cfg = self._device.get_active_configuration()
        return cfg[(0, 0)]

    @property
    def ep_out(self):
        return usb.util.find_descriptor(
            self.intf,
            # Match the first OUT endpoint
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_OUT)

    @property
    def ep_in(self):
        return usb.util.find_descriptor(
            self.intf,
            # Match the first OUT endpoint
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_IN)

    def run(self):
        self.wake_screen()
        self.set_brightness(100)
        self.clear_screen()
        self.refresh()
        self.load_config()
        self._set_keys()
        self._read()

    def set_keys(self, keys):
        self._keys = keys

    def _set_keys(self) -> None:
        if self._keys is None:
            return
        for i, entry in enumerate(self._keys):
            img, caption, cmd = entry
            self.set_key_image(i+1, os.path.expanduser(img), caption)
            self.refresh()

    @property
    def serial_number(self):
        return usb.util.get_string(self._device, self._device.iSerialNumber)

    def send_cmd(self, cmd, package_size=512):
        msg = self._cmd_prefix + cmd
        self.send(msg, package_size)

    def send(self, msg, package_size=512) -> None:
        if len(msg) < package_size:
            pad = ((package_size - len(msg)) * b"\x00")
            msg = msg + pad
        elif len(msg) > package_size:
            logger.error("Package size exceeded")
            return
        try:
            bytes_written = self._device.write(self.ep_out.bEndpointAddress, msg, 1000)
        except usb.core.USBTimeoutError as err:
            pass

    def send_bytes(self, data):
        chunk = data.read(self._package_size)
        # Loop until the chunk is empty
        while chunk:
            self.send(chunk, self._package_size)
            # Read the next chunk
            chunk = data.read(self._package_size)

    def set_brightness(self, brightness: int):
        self.send_cmd(self._cmd_brightness + brightness.to_bytes(1))

    def refresh(self):
        self.send_cmd(self._cmd_refresh)

    def wake_screen(self):
        self.send_cmd(self._cmd_wake_screen)

    def clear_screen(self):
        self.send_cmd(self._cmd_cls)

    def set_key_config(self, key: int, path: str, caption: str, cmd: str):
        logger.debug(f"{key}, {path}, {caption}, {cmd}")
        self._cmds[key] = cmd
        self.set_key_image(key, path, caption)
        self.refresh()

    def set_key_image(self, key, path, caption, font=ImageFont.load_default(14)):
        logger.debug(f"{key}, {path}, {caption}, {font}")
        # Image width and height
        width, height = self._img_width, self._img_height
        button_img = Image.new('RGB', (width, height), "black")
        draw = ImageDraw.Draw(button_img)
        draw.rectangle(((0, 0), (width, height)), fill="black")
        if path:
            path = os.path.expanduser(path)
            try:
                image = Image.open(path)
                size = (width, height)
                image.thumbnail(size, Image.LANCZOS)
                rgb_image = image.convert('RGB')
                button_img.paste(rgb_image, (0, 0))
            except FileNotFoundError:
                logger.error(f"{path} not found!")
        if caption:
            draw.text((width / 2, height / 2), caption, font=font, anchor="ms")
        roated_image = button_img.rotate(self._img_rotation)
        img_byte_arr = io.BytesIO()
        roated_image.save(img_byte_arr, "JPEG", subsampling=0, quality=100)
        img_data = img_byte_arr.getbuffer()
        cmd = self._cmd_set_key_image + img_data.nbytes.to_bytes(4) + self._KEY_MAPPING2.get(key, key).to_bytes(1)
        self.send_cmd(cmd, self._package_size_mapping.get(self._cmd_set_key_image, 512))
        img_byte_arr.seek(0)
        self.send_bytes(img_byte_arr)

    def key_pressed(self, key):
        if key in self._cmds:
            cmd = self._cmds[key]
        else:
            cmd = " ".join(self._keys[key-1][2])
        logger.info(f"executing cmd: {cmd}")
        subprocess.Popen(cmd, shell=True)

    def _read(self):
        while not self._stop_event.is_set():
            try:
                arr = self._device.read(self.ep_in.bEndpointAddress, self._package_size)
                logger.debug(arr)
                k = self._KEY_MAPPING.get(arr[9], arr[9])
                self.key_pressed(k)
                del arr
            except usb.core.USBTimeoutError:
                continue
            except Exception as err:
                tb = traceback.format_exc()
                logger.error(f"read error: {tb}")
                #self._running = False
        self.clear_screen()
        self.refresh()
        usb.util.dispose_resources(self._device)

    def stop(self):
        self._stop_event.set()


Device.set_key_mapping({
    13 : 1, 10 : 2, 7 : 3, 4 : 4,
    1 : 5, 14 : 6,  11 : 7,  8 : 8,
    5 : 9,  2 : 10, 15 : 11, 12 : 12,
    9 : 13, 6 : 14, 3 : 15
})


class Device2(Device):
    _vendor_id = 0x1500
    _product_id = 0x3001
    _package_size = 1024
    _img_rotation: int = -90
    _img_width: int = 70
    _img_height:int = 70
    _package_size_mapping = {Device._cmd_set_key_image: 1024}
    _key_count: int = 6


Device2.set_key_mapping({})

threads: list = []

DEVICE_CLS_MAPPING = {
    (0x5548, 0x6670): Device,
    (0x1500, 0x3001): Device2
}


def find_devices(vendor_id, product_id):
    logger.info(f"Search for devices with the vendor ID {vendor_id} and the product ID {product_id}")
    # find our device
    #backend = usb.backend.libusb1.get_backend(find_library=lambda x: "/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0")
    #devs = usb.core.find(idVendor=0x5548, idProduct=0x6670, find_all=1, backend=backend)
    devs = usb.core.find(idVendor=vendor_id, idProduct=product_id, find_all=1)
    for dev in devs:
        logger.info(f"Found supported device: {dev}")
        dev.reset()
        if dev.is_kernel_driver_active(0):
            try:
                dev.detach_kernel_driver(0)
            except usb.core.USBError as e:
                sys.exit("Could not detatch kernel driver from interface(0):", e)

        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        #dev.set_configuration()

        device_cls = DEVICE_CLS_MAPPING.get((dev.idVendor, dev.idProduct))
        device = device_cls(dev)
        logger.info(f"Serial number: {device.serial_number}")
        """"
        if device.serial_number in keys:
            device.set_keys(keys[device.serial_number])
        else:
            logger.error(f"Device with serial number {device.serial_number} was not found")
        """
        threads.append(device)
        device.start()


def main():
    supported_devices = ((0x5548, 0x6670), (0x1500, 0x3001))
    #supported_devices = ((0x1500, 0x3001),)
    #supported_devices = ((0x5548, 0x6670),)

    for supported_device in supported_devices:
        vendor_id, product_id = supported_device
        try:
            find_devices(vendor_id, product_id)
        except usb.core.USBError as err:
            tb = traceback.format_exc()
            logger.error(tb)

    # Wait for all threads to finish.
    for t in threads:
        t.join()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        for thread in threads:
            thread.stop()
