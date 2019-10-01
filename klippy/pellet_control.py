# Code for handling pellet feed control
#
# Copyright (C) 2019  Geoff Shannon <geoffpshannon@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import threading

BUFFER_TIME = 0.0
DRAIN_TIME = 7.0
OFF_DELAY_TIME = 10.0
SPOOL_UP_TIME = 0.0


class PelletControl:
    def __init__(self, config):
        self.feeding = False
        self.lock = threading.Lock()
        self.timer_handle = None

        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()

        self.base_buffer_time = config.getfloat("buffer_time", BUFFER_TIME, above=0.0)
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

    def sensor_callback(self, event_time, state):
        with self.lock:
            if self.feeding:
                logging.warn("sensor_callback(%.4f, %s)", event_time, state)
                print_time = self.mcu.estimated_print_time(event_time)
                logging.warn("sensor_callback print_time: %.4f", print_time)
                if state:
                    self.actuator.set_blower_low(
                        print_time + self._buffer_time()
                    )
                else:
                    self.actuator.set_blower_high(
                        print_time + self._drain_time()
                    )

    def update_next_movement_time(self, print_time):
        with self.lock:
            # logging.warn("update_next_movement_time called at: %.4f", print_time)
            self._start_feeding(print_time - self.spool_up_time)
            self._update_turn_off_time(print_time)

    def _setup_blower(self, ppins, config):
        blower = ppins.setup_pin("pwm", config.get("blower_pin"))
        blower.setup_max_duration(0.0)
        cycle_time = config.getfloat("cycle_time", 0.010, above=0.0)
        hardware_pwm = config.getboolean("hardware_pwm", False)
        blower.setup_cycle_time(cycle_time, hardware_pwm)
        blower.setup_start_value(0.0, 0.0)
        return blower

    def _setup_pump(self, ppins, config):
        pump = ppins.setup_pin("digital_out", config.get("pump_pin"))
        pump.setup_start_value(0, 0)
        return pump

    def _setup_sensor(self, config):
        self.sensor_pin = config.get("pellet_sensor_pin")
        buttons = self.printer.try_load_module(config, "buttons")
        buttons.register_buttons([self.sensor_pin], self.sensor_callback)

    def _setup_stop_timer(self, print_time):
        return None
        if self.timer_handle is None:
            logging.warn(
                "_setup_stop_timer called with time: %.4f",
                print_time
            )
            print_time = print_time + self.off_delay_time
            logging.warn(
                "_setup_stop_timer calculated wake at print_time: %.4f",
                print_time
            )
            wake_time = self.mcu.print_time_to_clock(print_time)
            logging.warn(
                "_setup_stop_timer calculated wake at system_time: %.4f",
                wake_time
            )

            def wake_handler(event_time):
                with self.lock:
                    logging.warn(
                        "captured wake_handler turn off time as: %.4f",
                        print_time
                    )
                    self._stop_feeding(print_time + 10)
                    return self.reactor.NEVER

            self.timer_handle = self.reactor.register_timer(
                wake_handler, wake_time
            )

    def _update_turn_off_time(self, print_time):
        if self.timer_handle is not None:
            wake_time = print_time + self.off_delay_time
            self.reactor.update_timer(self.timer_handle, wake_time)

    def _start_feeding(self, time):
        if not self.feeding:
            logging.warn("_start_feeding called with time: %.4f", time)
            self.feeding = True
            self.actuator.turn_on(time)
            self._setup_stop_timer(time)

    def _stop_feeding(self, time):
        if self.feeding:
            logging.warn("_stop_feeding called with time: %.4f", time)
            if self.timer_handle is not None:
                self.reactor.unregister_timer(self.timer_handle)
                self.timer_handle = None

            self.feeding = False
            self.actuator.turn_off(time)

    def _buffer_time(self):
        return self.base_buffer_time

    def _drain_time(self):
        return self.base_drain_time


class PelletActuator:
    def __init__(self, blower, pump):
        self.blower = blower
        self.pump = pump

    def turn_on(self, print_time):
        logging.warn("setting turn_on time: %.4f", print_time)
        self.blower.set_pwm(print_time, 1.0)
        # self.pump.set_digital(print_time + 10, 1)

    def turn_off(self, print_time):
        logging.warn("setting turn_off time: %.4f", print_time)
        self.blower.set_pwm(print_time, 0.0)
        # self.pump.set_digital(print_time + 10, 0)

    def set_blower_high(self, print_time):
        logging.warn("setting blower_high time: %.4f", print_time)
        self.blower.set_pwm(print_time, 1.0)

    def set_blower_low(self, print_time):
        logging.warn("setting blower_low time: %.4f", print_time)
        self.blower.set_pwm(print_time, 0.6)
