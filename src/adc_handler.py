import Adafruit_ADS1x15
import prt
import config
from generic_sensor import SensorBase


class ADCHandler(SensorBase):
    def __init__(self):
        self.adc_a = Adafruit_ADS1x15.ADS1115(address=config.ADC_ADDRESS_A)
        self.adc_b = Adafruit_ADS1x15.ADS1115(address=config.ADC_ADDRESS_B)
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
        #temp = other_sensor_data["sht_temp"]
        temp = 20  # The calibration has been done at this temperature
        # Calculate n factors from the temperature
        n_co = (-1 if temp < 25 else -3.8)
        n_no = (1.04 if temp < 15 else (1.82 if temp < 25 else 2))
        n_no2 = (0.76 if temp < 15 else (0.68 if temp < 25 else 0.23))
        n_o3 = (0.77 if temp < 5 else (1.56 if temp < 35 else 2.85))

        try:
            values_adc_a = [0] * 4
            values_adc_b = [0] * 4

            for i in range(4):
                values_adc_a[i] = self.adc_a.read_adc(i, gain=self.ADCGain)
                values_adc_b[i] = self.adc_b.read_adc(i, gain=self.ADCGain)

            #print("Raw values:",values_adc_a, values_adc_b)
            #print("Voltages:", [round(x * self.mVGain/1000, 3) for x in (values_adc_a + values_adc_b)])

            # calculate gas values from raw adc values
            ppbCO = self.rawADCtoPPB(values_adc_a[1], values_adc_a[0], config.ADC_CALI_CO, n_co)
            ppbNO = self.rawADCtoPPB(values_adc_a[3], values_adc_a[2], config.ADC_CALI_NO, n_no)
            ppbNO2 = self.rawADCtoPPB(values_adc_b[1], values_adc_b[0], config.ADC_CALI_NO2, n_no2)
            ppbO3 = self.rawADCtoPPB(values_adc_b[3], values_adc_b[2], config.ADC_CALI_O3, n_o3)

            # Apply two point calibration
            ppbCO = self.calibrate(ppbCO, config.ADC_CALI_CO)
            ppbNO = self.calibrate(ppbNO, config.ADC_CALI_NO)
            ppbNO2 = self.calibrate(ppbNO2, config.ADC_CALI_NO2)
            ppbO3 = self.calibrate(ppbO3, config.ADC_CALI_O3)

            return {"CO": ppbCO, "NO": ppbNO, "NO2": ppbNO2, "O3": ppbO3}

        except:
            prt.global_entity.printOnce("ADC disconnected", "ADC back online")
            return {"CO": 0, "NO": 0, "NO2": 0, "O3": 0}

    def stop(self):
        self.adc_a.stop_adc()
        self.adc_b.stop_adc()
