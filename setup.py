#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(name='pybot_abelec',
      namespace_packages=['pybot'],
      version='1.0.2',
      description='Support for AB Electronics Raspberry expansion boards',
      install_requires=['pybot_core'],
      extra_requires={
          'RasPi': ['pybot_raspi']
      },
      license='LGPL',
      author='Eric Pascual',
      author_email='eric@pobot.org',
      url='http://www.pobot.org',
      packages=find_packages("src"),
      package_dir={'': 'src'}
      )
