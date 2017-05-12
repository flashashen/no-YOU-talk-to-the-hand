from setuptools import setup
import os

setup(
    name='no_you_talk_to_the_hand',
    version='0.2',
    py_modules=['no_you_talk_to_the_hand'],
    install_requires=[
        'Click',
        'supervisor',
        'pyyaml',
        'jinja2'
    ],
    entry_points='''
        [console_scripts]
        no_you_talk_to_the_hand=no_you_talk_to_the_hand:cli
    ''',
    # data_files=[
    #     ('etc', ['config.yml'])
    # ]
    package_data={
        '': ['.subnets*'],
        '': ['supervisord.conf'],
    }

)