# -*- coding: utf-8 -*-

""" This module provides the high level abstraction of the board, with named IOs, external
configuration management, optimised IO states reading, changes notification,...
"""

__author__ = 'Eric Pascual'

__all__ = ['IOPiController']

import time
from collections import namedtuple

from .base import *

try:
    from pybot.raspi import i2c_bus
except ImportError:
    # print("WARNING: not running on a RaspberryPi => real IOs not supported")
    i2c_bus = None


class IOPiController(object):
    """ The board controller.

    Is provides high level operations and interfaces with the board for changing the outputs
    as requested and polling inputs periodically.

    Inputs changes are monitored and notifications are made using an application provided callback.
    """
    _board = None
    _i2c_address = None
    _polling_period = 100

    _inputs = None
    _inputs_state = None
    _inputs_mask = None

    _outputs = None
    _outputs_state = None
    _outputs_mask = None

    _logger = None
    _active = False
    _verbose = False

    def __init__(self, cfg, logger, verbose=False):
        """
        :param dict cfg: configuration dictionary (see :py:class:`IOPiNode` for details)
        :param logger: logger as set by our owner
        """
        self._verbose = verbose
        self._logger = logger

        self._i2c_address = cfg.get('i2c_address', IOPiBoard.EXP1_DEFAULT_ADDRESS)
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

        try:
            output_specs = [
                OutputSpecifications.from_dict(name, parms)
                for name, parms in cfg['outputs'].iteritems()
            ]
        except KeyError:
            output_specs = []
            self._logger.info('no output configured')
        else:
            self._logger.info('outputs configuration:')
            for specs in output_specs:
                self._logger.info("- %s", specs)

        # don't go further if neither input nor output is defined
        if not (input_specs or output_specs):
            raise ValueError('at least one input or output must be defined')

        # check that there is no overlap in definitions
        if {io.name for io in input_specs} & {io.name for io in output_specs}:
            raise ValueError('same name used for an input and for an output')

        input_io_nums = {io.expander_num * 100 + io.io_num for io in input_specs}
        output_io_nums = {io.expander_num * 100 + io.io_num for io in output_specs}
        if input_io_nums & output_io_nums:
            raise ValueError('same IO configured both as input and output')

        # don't go further if we are not running on the real hardware
        if not i2c_bus:
            raise ValueError('cannot continue since not running on a real RaspberryPi')

        # suppose I2C addresses are configured in sequence
        self._board = board = IOPiBoard(i2c_bus, exp1_addr=self._i2c_address, exp2_addr=self._i2c_address+1)

        # create input instances for those requested and index them by their name
        self._inputs = dict((
            (specs.name,
             _IODirectoryEntry(
                board.get_digital_input(specs.expander_num - 1, specs.io_num, pullup_enabled=specs.pull_up),
                specs.expander_num,
                specs.io_num
             )
             )
            for specs in input_specs
        ))

        # build the corresponding mask for bulk testing
        self._inputs_mask = reduce(lambda x, y: x | y, {1 << entry.num_32 for entry in self._inputs.values()})

        # create output instances for those requested, as for inputs
        # (no need to worry about setting the IO directions at chip level,
        # the IO class constructor takes care of this)
        self._outputs = dict((
            (specs.name,
             _IODirectoryEntry(
                 board.get_digital_output(specs.expander_num - 1, specs.io_num, specs.default_state),
                 specs.expander_num,
                 specs.io_num
             )
             )
            for specs in output_specs
        ))

        self._outputs_mask = reduce(lambda x, y: x | y, {1 << entry.num_32 for entry in self._outputs.values()})

        self._active = True

    @property
    def polling_period(self):
        return self._polling_period

    @property
    def input_names(self):
        return self._inputs.keys()

    @property
    def output_names(self):
        return self._outputs.keys()

    def reset_outputs(self):
        """ Resets outputs to their default states."""
        for output in self._outputs.itervalues():
            output.io.reset()

    def shutdown(self):
        """ Deactivates running tasks as part of the node shutdown sequence.
        """
        self.reset_outputs()

        self._active = False
        # ensure we have a chance to end what is running
        time.sleep(2 * self._polling_period / 1000.)

    def has_inputs(self):
        """ Tells if the boards has GPIO(s) configured as inputs.

        :return: True if at least one input has been defined
        :rtype: bool
        """
        return bool(self._inputs)

    def _process_ios(self, io_dict, io_mask, all_states, previous_states, notification_callback):
        """
        :param io_dict: the dictionary of the processed IOs
        :param io_mask: the global mask for the processed IOs
        :param all_states: the global states read from the board (all inputs and outputs included)
        :param previous_states: previous known state of the processed IOs
        :param notification_callback: change notification callback
        :return: the new states of the processed IOs in case of change, None otherwise
        """
        new_states = all_states & io_mask
        if new_states != previous_states:
            if previous_states is None:
                change_mask = io_mask
            else:
                change_mask = new_states ^ previous_states
            for name, io in io_dict.iteritems():
                num_32 = io.num_32
                mask = 1 << num_32
                if change_mask & mask:
                    state = bool(new_states & mask)
                    io.state = state
                    notification_callback(name, state)

            return new_states

        else:
            return None

    def update_io_states(self, notification_callbacks):
        """ This method must be invoked periodically by the application to read the IOs and monitor their
        state.

        Various options are available for this, such as:
            - explicitly in a dedicated thread of the application,
            - in main loops of the UI framework,
            - in the glib main loop for a D-Bus based application.

        To optimise I2C traffic, we acquire all the board IOs in bulk, and cache their state, so that
        individual IO read access will operate on this cache and will not perform an I2C transaction. The
        drawback is that the value returned to the application is not the true current one, but the one
        read on the previous polling. Most of the time this is accurate enough, knowing that a better
        precision can be achieved by reducing the polling period in the configuration parameters.

        The notification callbacks provided by the application must accept two parameters:

            name
                (string) the name of the IO which state has changed

            state
                (boolean) its new state

        :param notification_callbacks: a tuple containing the callbacks for inputs and outputs changes notification
        """
        all_states = self._board.read()
        cb_input_changed, cb_output_changed = notification_callbacks

        # process the input states and detect changes to publish the corresponding events
        new_states = self._process_ios(
            self._inputs, self._inputs_mask,
            all_states, self._inputs_state,
            cb_input_changed
        )
        if new_states is not None:
            if self._verbose:
                self._logger.info("input states changed to 0x%04x", new_states)
            self._inputs_state = new_states

        # process the output states the same way as above

        # Despite the small delay introduced by the polling period, it is better to do it this way
        # rather than directly in set_outputs_state() method because :
        # - it reflects the true state of the output, and not the supposed one
        # - it takes in account modifications done by some external action
        new_states = self._process_ios(
            self._outputs, self._outputs_mask,
            all_states, self._outputs_state,
            cb_output_changed
        )
        if new_states is not None:
            if self._verbose:
                self._logger.info("output states changed to 0x%04x", new_states)
            self._outputs_state = new_states

        # ask to keep on calling us while the node is active
        return self._active

    def get_inputs_state(self, names):
        """ Returns the current state of the inputs, as updated in the last loop iteration

        :param names: the list if input names which state is requested
        :return: the list if states, as an array synchronized with the `names` parameter
        """
        return [self._inputs[name].state for name in names]

    def set_outputs_state(self, states):
        """ Changes the outputs as specified.

        :param states: a list if tuples providing the name and the state
        :raises ValueError: if an unknown name is in the provided list
        """
        # better check before to avoid leaving outputs in a inconsistent state
        names = set([t[0] for t in states])
        invalids = names - set(self._outputs.iterkeys())
        if invalids:
            raise ValueError('unknown outputs : %s' % invalids)

        for name, state in states:
            io = self._outputs[name]
            state = bool(state)

            if state != io.state:
                if state:
                    self._outputs[name].io.set()
                else:
                    self._outputs[name].io.clear()

    def get_outputs_state(self, names):
        """ Returns the current state of the outputs

        :param names: the list if output names which state is requested
        :return: the list if states, as an array synchronized with the `names` parameter
        """
        return [self._outputs[name].state for name in names]


