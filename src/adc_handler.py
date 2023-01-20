from typing import Dict, Optional
import Adafruit_ADS1x15
import config
import prt
from generic_sensor import SensorBase


class ADCHandler(SensorBase):
    def __init__(self):
        super().__init__()
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

    def _raw_adc_to_ppb(self, w_raw: float, a_raw: float, cali: Dict[str, int], n: float) -> float:
        """uses raw working and auxiliary adc values as well as a calibration dict to calculate ppb values"""
        w = w_raw * self.mVGain
        a = a_raw * self.mVGain
        return ((w - cali["w0"]) - (n * (a - cali["a0"]))) / cali["sens"]

    def _raw_adc_to_mv(self, adc_raw: float) -> float:
        return round(adc_raw * self.mVGain, config.DIGIT_ACCURACY)

    def get_data(self, temp: int = 20) -> Dict[str, Optional[float]]:
        # The calibration has been done at 20 °C, use it as default
        # Could also be dynamically set by sht_temp
        # Calculate n factors from the temperature
        n_co = -1 if temp < 25 else -3.8
        n_no = 1.04 if temp < 15 else (1.82 if temp < 25 else 2)
        n_no2 = 0.76 if temp < 15 else (0.68 if temp < 25 else 0.23)
        n_o3 = 0.77 if temp < 5 else (1.56 if temp < 35 else 2.85)

        try:
            values_adc_a = [0] * 4
            values_adc_b = [0] * 4

            for i in range(4):
                values_adc_a[i] = self.adc_a.read_adc(i, gain=self.ADCGain)
                values_adc_b[i] = self.adc_b.read_adc(i, gain=self.ADCGain)

            # print("Raw values:",values_adc_a, values_adc_b)
            # print("Voltages:", [round(x * self.mVGain/1000, 3) for x in (values_adc_a + values_adc_b)])

            # calculate gas values from raw adc values
            ppb_co = self._raw_adc_to_ppb(values_adc_a[1], values_adc_a[0], config.ADC_CALI_CO, n_co)
            ppb_no = self._raw_adc_to_ppb(values_adc_a[3], values_adc_a[2], config.ADC_CALI_NO, n_no)
            ppb_no2 = self._raw_adc_to_ppb(values_adc_b[1], values_adc_b[0], config.ADC_CALI_NO2, n_no2)
            ppb_o3 = self._raw_adc_to_ppb(values_adc_b[3], values_adc_b[2], config.ADC_CALI_O3, n_o3)

            # Apply two point calibration
            ppb_co = self._calibrate(ppb_co, config.ADC_CALI_CO)
            ppb_no = self._calibrate(ppb_no, config.ADC_CALI_NO)
            ppb_no2 = self._calibrate(ppb_no2, config.ADC_CALI_NO2)
            ppb_o3 = self._calibrate(ppb_o3, config.ADC_CALI_O3)

            return {
                "CO": ppb_co,
                "NO": ppb_no,
                "NO2": ppb_no2,
                "O3": ppb_o3,
                "RAW_ADC_CO_W": self._raw_adc_to_mv(values_adc_a[1]),
                "RAW_ADC_CO_A": self._raw_adc_to_mv(values_adc_a[0]),
                "RAW_ADC_NO_W": self._raw_adc_to_mv(values_adc_a[3]),
                "RAW_ADC_NO_A": self._raw_adc_to_mv(values_adc_a[2]),
                "RAW_ADC_NO2_W": self._raw_adc_to_mv(values_adc_b[1]),
                "RAW_ADC_NO2_A": self._raw_adc_to_mv(values_adc_b[0]),
                "RAW_ADC_O3_W": self._raw_adc_to_mv(values_adc_b[3]),
                "RAW_ADC_O3_A": self._raw_adc_to_mv(values_adc_b[2]),
            }

        except OSError:
            prt.GLOBAL_ENTITY.print_once("ADC disconnected", "ADC back online")
            return {
                "CO": None,
                "NO": None,
                "NO2": None,
                "O3": None,
                "RAW_ADC_CO_W": None,
                "RAW_ADC_CO_A": None,
                "RAW_ADC_NO_W": None,
                "RAW_ADC_NO_A": None,
                "RAW_ADC_NO2_W": None,
                "RAW_ADC_NO2_A": None,
                "RAW_ADC_O3_W": None,
                "RAW_ADC_O3_A": None,
            }

    def stop(self) -> None:
        self.adc_a.stop_adc()
        self.adc_b.stop_adc()
