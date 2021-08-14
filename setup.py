# -*- coding: utf-8 -*-

from setuptools import setup

setup(
        name='socketrat',
        version='0.1',
        packages=['socketrat'],
        #entry_points="""
        #[console_scripts]
        #socketrat = socketrat:main
        #""",
        install_requires=[
            'colorama>=0.4.4',
            'tabulate>=0.8.9',
            'tqdm>=4.62.0',
        ],
)

