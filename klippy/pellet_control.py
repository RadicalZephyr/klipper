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

        self._setup_blower(ppins, config)
        self._setup_pump(ppins, config)
        self.pellet_sensor = ppins.setup_pin(
            'endstop', config.get('sensor_pin')
        )

    def _setup_blower(self, ppins, config):
        self.blower = ppins.setup_pin('pwm', config.get('blower_pin'))
        self.blower.setup_max_duration(0.)
        cycle_time = config.getfloat('cycle_time', 0.010, above=0.)
        hardware_pwm = config.getboolean('hardware_pwm', False)
        self.blower.setup_cycle_time(cycle_time, hardware_pwm)
        self.blower.setup_start_value(0.0, 0.0)

    def _setup_pump(self, ppins, config):
        self.pump = ppins.setup_pin('digital_out', config.get('pump_pin'))
        self.pump.setup_start_value(0, 0)
