# -*- coding: utf-8 -*-

from setuptools import setup

setup(
        name='socketrat',
        version='0.1.0',
        packages=['socketrat'],
        #entry_points="""
        #[console_scripts]
        #socketrat = socketrat:main
        #""",
        install_requires=[
            'pyreadline>=2.1',
            'tabulate',
            'tqdm',
        ],
)

