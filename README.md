# Grrchen's Stream Controller
This is a small user space driver for the following Soomfon devices:
 - 5548:6670 355 35549
 - 1500:3001 Ellisys HOTSPOTEKUSB HID DEMO
 - 1500:3003 Ellisys HOTSPOTEKUSB HID DEMO

## Installation
### Debian
```sh
sudo apt update
sudo apt install python3-usb1
sudo cp udev/50-soomfon.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

**If the devices are not working as expected, try rebooting your computer.** (I read somewhere that the two commands may not be enough: `sudo udevadm control --reload-rules && sudo udevadm trigger`)

## Search for devices
The following command can be used to search for supported devices and display their serial numbers:
```bash
python3 stream_controller.py --find-devices
Found supported device 355 (21832:26224) with serial number 355499441494 on USB port 2
Found supported device HOTSPOTEKUSB (5376:12289) with serial number 0300D078472F on USB port 3
Found supported device HOTSPOTEKUSB (5376:12291) with serial number 4250D2782E07 on USB port 2
```
## Configuration
The user space driver searches in the current working directory for a folder named `config`. 

The configuration files must be located in this folder. For example, if the serial number is `4250D2782E07`, the configuration file in the `config` folder must be named `4250D2782E07.ini`.

Examples of configurations can be found in the `config` folder of this repository.

## Run the user space driver

```bash
python3 stream_controller.py
```
