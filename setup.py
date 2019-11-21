#!/usr/bin/env python

from setuptools import setup


setup(
    name = 'ctfhost',
    version = '2.0.0.a0',
    packages = ['ctfhost'],
    install_requires = [
        'loguru',
        'markdown',
        'pygments',
        'tornado',
    ],
    entry_points = {
        'console_scripts': [
            'ctfhost = ctfhost.__main__:main',
        ]
    },

    author = 'kodopp',
    description = 'A platform for hosting task-based CTF competitions',
    keywords = 'ctf task-based self-hosted web',
    url = 'https://github.com/kodo-pp/ctfhost',
    classifiers = [
        'Development Status :: 1 - Planning',
        'Environment :: Web Environment',
        'Intended Audience :: Other Audience',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Topic :: Games/Entertainment',
        'Topic :: Other/Nonlisted Topic',
    ]
)
