#!/bin/sh

PORT="$1"

stty -F ${PORT} 1200 hup
stty -F ${PORT} 9600

sleep 3

make flash FLASH_DEVICE=/dev/ttyACM0
