# -*- coding: utf-8 -*-

""" This package contains a set of simple classes for interacting with the IOPi board
from AB Electronics.
(https://www.abelectronics.co.uk/products/3/Raspberry-Pi/18/IO-Pi).

It is composed of 2 layers:

    - the base layer, provided by the module :py:module:`pybot.abelec.iopi.base`, which contains
      the low level classes modeling the board components : expanders, expander ports, individual IOs

    - the module :py:module:`pybot.abelec.iopi.control`, built on top of the previous module,
      and which offers a high level abstraction of the board, providing IO symbolic naming,
      external configuration management, optimised IO states reading, changes notifications,...

For imports simplification, public definitions of the base module are exported at the package level,
and thus both clauses hereafter are equivalent:

>>> from pybot.abelec.iopi.base import IOPiBoard

>>> from pybot.abelec.iopi import IOPiBoard

Definitions from the ``control`` package module are not exported at the package level to avoid
importing both modules when the application needs the ``core`` only.

It is perfectly valid to work with the base layer only for simple needs.

"""

__author__ = 'Eric Pascual'

from base import *
