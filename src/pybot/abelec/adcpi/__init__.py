#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" This package contains a set of simple classes for interacting with the ADCPi board
from AB Electronics.
(https://www.abelectronics.co.uk/products/3/Raspberry-Pi/18/ADC-Pi).

It is composed of 2 layers:

    - the base layer, provided by the module :py:module:`pybot.abelec.adcpi.base`, which contains
      the low level classes modeling the board components : converters, individual inputs

    - the module :py:module:`pybot.abelec.adcpi.control`, built on top of the previous module,
      and which offers a high level abstraction of the board, providing input symbolic naming,
      external configuration management, optimised input reading, changes notifications,...

For imports simplification, public definitions of the base module are exported at the package level,
and thus both clauses hereafter are equivalent:

>>> from pybot.abelec.adcpi.base import ADCPiBoard

>>> from pybot.abelec.adcpi import ADCPiBoard

Definitions from the ``control`` package module are not exported at the package level to avoid
importing both modules when the application needs the ``core`` only.

It is perfectly valid to work with the base layer only for simple needs.
"""

__author__ = 'Eric Pascual'

from base import *
