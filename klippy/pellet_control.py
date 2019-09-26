# Code for handling pellet feed control
#
# Copyright (C) 2019  Geoff Shannon <geoffpshannon@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

BUFFER_TIME = 3.0
DRAIN_TIME = 7.0
OFF_DELAY_TIME = 10.0
SPOOL_UP_TIME = 0.0


class PelletControl:
    def __init__(self, config):
        self.feeding = False
        self.last_movement_time = 0
        self.timer_handle = None

        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()

        self.base_buffer_time = config.getfloat("buffer_time", BUFFER_TIME, above=0.0)
        self.base_drain_time = config.getfloat("drain_time", DRAIN_TIME, above=0.0)
        self.off_delay_time = config.getfloat(
            "off_delay_time", OFF_DELAY_TIME, above=0.0
        )
        self.spool_up_time = config.getfloat("spool_up_time", SPOOL_UP_TIME, above=0.0)
        ppins = config.get_printer().lookup_object("pins")

        self._setup_blower(ppins, config)
        self._setup_pump(ppins, config)
        self._setup_sensor(config)
        self.mcu = self.blower.get_mcu()

    def sensor_callback(self, event_time, state):
        if self.feeding:
            if state:
                self._set_blower_low(event_time + self._buffer_time())
            else:
                self._set_blower_high(event_time + self._drain_time())

    def update_next_movement_time(self, print_time):
        self._start_feeding(print_time - self.spool_up_time)
        self._update_turn_off_time(print_time)

    def _setup_blower(self, ppins, config):
        self.blower = ppins.setup_pin("pwm", config.get("blower_pin"))
        self.blower.setup_max_duration(0.0)
        cycle_time = config.getfloat("cycle_time", 0.010, above=0.0)
        hardware_pwm = config.getboolean("hardware_pwm", False)
        self.blower.setup_cycle_time(cycle_time, hardware_pwm)
        self.blower.setup_start_value(0.0, 0.0)

    def _setup_pump(self, ppins, config):
        self.pump = ppins.setup_pin("digital_out", config.get("pump_pin"))
        self.pump.setup_start_value(0, 0)

    def _setup_sensor(self, config):
        self.sensor_pin = config.get("pellet_sensor_pin")
        buttons = self.printer.try_load_module(config, "buttons")
        buttons.register_buttons([self.sensor_pin], self.sensor_callback)

    def _setup_stop_timer(self, time):
        if not self.timer_handle:
            waketime = time + self.off_delay_time
            # Maybe use self.mcu.clock_to_print_time here?
            self.timer_handle = self.reactor.register_timer(
                lambda waketime: self._stop_feeding(
                    self.mcu.clock_to_print_time(waketime) + 0.5
                ),
                waketime
            )

    def _update_turn_off_time(self, time):
        if self.timer_handle:
            waketime = time + self.off_delay_time
            # Maybe use self.mcu.clock_to_print_time here?
            self.reactor.update_timer(self.timer_handle, waketime)

    def _start_feeding(self, time):
        if not self.feeding:
            self.feeding = True
            self._turn_on(time)
            self._setup_stop_timer(time)

    def _stop_feeding(self, time):
        if self.feeding:
            self.timer_handle = None
            self.feeding = False
            self._turn_off(time)

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
