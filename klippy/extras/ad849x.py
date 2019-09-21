# Support AD849x series
#
# Copyright (C) 2019 Geoff Shannon <geoffpshannon@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
from bisect import bisect_left

RANGE_CHECK_COUNT = 4
REPORT_TIME = 0.300
SAMPLE_COUNT = 8
SAMPLE_TIME = 0.001


class AD849x:
    def __init__(self, config, lookup_table):
        self.linearity_correction = LinearityCorrection(lookup_table)
        self.printer = config.get_printer()

        self.adc_voltage = config.getfloat("adc_voltage", minval=0.0)
        self.voltage_offset = config.getfloat("voltage_offset", 0.0)

        ppins = config.get_printer().lookup_object("pins")
        self.mcu_adc = ppins.setup_pin("adc", config.get("sensor_pin"))
        self.mcu_adc.setup_adc_callback(REPORT_TIME, self.adc_callback)
        self.last_value = 0.0

    def setup_callback(self, temperature_callback):
        self.temperature_callback = temperature_callback

    def get_report_time_delta(self):
        return REPORT_TIME

    def adc_callback(self, read_time, read_value):
        measured_voltage = (read_value * self.adc_voltage) - self.voltage_offset
        temperature = self.linearity_correction[measured_voltage]

        self.temperature_callback(read_time + SAMPLE_COUNT * SAMPLE_TIME, temperature)

    def setup_minmax(self, min_temp, max_temp):
        self.mcu_adc.setup_minmax(
            SAMPLE_TIME,
            SAMPLE_COUNT,
            minval=0.0,
            maxval=99999999.9,
            range_check_count=RANGE_CHECK_COUNT,
        )


def load_config(config):
    # Register default sensors
    pheater = config.get_printer().lookup_object("heater")
    for sensor_type, params in [
        ("AD8494", AD8494),
        ("AD8495", AD8495),
        ("AD8496", AD8496),
        ("AD8497", AD8497),
    ]:
        func = lambda config, params=params: AD849x(config, params)
        pheater.add_sensor_factory(sensor_type, func)


class LinearityCorrection:
    def __init__(self, lookup_table):
        vs = self.voltages = [float(v) for (v, t) in lookup_table]
        ts = self.temperatures = [float(t) for (v, t) in lookup_table]
        intervals = zip(vs, vs[1:], ts, ts[1:])
        self.slopes = [(t2 - t1) / (v2 - v1) for v1, v2, t1, t2 in intervals]

    def __getitem__(self, voltage):
        idx = bisect_left(self.voltages, voltage)

        # The voltage value is amazingly actually in the array
        if self.voltages[idx] == voltage:
            return self.temperatures[idx]

        # This means the voltage is either smaller or larger than any
        # value in the array, so no interpolation can be done. Instead
        # use the simple 5mV/degree transfer function.
        elif idx <= 0 or idx >= len(self.voltages):
            return voltage / 0.005

        # Finally, interpolate between two values in the table
        else:
            i = idx - 1
            return self.temperatures[i] + (
                self.slopes[i] * (voltage - self.voltages[i])
            )


# These values taken from AN-1087 for AD849x series.  The format of
# the data is an in-order array of two-tuples where the first element
# in the tuple is the voltage, and the second is the measurement
# junction temperature that corresponds to that voltage.

# fmt: off
AD8494 = [
    (-0.714, -180),
    (-0.658, -160),
    (-0.594, -140),
    (-0.523, -120),
    (-0.446, -100),
    (-0.365,  -80),
    (-0.278,  -60),
    (-0.188,  -40),
    (-0.095,  -20),
    (0.002,     0),
    (0.100,    20),
    (0.125,    25),
    (0.201,    40),
    (0.303,    60),
    (0.406,    80),
    (0.511,   100),
    (0.617,   120),
    (0.723,   140),
    (0.829,   160),
    (0.937,   180),
    (1.044,   200),
    (1.151,   220),
    (1.259,   240),
    (1.366,   260),
    (1.473,   280),
    (1.580,   300),
    (1.687,   320),
    (1.794,   340),
    (1.901,   360),
    (2.008,   380),
    (2.114,   400),
    (2.221,   420),
    (2.328,   440),
    (2.435,   460),
    (2.542,   480),
    (2.650,   500),
    (2.759,   520),
    (2.868,   540),
    (2.979,   560),
    (3.090,   580),
    (3.203,   600),
    (3.316,   620),
    (3.431,   640),
    (3.548,   660),
    (3.666,   680),
    (3.786,   700),
    (3.906,   720),
    (4.029,   740),
    (4.152,   760),
    (4.276,   780),
    (4.401,   800),
    (4.526,   820),
    (4.650,   840),
    (4.774,   860),
    (4.897,   880),
    (5.018,   900),
    (5.138,   920),
    (5.257,   940),
    (5.374,   960),
    (5.490,   980),
    (5.606,  1000),
    (5.720,  1020),
    (5.833,  1040),
    (5.946,  1060),
    (6.058,  1080),
    (6.170,  1100),
    (6.282,  1120),
    (6.394,  1140),
    (6.505,  1160),
    (6.616,  1180),
    (6.727,  1200),
]

