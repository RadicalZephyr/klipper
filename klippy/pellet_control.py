# Code for handling pellet feed control
#
# Copyright (C) 2019  Geoff Shannon <geoffpshannon@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.


class PelletControl:
    def __init__(self, config):
        self.printer = config.get_printer()

        self.base_buffer_time = config.getfloat("buffer_time", above=0.0)
        self.base_clear_time = config.getfloat("clear_time", above=0.0)

        ppins = config.get_printer().lookup_object('pins')

        self.pellet_sensor = ppins.setup_pin('endstop', config.get('sensor_pin'))
        self.blower = ppins.setup_pin('pwm', config.get('blower_pin'))
        self.pump = ppins.setup_pin('digital_out', config.get('pump_pin'))
