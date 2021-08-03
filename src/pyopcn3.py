import logging
import re
import struct
from time import sleep
import sys

# set up a default logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class _OPC(object):
    """Generic class for any Alphasense OPC. Provides the common methods and calculations for each OPC. This class is designed to be the base class, and should not be used alone unless during development.
    :param spi_connection: spidev.SpiDev or usbiss.spi.SPI connection
    :param debug: Set true to print data to console while running
    :param model: Model number of the OPC ('N1' or 'N2' or 'N3') set by the parent class
    :param firmware: You can manually set the firmware version as a tuple. Ex. (18,2)
    :param max_cnxn_retries: Maximum number of times a connection will try to be made.
    :param retry_interval_ms: The sleep interval for the device between retrying to connect to the OPC. Units are in ms.
    :raises: opc.exceptions.SpiConnectionError
    :type spi_connection: spidev.SpiDev or usbiss.spi.SPI
    :type debug: boolean
    :type model: string
    :type max_cnxn_retries: int
    :type retry_interval_ms: int
    :rtype: opc._OPC
    """

    def __init__(self, spi_connection, firmware=None, max_cnxn_retries=5, retry_interval_ms=1000, **kwargs):
        self.cnxn = spi_connection
        self.debug = kwargs.get('debug', False)
        self.model = kwargs.get('model', 'N2')

        if firmware is not None:
            major, minor = firmware[0], firmware[1]
            version = float("{}.{}".format(major, minor))
        else:
            major, minor, version = None, None, None

        self.firmware = {'major': major, 'minor': minor, 'version': version}

        # Check to make sure the connection has the xfer attribute
        msg = ("The SPI connection must be a valid SPI master with "
               "transfer function 'xfer'")
        assert hasattr(spi_connection, 'xfer'), msg
        assert self.cnxn.mode == 1, "SPI mode must be 1"

        # Set the firmware version upon initialization IFF it hasn't been set manually
        i = 0

        self.firmware['version'] = 18.

        if self.firmware['version'] is None:
            while self.firmware['version'] is None:
                if i > max_cnxn_retries:
                    msg = """
                            Your firmware version could not be automatically detected. This is usually caused by bad wiring or a poor power supply. If niether of these are likely candidates, please open an issue on the GitHub repository at https://github.com/dhhagan/py-opc/issues/new. Another option would be to
                            increase the max_cnxn_retries variable if you feel the serial communication is being held up for some reason.
                            """

                ## raise FirmwareVersionError(msg)

                # store the info_string
                infostring = self.read_info_string()

                print(infostring)

                try:
                    self.firmware['version'] = int(re.findall("\d{3}", infostring)[-1])
                except Exception as e:
                    ##  logger.error("Could not parse the fimrware version from {}".format(infostring), exc_info=True)

                    # sleep for a period of time
                    sleep(retry_interval_ms / 1000)

                i += 1

        # At this point, we have a firmware version

        # If firmware version is >= 18, set the major and minor versions..
        #      try:
        #          if self.firmware['version'] >= 18.:
        #              self.read_firmware()
        #          else:
        #              self.firmware['major'] = self.firmware['version']
        #      except:
        #          logger.info("No firmware version could be read.")

        # We requested to wait until the device is connected
        if kwargs.get('wait', False) is not False:
            self.wait(**kwargs)

        else:  # Sleep for a bit to alleviate issues
            sleep(1)

    def _16bit_unsigned(self, LSB, MSB):
        """Returns the combined LSB and MSB
        :param LSB: Least Significant Byte
        :param MSB: Most Significant Byte
        :type LSB: byte
        :type MSB: byte
        :rtype: 16-bit unsigned int
        """
        return (MSB << 8) | LSB

    def _calculate_float(self, byte_array):
        """Returns an IEEE 754 float from an array of 4 bytes
        :param byte_array: Expects an array of 4 bytes
        :type byte_array: array
        :rtype: float
        """
        # print("len(byte_array):",len(byte_array))
        if len(byte_array) != 4:
            return None
        return struct.unpack('f', struct.pack('4B', *byte_array))[0]

    def _calculate_mtof(self, mtof):
        """Returns the average amount of time that particles in a bin
        took to cross the path of the laser [units -> microseconds]
        :param mtof: mass time-of-flight
        :type mtof: float
        :rtype: float
        """
        return mtof / 3.0

    def _calculate_temp(self, vals):
        """Calculates the temperature in degrees celcius
        :param vals: array of bytes
        :type vals: array
        :rtype: float
        """
        print("temp: ", vals)
        if len(vals) < 4:
            return None
        return ((vals[3] << 24) | (vals[2] << 16) | (vals[1] << 8) | vals[0])

    def _calculate_temp_uint(self, LSB, MSB):
        """Calculates the temperature in degrees celcius"""
        tempraw = ((MSB << 8) | LSB)
        temp = -45.0 + 175.0 * tempraw / (2 ** 16 - 1)
        # print("temp raw/deg =", tempraw, temp)
        return temp

    def _calculate_hum(self, vals):
        """Calculates the relative humidity in percent
        :param vals: array of bytes
        :type vals: array
        :rtype: float
        """
        if len(vals) < 4:
            return None
        return ((vals[3] << 24) | (vals[2] << 16) | (vals[1] << 8) | vals[0])

    def _calculate_hum_uint(self, LSB, MSB):
        hum = ((MSB << 8) | LSB)
        hum = 100.0 * hum / (2 ** 16 - 1)
        return hum

    def _calculate_flowrate(self, LSB, MSB):
        """Calculates the temperature in degrees celcius
        :param vals: array of bytes
        :type vals: array
        :rtype: float
        """
        return ((MSB << 8) | LSB) / 100.0

    def _calculate_pressure(self, vals):
        """Calculates the pressure in pascals
        :param vals: array of bytes
        :type vals: array
        :rtype: float
        """
        if len(vals) < 4:
            return None

        return ((vals[3] << 24) | (vals[2] << 16) | (vals[1] << 8) | vals[0])

    def _calculate_period(self, vals):
        ''' calculate the sampling period in seconds '''
        if len(vals) < 4:
            return None
        if self.firmware < 16:
            return ((vals[3] << 24) | (vals[2] << 16) | (vals[1] << 8) | vals[0]) / 12e6
        else:
            return self._calculate_float(vals)

    def _calculate_period_uint(self, LSB, MSB):
        ''' calculate the sampling period in seconds '''
        return ((MSB << 8) | LSB) / 100.0

    def _calculate_crc16(self, data, length):
        ''' calculate the modbus like CRC16 Checksum '''
        crc = 0xFFFF
        j = 0
        while length != 0:
            crc ^= list.__getitem__(data, j)
            for i in range(0, 8):
                if crc & 1:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
            length -= 1
            j += 1
        return crc

    def wait(self, **kwargs):
        """Wait for the OPC to prepare itself for data transmission. On some devides this can take a few seconds
        :rtype: self
        :Example:
        >> alpha = opc.OPCN2(spi, debug=True).wait(check=200)
        >> alpha = opc.OPCN2(spi, debug=True, wait=True, check=200)
        """

        if not callable(self.on):
            raise UserWarning('Your device does not support the self.on function, try without wait')

        if not callable(self.histogram):
            raise UserWarning('Your device does not support the self.histogram function, try without wait')

        self.on()
        while True:
            try:
                if self.histogram() is None:
                    raise UserWarning('Could not load histogram, perhaps the device is not yet connected')

            except UserWarning as e:
                sleep(kwargs.get('check', 200) / 1000.)

        return self

    def lookup_bin_boundary(self, adc_value):
        """Looks up the bin boundary value in microns based on the lookup table provided by Alphasense.
            :param adc_value: ADC Value (0 - 4095)
            :type adc_value: int
            :rtype: float
        """
        if adc_value < 0:
            adc_value = 0

        if adc_value > 4095:
            adc_value = 4095

        return OPC_LOOKUP[adc_value]

    def calculate_bin_boundary(self, bb):
        """Calculate the adc value that corresponds to a specific bin boundary diameter in microns.
            :param bb: Bin Boundary in microns
            :type bb: float
            :rtype: int
        """

        return min(enumerate(OPC_LOOKUP), key=lambda x: abs(x[1] - bb))[0]

    def read_info_string(self):
        """Reads the information string for the OPC
        :rtype: string
        'OPC-N2 FirmwareVer=OPC-018.2....................BD'
        """
        infostring = []

        # Send the command byte and sleep for 9 ms
        self.cnxn.xfer([0x3F])
        sleep(10e-3)

        # Read the info string by sending 60 empty bytes
        for i in range(60):
            # resp = self.cnxn.xfer([0x00])[0]
            resp = self.cnxn.xfer([0x3F])[0]
            infostring.append(chr(resp))

        sleep(0.1)

        return ''.join(infostring)

    def ping(self):
        """Checks the connection between the Raspberry Pi and the OPC
        :rtype: Boolean
        """
        b = self.cnxn.xfer([0xCF])[0]  # send the command byte
        sleep(0.1)
        return True if b == 0xF3 else False

    def __repr__(self):
        return "Alphasense OPC-{}v{}".format(self.model, self.firmware['version'])


