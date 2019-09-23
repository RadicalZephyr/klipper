# Code for handling pellet feed control
#
# Copyright (C) 2019  Geoff Shannon <geoffpshannon@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging

BUFFER_TIME = 7000
DRAIN_TIME = 7000


class PelletControl:
    def __init__(self, config):
        self.feeding = False
        self.last_movement_time = 0

        self.printer = config.get_printer()

        self.base_buffer_time = config.getfloat("buffer_time", BUFFER_TIME, above=0.0)
        self.base_drain_time = config.getfloat("drain_time", DRAIN_TIME, above=0.0)

        ppins = config.get_printer().lookup_object('pins')

        self._setup_blower(ppins, config)
        self._setup_pump(ppins, config)
        self._setup_sensor(config)

    def sensor_callback(self, event_time, state):
        if self.feeding:
            if state:
                self._set_blower_low(event_time + self._buffer_time())
            else:
                self._set_blower_high(event_time + self._drain_time())

    def check_next_movement_time(self, print_time):
        logging.warn('NEXT MOVEMENT TIME: %d', print_time)

    def start_feeding(self, time):
        if not self.feeding:
            self.feeding = True
            self._turn_on(time)

    def stop_feeding(self, time):
        if self.feeding:
            self.feeding = False
            self._turn_off(time)

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

    def _setup_sensor(self, config):
        self.sensor_pin = config.get('pellet_sensor_pin')
        buttons = self.printer.try_load_module(config, "buttons")
        buttons.register_buttons([self.sensor_pin], self.sensor_callback)

    def _buffer_time(self):
        return self.base_buffer_time

    def _drain_time(self):
        return self.base_drain_time

    def _turn_on(self, time):
        self.blower.set_pwm(time, 1.0)
        self.pump.set_digital(time, 1)

    def _turn_off(self, time):
        self.blower.set_pwm(time, 0.0)
        self.pump.set_digital(time, 0)

    def _set_blower_high(self, time):
        self.blower.set_pwm(time, 1.0)

    def _set_blower_low(self, time):
        self.blower.set_pwm(time, 0.6)
