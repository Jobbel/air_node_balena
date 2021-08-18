import config

# This class is the parent of all sensors and provides a two point calibration function


class SensorBase(object):
    def __init__(self):
        pass

    def calibrate(self, raw, cali):
        """
        :param raw: raw sensor value
        :param cali: calibration dict
        :return: calibrated sensor value
        """
        raw_range = cali["raw_high"] - cali["raw_low"]
        reference_range = cali["ref_high"] - cali["ref_low"]
        ret = (((raw - cali["raw_low"]) * reference_range) / raw_range) + cali["ref_low"]
        return round(ret, config.DIGIT_ACCURACY)
