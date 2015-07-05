''pybot'' collection
====================

This package is part of POBOT's `pybot` packages collection, which aims
at gathering contributions created while experimenting with various technologies or
hardware in the context of robotics projects.

Although primarily focused on robotics applications (taken with its widest acceptation)
some of these contributions can be used in other contexts. Don't hesitate to keep us informed
on any usage you could have made.

Implementation note
-------------------

The collection code is organized using namespace packages, in order to group them in
a single tree rather that resulting in a invading flat collection. Please refer to [this official
documentation](https://www.python.org/dev/peps/pep-0382/) for details.

Package content
===============

This package contains several modules for using Raspberry Pi expansion boards from
AB Electronics (https://www.abelectronics.co.uk).

Installation
============

::

    $ cd <PROJECT_ROOT_DIR>
    $ python setup.py sdist
    $ pip install dist/*.tar.gz

Documentation generation
========================

The documentation generation uses Sphinx (http://sphinx-doc.org/).
::

    $ cd <PROJECT_ROOT_DIR>/docs
    $ make html

Examples
========

*Under work*