AD8495 = [
    (-0.786, -260),
    (-0.774, -240),
    (-0.751, -220),
    (-0.719, -200),
    (-0.677, -180),
    (-0.627, -160),
    (-0.569, -140),
    (-0.504, -120),
    (-0.432, -100),
    (-0.355,  -80),
    (-0.272,  -60),
    (-0.184,  -40),
    (-0.093,  -20),
    (0.003,     0),
    (0.100,    20),
    (0.125,    25),
    (0.200,    40),
    (0.301,    60),
    (0.402,    80),
    (0.504,   100),
    (0.605,   120),
    (0.705,   140),
    (0.803,   160),
    (0.901,   180),
    (0.999,   200),
    (1.097,   220),
    (1.196,   240),
    (1.295,   260),
    (1.396,   280),
    (1.497,   300),
    (1.599,   320),
    (1.701,   340),
    (1.803,   360),
    (1.906,   380),
    (2.010,   400),
    (2.113,   420),
    (2.217,   440),
    (2.321,   460),
    (2.425,   480),
    (2.529,   500),
    (2.634,   520),
    (2.738,   540),
    (2.843,   560),
    (2.947,   580),
    (3.051,   600),
    (3.155,   620),
    (3.259,   640),
    (3.362,   660),
    (3.465,   680),
    (3.568,   700),
    (3.670,   720),
    (3.772,   740),
    (3.874,   760),
    (3.975,   780),
    (4.076,   800),
    (4.176,   820),
    (4.275,   840),
    (4.374,   860),
    (4.473,   880),
    (4.571,   900),
    (4.669,   920),
    (4.766,   940),
    (4.863,   960),
    (4.959,   980),
    (5.055,  1000),
    (5.150,  1020),
    (5.245,  1040),
    (5.339,  1060),
    (5.432,  1080),
    (5.525,  1100),
    (5.617,  1120),
    (5.709,  1140),
    (5.800,  1160),
    (5.891,  1180),
    (5.980,  1200),
    (6.069,  1220),
    (6.158,  1240),
    (6.245,  1260),
    (6.332,  1280),
    (6.418,  1300),
    (6.503,  1320),
    (6.587,  1340),
    (6.671,  1360),
    (6.754,  1380)
]

AD8496 = [
    (-0.642, -180),
    (-0.590, -160),
    (-0.530, -140),
    (-0.464, -120),
    (-0.392, -100),
    (-0.315,  -80),
    (-0.235,  -60),
    (-0.150,  -40),
    (-0.063,  -20),
    (0.027,     0),
    (0.119,    20),
    (0.142,    25),
    (0.213,    40),
    (0.308,    60),
    (0.405,    80),
    (0.503,   100),
    (0.601,   120),
    (0.701,   140),
    (0.800,   160),
    (0.900,   180),
    (1.001,   200),
    (1.101,   220),
    (1.201,   240),
    (1.302,   260),
    (1.402,   280),
    (1.502,   300),
    (1.602,   320),
    (1.702,   340),
    (1.801,   360),
    (1.901,   380),
    (2.001,   400),
    (2.100,   420),
    (2.200,   440),
    (2.300,   460),
    (2.401,   480),
    (2.502,   500),
    (2.603,   520),
    (2.705,   540),
    (2.808,   560),
    (2.912,   580),
    (3.017,   600),
    (3.124,   620),
    (3.231,   640),
    (3.340,   660),
    (3.451,   680),
    (3.562,   700),
    (3.675,   720),
    (3.789,   740),
    (3.904,   760),
    (4.020,   780),
    (4.137,   800),
    (4.254,   820),
    (4.370,   840),
    (4.486,   860),
    (4.600,   880),
    (4.714,   900),
    (4.826,   920),
    (4.937,   940),
    (5.047,   960),
    (5.155,   980),
    (5.263,  1000),
    (5.369,  1020),
    (5.475,  1040),
    (5.581,  1060),
    (5.686,  1080),
    (5.790,  1100),
    (5.895,  1120),
    (5.999,  1140),
    (6.103,  1160),
    (6.207,  1180),
    (6.311,  1200),
]

AD8497 = [
    (-0.785, -260),
    (-0.773, -240),
    (-0.751, -220),
    (-0.718, -200),
    (-0.676, -180),
    (-0.626, -160),
    (-0.568, -140),
    (-0.503, -120),
    (-0.432, -100),
    (-0.354,  -80),
    (-0.271,  -60),
    (-0.184,  -40),
    (-0.092,  -20),
    (0.003,     0),
    (0.101,    20),
    (0.126,    25),
    (0.200,    40),
    (0.301,    60),
    (0.403,    80),
    (0.505,   100),
    (0.605,   120),
    (0.705,   140),
    (0.804,   160),
    (0.902,   180),
    (0.999,   200),
    (1.097,   220),
    (1.196,   240),
    (1.296,   260),
    (1.396,   280),
    (1.498,   300),
    (1.599,   320),
    (1.701,   340),
    (1.804,   360),
    (1.907,   380),
    (2.010,   400),
    (2.114,   420),
    (2.218,   440),
    (2.322,   460),
    (2.426,   480),
    (2.530,   500),
    (2.634,   520),
    (2.739,   540),
    (2.843,   560),
    (2.948,   580),
    (3.052,   600),
    (3.156,   620),
    (3.259,   640),
    (3.363,   660),
    (3.466,   680),
    (3.569,   700),
    (3.671,   720),
    (3.773,   740),
    (3.874,   760),
    (3.976,   780),
    (4.076,   800),
    (4.176,   820),
    (4.276,   840),
    (4.375,   860),
    (4.474,   880),
    (4.572,   900),
    (4.670,   920),
    (4.767,   940),
    (4.863,   960),
    (4.960,   980),
    (5.055,  1000),
    (5.151,  1020),
    (5.245,  1040),
    (5.339,  1060),
    (5.433,  1080),
    (5.526,  1100),
    (5.618,  1120),
    (5.710,  1140),
    (5.801,  1160),
    (5.891,  1180),
    (5.981,  1200),
    (6.070,  1220),
    (6.158,  1240),
    (6.246,  1260),
    (6.332,  1280),
    (6.418,  1300),
    (6.503,  1320),
    (6.588,  1340),
    (6.671,  1360),
    (6.754,  1380)
]
# fmt: on
