# https://packaging.python.org/tutorials/distributing-packages/

from setuptools import setup
import os

readme = open('README.md', 'r')
README_TEXT = readme.read()
readme.close()

setup(
    name='no_you_talk_to_the_hand',
    version='1.0.1',
    author='flashashen',
    author_email='flashashen@gmail.com',
    description='Boss your corporate network effortlessly. Automatic and organized tunneling with sshuttle + supervisord + yaml',
    license = "MIT",
    url="https://github.com/flashashen/no-YOU-talk-to-the-hand",
    classifiers= [
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Networking',
        'Topic :: System :: Networking :: Firewalls',
        'Environment :: Console',
        'Operating System :: MacOS',
        'Operating System :: POSIX :: Linux',
        'Development Status :: 5 - Production/Stable',

    ],
    platforms='osx,linux',
    keywords = "ssh vpn tunnel forward daemonn",
    long_description=README_TEXT,
    py_modules=['no_you_talk_to_the_hand'],
    install_requires=[
        'Click',
        'supervisor',
        'pyyaml',
        'jinja2'
    ],

    entry_points='''
        [console_scripts]
        nyttth=no_you_talk_to_the_hand:cli
    ''',
)