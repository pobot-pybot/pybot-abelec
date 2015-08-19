``pybot_abelec.iopi`` module
============================

Overview
--------
.. automodule:: pybot.abelec.iopi

API reference
-------------

The classes are ordered by "level of detail", i.e. from the board down to to single IO.
In other words, this leads to the sequence : ``board > expander > port > IO``.

.. py:currentmodule:: pybot.abelec.iopi

Board level class
~~~~~~~~~~~~~~~~~

.. autoclass:: IOPiBoard
    :members:
    :show-inheritance:

Intermediate classes
~~~~~~~~~~~~~~~~~~~~

The board in built around two **IO expander** chips, each one containing two **IO ports** of height IOs each.
The following classes model these two intermediate levels.

.. autoclass:: Expander
    :members:
    :show-inheritance:

.. autoclass:: Port
    :members:
    :show-inheritance:

Individual IO classes
~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: IO
    :members:
    :show-inheritance:

.. autoclass:: DigitalInput
    :members:
    :show-inheritance:

.. autoclass:: DigitalOutput
    :members:
    :show-inheritance:
