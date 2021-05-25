# Code for handling pellet feed control
#
# Copyright (C) 2019  Geoff Shannon <geoffpshannon@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import threading

BUFFER_TIME = 0.0
DEBOUNCE_TIME = 0.2
DRAIN_TIME = 7.0
OFF_DELAY_TIME = 0.0
PIN_MIN_TIME = 0.100
SPOOL_UP_TIME = 0.0


class PelletControl:
    def __init__(self, config):
        self.blower_set = False
        self.feeding = False
        self.last_pellet_sensor_state = 0
        self.last_pellet_sensor_time = None
        self.lock = threading.Lock()
        self.timer_handle = None

        self.printer = config.get_printer()
        self._setup_event_handlers(self.printer)

        self.reactor = self.printer.get_reactor()

        self.base_buffer_time = config.getfloat("buffer_time", BUFFER_TIME, above=0.0)
        self.debounce_time = config.getfloat("debounce_time", DEBOUNCE_TIME, above=0.0)
        self.base_drain_time = config.getfloat("drain_time", DRAIN_TIME, above=0.0)
        self.off_delay_time = config.getfloat(
            "off_delay_time", OFF_DELAY_TIME, above=0.0
        )
        self.spool_up_time = config.getfloat("spool_up_time", SPOOL_UP_TIME, above=0.0)

        ppins = self.printer.lookup_object("pins")

        blower = self._setup_blower(ppins, config)
        pump = self._setup_pump(ppins, config)

        self.actuator = PelletActuator(blower, pump)

        self._setup_sensor(config)
        self.mcu = blower.get_mcu()

    def handle_stopped(self, print_time):
        with self.lock:
            self._stop_feeding(print_time)

    def sensor_callback(self, event_time, state):
        with self.lock:
            logging.warn("pellet sensor state: %s", state)
            self.last_pellet_sensor_state = state

            if self.last_pellet_sensor_time:
                delta_t = event_time - self.last_pellet_sensor_time
                if delta_t >= self.debounce_time:
                    self.blower_set = False

            self.last_pellet_sensor_time = event_time
        print_time = self.mcu.estimated_print_time(event_time) + PIN_MIN_TIME
        logging.warn("sensor callback: estimated print time %.4f", print_time)

    def tick_callback(self, event_time):
        with self.lock:
            print_time = self.mcu.estimated_print_time(event_time) + PIN_MIN_TIME
            logging.warn("tick callback: estimated print time %.4f", print_time)

            if not self.feeding:
                self._stop_feeding(print_time)
                return self.reactor.NEVER

            if self.blower_set:
                return event_time + 1.0

            if self.last_pellet_sensor_state:
                self.actuator.set_blower_low(
                    print_time + self._buffer_time()
                )
            else:
                self.actuator.set_blower_high(
                    print_time + self._drain_time()
                )
            self.blower_set = True

        return event_time + 1.0

    def update_next_movement_time(self, print_time):
        with self.lock:
            logging.warn("update_next_movement_time called at: %.4f", print_time)
            self._start_feeding(print_time - self.spool_up_time)

    def _setup_blower(self, ppins, config):
        blower = ppins.setup_pin("pwm", config.get("blower_pin"))
        blower.setup_max_duration(0.0)
        cycle_time = config.getfloat("cycle_time", 0.010, above=0.0)
        hardware_pwm = config.getboolean("hardware_pwm", False)
        blower.setup_cycle_time(cycle_time, hardware_pwm)
        blower.setup_start_value(0.0, 0.0)
        return blower

    def _setup_event_handlers(self, printer):
        printer.register_event_handler(
            "gcode:request_restart", self.handle_stopped
        )
        printer.register_event_handler(
            "idle_timeout:idle", self.handle_stopped
        )
        printer.register_event_handler(
            "idle_timeout:ready", self.handle_stopped
        )

    def _setup_pump(self, ppins, config):
        pump = ppins.setup_pin("digital_out", config.get("pump_pin"))
        pump.setup_max_duration(0.0)
        pump.setup_start_value(0, 0)
        return pump

    def _setup_sensor(self, config):
        self.sensor_pin = config.get("pellet_sensor_pin")
        buttons = self.printer.try_load_module(config, "buttons")
        buttons.register_buttons([self.sensor_pin], self.sensor_callback)

    def _start_feeding(self, time):
        if not self.feeding:
            logging.warn("_start_feeding called with time: %.4f", time)
            self.timer_handle = self.reactor.register_timer(
                self.tick_callback, self.reactor.NOW
            )
            self.feeding = True
            self.actuator.turn_on(time)

    def _stop_feeding(self, time):
        if self.feeding:
            logging.warn("_stop_feeding called with time: %.4f", time)

            if self.timer_handle is not None:
                self.reactor.unregister_timer(self.timer_handle)
                self.timer_handle = None

            self.feeding = False
            self.last_pellet_sensor_state = 0

            self.actuator.turn_off(time)

    def _buffer_time(self):
        return self.base_buffer_time

    def _drain_time(self):
        return self.base_drain_time


class PelletActuator:
    def __init__(self, blower, pump):
        self.blower = blower
        self.pump = pump
        self.is_on = False
        self.last_blower_output = 0.0

    def renew_outputs(self, print_time):
        if self.is_on:
            self._set_blower(print_time, self.last_blower_output)
            self.pump.set_digital(print_time+0.05, 1)

    def turn_on(self, print_time):
        logging.warn("setting turn_on time: %.4f", print_time)
        self.is_on = True
        self.set_blower_high(print_time)
        self.pump.set_digital(print_time+0.05, 1)

    def turn_off(self, print_time):
        logging.warn("setting turn_off time: %.4f", print_time)
        self.is_on = False
        self.set_blower_off(print_time)
        self.pump.set_digital(print_time+0.05, 0)

    def set_blower_high(self, print_time):
        self._set_blower(print_time, 1.0)

    def set_blower_low(self, print_time):
        self._set_blower(print_time, 0.4)

    def set_blower_off(self, print_time):
        self._set_blower(self, print_time, 0.0)

    def _set_blower(self, print_time, level):
        logging.warn("setting blower to %d at time: %.4f", level, print_time)
        self.last_blower_output = level
        self.blower.set_pwm(print_time, level)
