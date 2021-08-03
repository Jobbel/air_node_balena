import Adafruit_ADS1x15
import prt


class ADCHandler(object):

    def __init__(self, config):
        self._config = config
        self._digit_accuracy = self._config["digit_accuracy"]
        self.adc = Adafruit_ADS1x15.ADS1115(address=self._config["adc_address_a"])
        self.ADCGain = 4
        self.mVGain = 0.03125

        # Gain table
        #  - 2/3 = +/-6.144V
        #  -   1 = +/-4.096V
        #  -   2 = +/-2.048V
        #  -   4 = +/-1.024V
        #  -   8 = +/-0.512V
        #  -  16 = +/-0.256V
        # See table 3 in the ADS1015/ADS1115 datasheet for more info on gain.


    def rawADCtoPPB(self, w_raw, a_raw, cali, n):
        """uses raw working and auxiliary adc values as well as a calibration dict to calculate ppb values"""
        w = w_raw * self.mVGain
        a = a_raw * self.mVGain
        return ((w - cali['w0']) - (n * (a - cali['a0']))) / cali['sens']

    def getData(self, other_sensor_data):
        temp = other_sensor_data["sht_temp"]
        # Calculate n factors from the temperature
        n_co = (-1 if temp < 25 else -3.8)
        n_no = (1.04 if temp < 15 else (1.82 if temp < 25 else 2))
        n_no2 = (0.76 if temp < 15 else (0.68 if temp < 25 else 0.23))
        n_o3 = (0.77 if temp < 5 else (1.56 if temp < 35 else 2.85))

        try:
            values = [0] * 4
            for i in range(4):
                values[i] = self.adc.read_adc(i, gain=self.ADCGain)

            # calculate gas values from raw adc values
            ppbCO = self.rawADCtoPPB(0, 0, self._config["cali_co"], n_co)
            ppbNO = self.rawADCtoPPB(0, 0, self._config["cali_no"], n_no)
            ppbNO2 = self.rawADCtoPPB(values[0], values[1], self._config["cali_no2"], n_no2)
            ppbO3 = self.rawADCtoPPB(values[2], values[3], self._config["cali_o3"], n_o3)

            # apply zero offset and round to the desired accuracy
            ppbCO = round(ppbCO + float(self._config["cali_co"]["offset"]), self._digit_accuracy)
            ppbNO = round(ppbNO + float(self._config["cali_no"]["offset"]), self._digit_accuracy)
            ppbNO2 = round(ppbNO2 + float(self._config["cali_no2"]["offset"]), self._digit_accuracy)
            ppbO3 = round(ppbO3 + float(self._config["cali_o3"]["offset"]), self._digit_accuracy)

            return {"CO": ppbCO, "NO": ppbNO, "NO2": ppbNO2, "O3": ppbO3}

        except:
            prt.global_entity.printOnce("ADC disconnected", "ADC back online")
            return {"CO": 0, "NO": 0, "NO2": 0, "O3": 0}

    def stop(self):
        self.adc.stop_adc()