###################################################################################
class OPCN3(_OPC):
    """Create an instance of the Alphasene OPC-N3. Currently supported by firmware
    versions 14-18. opc.OPCN3 inherits from the opc.OPC parent class.
    :param spi_connection: The spidev instance for the SPI connection.
    :type spi_connection: spidev.SpiDev
    :rtype: opc.OPCN3
    :raises: opc.exceptions.FirmwareVersionError
    :Example:
    >>> alpha = opc.OPCN3(spi)
    >>> alpha
    Alphasense OPC-N3v18.2
    """

    def __init__(self, spi_connection, **kwargs):
        super(OPCN3, self).__init__(spi_connection, model='N3', **kwargs)

    ## firmware_min = 0.   # Minimum firmware version supported
    ## firmware_max = 9999.   # Maximum firmware version supported

    ## if self.firmware['major'] < firmware_min or self.firmware['major'] > firmware_max:
    ##     logger.error("Firmware version is invalid for this device.")

    ## print(self.firmware['major'])

    ## raise FirmwareVersionError("Your firmware is not yet supported. Only versions 14-18 ...")

    def fan_on(self):

        # SEND COMMAND BYTE 0x03
        a = self.cnxn.xfer([0x03])[0]
        print("CMD: ", hex(a), a)
        while a is not int('0x31', 16):  # [0xf3]: #49
            sleep(3)
            a = self.cnxn.xfer([0x03])[0]
            print("CMD: ", hex(a), a)
        sleep(0.02)  # >10ms <100ms
        a = self.cnxn.xfer([0x03])[0]
        sleep(0.02)

        # SEND 0x03 TO SET FAN ON
        a = int('0x03', 16)
        print("sending ", "{0:08b}".format(a))
        a = self.cnxn.xfer([0x03])[0]
        print("FAN_ON: ", hex(a), a)

    def fan_off(self):

        # SEND COMMAND BYTE 0x03
        a = self.cnxn.xfer([0x03])[0]
        print("CMD: ", hex(a), a)
        while a is not int('0x31', 16):  # [0xf3]: #49
            sleep(3)
            a = self.cnxn.xfer([0x03])[0]
            print("CMD: ", hex(a), a)
        sleep(0.02)  # >10ms <100ms
        a = self.cnxn.xfer([0x03])[0]
        sleep(0.02)

        # SEND 0x02 TO SET FAN OFF
        a = int('0x02', 16)
        print("sending ", "{0:08b}".format(a))
        a = self.cnxn.xfer([0x02])[0]
        print("FAN_OFF: ", hex(a), a)

    def laser_on(self):

        # SEND COMMAND BYTE 0x03
        a = self.cnxn.xfer([0x03])[0]
        print("CMD: ", hex(a), a)
        while a is not int('0x31', 16):  # [0xf3]: #49
            sleep(3)
            a = self.cnxn.xfer([0x03])[0]
            print("CMD: ", hex(a), a)
        sleep(0.02)  # >10ms <100ms
        a = self.cnxn.xfer([0x03])[0]
        sleep(0.02)

        # SEND 0x07 TO SET FAN ON
        a = int('0x07', 16)
        print("sending ", "{0:08b}".format(a))
        a = self.cnxn.xfer([0x07])[0]
        print("LASER_ON: ", hex(a), a)

    def laser_off(self):

        # SEND COMMAND BYTE 0x03
        a = self.cnxn.xfer([0x03])[0]
        print("CMD: ", hex(a), a)
        while a is not int('0x31', 16):  # [0xf3]: #49
            sleep(3)
            a = self.cnxn.xfer([0x03])[0]
            print("CMD: ", hex(a), a)
        sleep(0.02)  # >10ms <100ms
        a = self.cnxn.xfer([0x03])[0]
        sleep(0.02)

        # SEND 0x06 TO SET LASER OFF
        a = int('0x06', 16)
        print("sending ", "{0:08b}".format(a))
        a = self.cnxn.xfer([0x06])[0]
        print("LASER_OFF: ", hex(a), a)

    def on(self):
        """Turn ON the OPC (fan and laser)
        :rtype: boolean
        :Example:
        >>> alpha.on()
        True
        """

        # SEND COMMAND BYTE 0x03
        a = self.cnxn.xfer([0x03])[0]
        # print("CMD: ", hex(a), a)
        while a is not int('0x31', 16):  # [0xf3]: #49
            sleep(3)
            a = self.cnxn.xfer([0x03])[0]
            # print("CMD: ", hex(a), a)
        sleep(0.02)  # >10ms <100ms
        a1 = self.cnxn.xfer([0x03])[0]
        sleep(0.02)

        # SEND 0x03 TO SET FAN ON
        a = int('0x03', 16)
        # print("sending ", "{0:08b}".format(a))
        b1 = self.cnxn.xfer([0x03])[0]
        # print("FAN_ON: ", hex(b1), b1)

        sleep(1)

        # SEND COMMAND BYTE 0x03
        a = self.cnxn.xfer([0x03])[0]
        # print("CMD: ", hex(a), a)
        while a is not int('0x31', 16):  # [0xf3]: #49
            sleep(3)
            a = self.cnxn.xfer([0x03])[0]
            # print("CMD: ", hex(a), a)
        sleep(0.02)  # >10ms <100ms
        a2 = self.cnxn.xfer([0x03])[0]
        sleep(0.02)

        # SEND 0x07 TO SET FAN ON
        a = int('0x07', 16)
        # print("sending ", "{0:08b}".format(a))
        b2 = self.cnxn.xfer([0x07])[0]
        # print("LASER_ON: ", hex(b2), b2)

        return True if a1 == 0xF3 and b1 == 0x03 and a2 == 0xF3 and b2 == 0x03 else False

    def off(self):
        """Turn OFF the OPC (fan and laser)
        :rtype: boolean
        :Example:
        >>> alpha.off()
        True
        """

        # SEND COMMAND BYTE 0x03
        a = self.cnxn.xfer([0x03])[0]
        # print("CMD: ", hex(a), a)
        while a is not int('0x31', 16):  # [0xf3]: #49
            sleep(3)
            a = self.cnxn.xfer([0x03])[0]
            # print("CMD: ", hex(a), a)
        sleep(0.02)  # >10ms <100ms
        a1 = self.cnxn.xfer([0x03])[0]
        sleep(0.02)

        # SEND 0x06 TO SET LASER OFF
        a = int('0x06', 16)
        # print("sending ", "{0:08b}".format(a))
        b1 = self.cnxn.xfer([0x06])[0]
        # print("LASER_OFF: ", hex(b1), b1)

        sleep(1)

        # SEND COMMAND BYTE 0x03
        a = self.cnxn.xfer([0x03])[0]
        # print("CMD: ", hex(a), a)
        while a is not int('0x31', 16):  # [0xf3]: #49
            sleep(3)
            a = self.cnxn.xfer([0x03])[0]
            print("CMD: ", hex(a), a)
        sleep(0.02)  # >10ms <100ms
        a2 = self.cnxn.xfer([0x03])[0]
        sleep(0.02)

        # SEND 0x02 TO SET FAN OFF
        a = int('0x02', 16)
        # print("sending ", "{0:08b}".format(a))
        b2 = self.cnxn.xfer([0x02])[0]
        # print("FAN_OFF: ", hex(b2), b2)

        return True if a1 == 0xF3 and b1 == 0x03 and a2 == 0xF3 and b2 == 0x03 else False

    def read_pot_status(self):
        """Read the status of the digital pot. Firmware v18+ only.
        The return value is a dictionary containing the following as
        unsigned 8-bit integers: FanON, LaserON, FanDACVal, LaserDACVal.
        :rtype: dict
        :Example:
        >>> alpha.read_pot_status()
        {
            'LaserDACVal': 230,
            'FanDACVal': 255,
            'FanON': 0,
            'LaserON': 0
        }
        """
        # Send the command byte and wait 10 ms
        a = self.cnxn.xfer([0x13])[0]
        sleep(0.02)
        a = self.cnxn.xfer([0x13])[0]
        sleep(0.02)

        # Build an array of the results
        res = []
        for i in range(6):
            res.append(self.cnxn.xfer([0x00])[0])
        sleep(0.1)
        return {
            'FanON': res[0],
            'LaserON': res[1],
            'FanDACVal': res[2],
            'LaserDACVal': res[3],
            'LaserSwitch': res[4],
            'GainToggle': res[5]
        }

    def histogram(self, number_concentration=True):
        """Read and reset the histogram. As of v1.3.0, histogram
        values are reported in particle number concentration (#/cc) by default.
        :param number_concentration: If true, histogram bins are reported in number concentration vs. raw values.
        :type number_concentration: boolean
        :rtype: dictionary
        :Example:
        >>> alpha.histogram()
        {
            'Temperature': None, 'Pressure': None, 'Bin 0': 0, 'Bin 1': 0, 'Bin 2': 0, ... 'Bin 15': 0,
            'SFR': 3.700, 'Bin1MToF': 0, 'Bin3MToF': 0, 'Bin5MToF': 0, 'Bin7MToF': 0, 'PM1': 0.0, 'PM2.5': 0.0,
            'PM10': 0.0, 'Sampling Period': 2.345, 'Checksum': 0
        }
        """
        resp = []
        data = {}

        # Send the command byte
        a = 0
        b = 0
        arep = int('0x31', 16)
        brep = int('0xf3', 16)
        while a is not arep or b is not brep:
            a = self.cnxn.xfer([0x30])[0]
            # print(hex(a), a)
            sleep(0.01)
            b = self.cnxn.xfer([0x30])[0]
            # print(hex(b), b)

        # Wait 20 ms
        sleep(20e-3)
        # a = self.cnxn.xfer([0x30])[0]

        # read the histogram
        for i in range(86):
            # r = self.cnxn.xfer([0x00])[0]
            r = self.cnxn.xfer([0x30])[0]
            resp.append(r)

        # print(resp)

        # convert to real things and store in dictionary!
        data['Bin 0'] = self._16bit_unsigned(resp[0], resp[1])
        data['Bin 1'] = self._16bit_unsigned(resp[2], resp[3])
        data['Bin 2'] = self._16bit_unsigned(resp[4], resp[5])
        data['Bin 3'] = self._16bit_unsigned(resp[6], resp[7])
        data['Bin 4'] = self._16bit_unsigned(resp[8], resp[9])
        data['Bin 5'] = self._16bit_unsigned(resp[10], resp[11])
        data['Bin 6'] = self._16bit_unsigned(resp[12], resp[13])
        data['Bin 7'] = self._16bit_unsigned(resp[14], resp[15])
        data['Bin 8'] = self._16bit_unsigned(resp[16], resp[17])
        data['Bin 9'] = self._16bit_unsigned(resp[18], resp[19])
        data['Bin 10'] = self._16bit_unsigned(resp[20], resp[21])
        data['Bin 11'] = self._16bit_unsigned(resp[22], resp[23])
        data['Bin 12'] = self._16bit_unsigned(resp[24], resp[25])
        data['Bin 13'] = self._16bit_unsigned(resp[26], resp[27])
        data['Bin 14'] = self._16bit_unsigned(resp[28], resp[29])
        data['Bin 15'] = self._16bit_unsigned(resp[30], resp[31])
        data['Bin 16'] = self._16bit_unsigned(resp[32], resp[33])
        data['Bin 17'] = self._16bit_unsigned(resp[34], resp[35])
        data['Bin 18'] = self._16bit_unsigned(resp[36], resp[37])
        data['Bin 19'] = self._16bit_unsigned(resp[38], resp[39])
        data['Bin 20'] = self._16bit_unsigned(resp[40], resp[41])
        data['Bin 21'] = self._16bit_unsigned(resp[42], resp[43])
        data['Bin 22'] = self._16bit_unsigned(resp[44], resp[45])
        data['Bin 23'] = self._16bit_unsigned(resp[46], resp[47])

        data['Bin1 MToF'] = self._calculate_mtof(resp[48])
        data['Bin3 MToF'] = self._calculate_mtof(resp[49])
        data['Bin5 MToF'] = self._calculate_mtof(resp[50])
        data['Bin7 MToF'] = self._calculate_mtof(resp[51])

        data['Sampling Period'] = self._calculate_period_uint(resp[52], resp[53])
        data['SFR'] = self._calculate_flowrate(resp[54], resp[55])
        data['Temperature'] = self._calculate_temp_uint(resp[56], resp[57])
        data['Relative humidity'] = self._calculate_hum_uint(resp[58], resp[59])

        data['PM1'] = self._calculate_float(resp[60:64])
        data['PM2.5'] = self._calculate_float(resp[64:68])
        data['PM10'] = self._calculate_float(resp[68:72])

        # The OPCN3 sometimes gives nan as PM values, most likely a power issue
        if data['PM1'] != data['PM1']:
            print("Received faulty PM values check OPCN3 power supply")

        data['Reject count Glitch'] = self._16bit_unsigned(resp[72], resp[73])
        data['Reject count LongTOF'] = self._16bit_unsigned(resp[74], resp[75])
        data['Reject count Ratio'] = self._16bit_unsigned(resp[76], resp[77])
        data['Reject Count OutOfRange'] = self._16bit_unsigned(resp[78], resp[79])
        data['Fan rev count'] = self._16bit_unsigned(resp[80], resp[81])
        data['Laser status'] = self._16bit_unsigned(resp[82], resp[83])
        data['Checksum'] = self._16bit_unsigned(resp[84], resp[85])

        calculated_checksum = self._calculate_crc16(resp, 84)

        # Check that calculated checksum and sent checksum are identical
        if calculated_checksum != data['Checksum']:
            print("CHECKSUM: ", calculated_checksum, data['Checksum'])
            logger.warning("Data transfer was incomplete")
            return None

        # If histogram is true, convert histogram values to number concentration
        if number_concentration is True:
            _conv_ = data['SFR'] * data['Sampling Period']  # Divider in units of ml (cc)

            data['Bin 0'] = data['Bin 0'] / _conv_
            data['Bin 1'] = data['Bin 1'] / _conv_
            data['Bin 2'] = data['Bin 2'] / _conv_
            data['Bin 3'] = data['Bin 3'] / _conv_
            data['Bin 4'] = data['Bin 4'] / _conv_
            data['Bin 5'] = data['Bin 5'] / _conv_
            data['Bin 6'] = data['Bin 6'] / _conv_
            data['Bin 7'] = data['Bin 7'] / _conv_
            data['Bin 8'] = data['Bin 8'] / _conv_
            data['Bin 9'] = data['Bin 9'] / _conv_
            data['Bin 10'] = data['Bin 10'] / _conv_
            data['Bin 11'] = data['Bin 11'] / _conv_
            data['Bin 12'] = data['Bin 12'] / _conv_
            data['Bin 13'] = data['Bin 13'] / _conv_
            data['Bin 14'] = data['Bin 14'] / _conv_
            data['Bin 15'] = data['Bin 15'] / _conv_
            data['Bin 16'] = data['Bin 16'] / _conv_
            data['Bin 17'] = data['Bin 17'] / _conv_
            data['Bin 18'] = data['Bin 18'] / _conv_
            data['Bin 19'] = data['Bin 19'] / _conv_
            data['Bin 20'] = data['Bin 20'] / _conv_
            data['Bin 21'] = data['Bin 21'] / _conv_
            data['Bin 22'] = data['Bin 22'] / _conv_
            data['Bin 23'] = data['Bin 23'] / _conv_

        return data

    def sn(self):
        """Read the Serial Number string. This method is only available on OPC-N2
        firmware versions 18+.
        :rtype: string
        :Example:
        >>> alpha.sn()
        'OPC-N2 123456789'
        """
        string = []

        # Send the command byte and sleep for 9 ms
        a = self.cnxn.xfer([0x10])
        sleep(0.02)
        b = self.cnxn.xfer([0x10])
        sleep(0.02)

        # Read the info string by sending 60 empty bytes
        for i in range(60):
            resp = self.cnxn.xfer([0x10])[0]
            string.append(chr(resp))

        sleep(0.1)

        return ''.join(string)
