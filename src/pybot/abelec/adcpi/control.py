# -*- coding: utf-8 -*-

__author__ = 'Eric Pascual'

from collections import namedtuple
import time

from .base import *

try:
    from pybot.raspi import i2c_bus
except ImportError:
    # print("WARNING: not running on a RaspberryPi => real IOs not supported")
    i2c_bus = None


class ADCPiController(object):
    """ The board controller.

    Is provides high level operations and interfaces with the board for polling inputs periodically.

    Inputs changes are monitored and appropriate signals are sent on D-Bus.
    """
    _board = None
    _i2c_address = None
    _inputs = None
    _inputs_value = None
    _logger = None
    _polling_period = 100
    _active = False

    _verbose = False

    def __init__(self, cfg, logger, verbose=False, debug=False):
        """
        :param dict cfg: configuration dictionary (see :py:class:`ADCPiNode` for details)
        :param logger: logger as set by our owner
        :param bool verbose: verbose logs
        :param bool debug: debug mode
        """
        self._verbose = verbose
        self._debug = debug

        self._logger = logger

        self._i2c_address = cfg.get('i2c_address', ADCPiBoard.CONV1_DEFAULT_ADDRESS)
        self._logger.info("i2c_address = 0x%x", self._i2c_address)

        self._polling_period = cfg.get('polling_period', self._polling_period)
        self._logger.info("polling_period = %dms", self._polling_period)

        try:
            input_specs = [
                InputSpecifications.from_dict(name, parms)
                for name, parms in cfg['inputs'].iteritems()
            ]
        except KeyError:
            input_specs = []
            self._logger.info('no input configured')
        else:
            self._logger.info('inputs configuration:')
            for specs in input_specs:
                self._logger.info("- %s", specs)

        # don't go further if no input is defined
        if not input_specs:
            raise ValueError('no input defined')

        # don't go further if we are not running on the real hardware
        if not i2c_bus:
            raise ValueError('cannot continue since not running on a real RaspberryPi')

        # suppose I2C addresses are configured in sequence
        self._board = board = ADCPiBoard(i2c_bus, conv1_addr=self._i2c_address, conv2_addr=self._i2c_address+1)

        # create input instances for those requested and index them by their name
        self._inputs = dict((
            (specs.name, _InputsDirectoryEntry(
                board.get_analog_input(specs.channel, rate=specs.rate_x, gain=specs.gain_x),
                int(2**specs.resolution * specs.drel_min)
            ))
            for specs in input_specs
        ))

        self._active = True

    @property
    def polling_period(self):
        return self._polling_period

    @property
    def input_names(self):
        return self._inputs.keys()

    def shutdown(self):
        """ Deactivates running tasks as part of the node shutdown sequence.
        """
        self._active = False

        # ensure we have a chance to end what is running
        time.sleep(2 * self._polling_period / 1000.)

    def update_inputs(self, notification_callback):
        """ This method must be invoked periodically by the application to read the inputs and monitor their
        value.

        Various options are available for this, such as:
            - explicitly in a dedicated thread of the application,
            - in main loops of the UI framework,
            - in the glib main loop for a D-Bus based application.

        The notification callback provided by the application must accept three parameters:

            name
                (string) the name of the IO which state has changed

            new_value
                (int) its new raw value

            voltage
                (float) the raw value converted to a voltage

        :param notification_callback: the callback for inputs changes notification
        """
        for input_name, entry in self._inputs.iteritems():
            adc_input = entry.adc_input
            new_value = adc_input.read_raw()

            value, _ = entry.last_reading

            if value is None or abs(new_value - value) >= entry.delta_min:
                voltage = adc_input.convert_raw(new_value)
                if self._verbose:
                    self._logger.info("input '%s' changed to %f V (raw=%d)", input_name, voltage, new_value)
                notification_callback(input_name, new_value, voltage)

                entry.last_reading = (new_value, voltage)

        return self._active

    def get_inputs_values(self, names):
        """ Returns the current raw value and converted voltage of the inputs, as updated in the last loop iteration

        :param names: the list if input names which state is requested
        :return: the list if values, as an array of tuples (raw, voltage) synchronized with the `names` parameter
        """
        return [self._inputs[name].last_reading for name in names]


class InputSpecifications(namedtuple('InputSpecifications', 'name channel resolution gain drel_min rate_x gain_x')):
    __slots__ = ()

    def __new__(cls, name, channel, resolution=None, gain=None, drel_min=0.005):
        if not name:
            raise ValueError('name is mandatory')
        if resolution is None:
            resolution = 12
        rate_x = ADCPiBoard.resolution_to_rate_x[resolution]
        if gain is None:
            gain = 1
        gain_x = ADCPiBoard.gain_factor_to_gain_x[gain]
        if not 0 <= drel_min <= 1.0:
            raise ValueError('invalid drel_min : %s' % drel_min)
        return super(InputSpecifications, cls).__new__(cls, name, channel, resolution, gain, drel_min, rate_x, gain_x)

    def __str__(self):
        return "name:%s channel:%d resolution:%d gain:%d drel_min=%f" % (
            self.name, self.channel, self.resolution, self.gain, self.drel_min
        )

    @classmethod
    def from_dict(cls, name, d):
        kwargs = dict([
            (k, d[k]) for k in set(InputSpecifications._fields) - {'name', 'rate_x', 'gain_x'} if k in d
        ])
        return InputSpecifications(name, **kwargs)


class _InputsDirectoryEntry(object):
        __slots__ = ('adc_input', 'delta_min', 'last_reading')

        def __init__(self, adc_input, delta_min):
            self.adc_input = adc_input
            self.delta_min = delta_min
            self.last_reading = (None, None)


