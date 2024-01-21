# Based on UPS Lite v1.1 from https://github.com/xenDE
#
# functions for get UPS status - needs enable "i2c" in raspi-config
#
# https://github.com/linshuqin329/UPS-Lite
#
# For Raspberry Pi Zero Ups Power Expansion Board with Integrated Serial Port S3U4
# https://www.ebay.de/itm/For-Raspberry-Pi-Zero-Ups-Power-Expansion-Board-with-Integrated-Serial-Port-S3U4/323873804310
# https://www.aliexpress.com/item/32888533624.html
#
# To display external power supply status you need to bridge the necessary pins on the UPS-Lite board. See instructions in the UPS-Lite repo.
#
# Update for UPS Lite v1.3 by LouD
# Code reused from https://github.com/linshuqin329/UPS-Lite/blob/master/UPS-Lite_V1.3_CW2015/UPS_Lite_V1.3_CW2015.py

import logging
import struct

import RPi.GPIO as GPIO

import pwnagotchi
import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

CW2015_ADDRESS   = 0X62
CW2015_REG_VCELL = 0X02
CW2015_REG_SOC   = 0X04
CW2015_REG_MODE  = 0X0A

# TODO: add enable switch in config.yml an cleanup all to the best place
class UPS:
    def __init__(self):
        # only import when the module is loaded and enabled
        import smbus
        # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)
        self._bus = smbus.SMBus(1)

    def voltage(self):
        try:
            read = self._bus.read_word_data(CW2015_ADDRESS, CW2015_REG_VCELL)
            swapped = struct.unpack("<H", struct.pack(">H", read))[0]
            return swapped * 0.305 /1000
        except:
            return 0.0

    def capacity(self):
        try:
            read = self._bus.read_word_data(CW2015_ADDRESS, CW2015_REG_SOC)
            swapped = struct.unpack("<H", struct.pack(">H", read))[0]
            return swapped / 256
        except:
            return 0.0

    def charging(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(4, GPIO.IN)
            return '+' if GPIO.input(4) == GPIO.HIGH else '-'
        except:
            return '-'

    def quickstart(self):
            "This function wake up the CW2015 and make a quick-start fuel-gauge calculations "
            self._bus.write_word_data(CW2015_ADDRESS, CW2015_REG_MODE, 0x30)


class UPSLite(plugins.Plugin):
    __author__ = 'evilsocket@gmail.com & LouD'
    __version__ = '1.0.1'
    __license__ = 'GPL3'
    __description__ = 'A plugin that will add a voltage indicator for the UPS Lite v1.3'

    def __init__(self):
        self.ups = None

    def on_loaded(self):
        self.ups = UPS()

    def on_ui_setup(self, ui):
        ui.add_element('ups', LabeledValue(color=BLACK, label='', value='0%/0V', position=(ui.width() / 2 + 15, 0),
                                           label_font=fonts.Bold, text_font=fonts.Medium))

    def on_unload(self, ui):
        with ui._lock:
            ui.remove_element('ups')

    def on_ui_update(self, ui):
        self.ups.quickstart()        
        voltage  = self.ups.voltage()  # Does not show on main display, not enough room
        capacity = self.ups.capacity()
        charging = self.ups.charging()
        ui.set('ups', "%2i%%%s" % (capacity, charging))
        if capacity <= self.options['shutdown']:
            logging.info('[ups_lite] Empty battery (%.2fVolt %s%% <= %s%%): shuting down' % (voltage, capacity, self.options['shutdown']))
            ui.update(force=True, new_data={'status': 'Battery exhausted, bye ...'})
            pwnagotchi.shutdown()