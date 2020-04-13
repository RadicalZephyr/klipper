#!/bin/bash

set -e

PORT=/dev/serial/by-id/usb-Arduino__www.arduino.cc__Arduino_Due_Prog._Port_5573932363735191E0D2-if00

# Activate the bootloader
stty -F ${PORT} 1200 hup
stty -F ${PORT} 9600
sleep 3

make flash FLASH_DEVICE=/dev/serial/by-id/usb-03eb_6124-if00
