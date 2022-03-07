#!/usr/bin/env python

from distutils.core import setup

setup(name='Textile parser',
      version='1.0',
      description='Parse textile files (Dradis) to a LaTeX issue format',
      author='Jan-Jaap Korpershoek',
      author_email='jjkorpershoek96@gmail.com',
      packages=['textile_parser'],
      install_requires=['lark', 'jinja2'],
      entry_points={
        'console_scripts': ['dradis_to_latex=textile_parser:main'],
      }
      )