class _IOSpecifications(object):
    @staticmethod
    def _check(name, expander_num, io_num):
        if not name:
            raise ValueError('name is mandatory')

        if expander_num not in (1, 2):
            raise ValueError('invalid expander num')

        if not 1 <= io_num <= 16:
            raise ValueError('invalid IO num')


class InputSpecifications(namedtuple('InputSpecifications', 'name expander_num io_num pull_up'), _IOSpecifications):
    __slots__ = ()

    def __new__(cls, name, expander_num, io_num, pull_up=True):
        cls._check(name, expander_num, io_num)
        return super(InputSpecifications, cls).__new__(cls, name, expander_num, io_num, pull_up)

    @classmethod
    def from_dict(cls, name, d):
        return InputSpecifications(
            name,
            **dict([(fld, d[fld]) for fld in set(InputSpecifications._fields) - {'name'}])
        )

    def __str__(self):
        return "name:%s expander:%d io:%d pull_up:%s" % (
            self.name, self.expander_num, self.io_num, self.pull_up
        )


class OutputSpecifications(namedtuple('OutputSpecifications', 'name expander_num io_num default_state'), _IOSpecifications):
    __slots__ = ()

    def __new__(cls, name, expander_num, io_num, default_state=0):
        cls._check(name, expander_num, io_num)
        return super(OutputSpecifications, cls).__new__(cls, name, expander_num, io_num, default_state)

    @classmethod
    def from_dict(cls, name, d):
        return OutputSpecifications(
            name,
            **dict([(fld, d[fld]) for fld in set(OutputSpecifications._fields) - {'name'}])
        )

    def __str__(self):
        return "name:%s expander:%d io:%d default_state:%d" % (
            self.name, self.expander_num, self.io_num, self.default_state
        )


class _IODirectoryEntry(object):
    def __init__(self, io, exp_board_num, io_board_num):
        self.io = io
        self.state = None
        self.num_32 = (exp_board_num - 1) * 16 + io_board_num - 1
        self.pub = None


