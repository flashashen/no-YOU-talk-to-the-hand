from setuptools import setup
import os

setup(
    name='no_you_talk_to_the_hand',
    version='0.3',
    py_modules=['no_you_talk_to_the_hand'],
    install_requires=[
        'Click',
        'supervisor',
        'pyyaml',
        'jinja2'
    ],
    #  entry points won't work until the config location is moved
    # entry_points='''
    #     [console_scripts]
    #     no_you_talk_to_the_hand=no_you_talk_to_the_hand:cli
    # ''',
)