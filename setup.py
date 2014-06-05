#!/usr/bin/env python
# - coding: utf-8 -
from distutils.core import setup

for cmd in ('egg_info', 'develop'):
    import sys
    if cmd in sys.argv:
        from setuptools import setup

import sys
reload(sys).setdefaultencoding("UTF-8")

setup(
    name='django-nodes',
    version='0.1',

    description = (u'A content management toolkit for Django'
                   u' framework'.encode('utf8')),
    long_description = (open('README.rst').read().decode('utf8') 
                        + open('CHANGES.rst').read().decode('utf8')),

    author='Guchetl Murat',
    author_email='gmurka@gmail.com',

    url='https://bitbucket.org/sakkada/django-nodes/',

    packages=['nodes',
              'menus',],
    license = 'MIT license',

    requires=['django (>= 1.4)'],

    classifiers=(
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ),
)
