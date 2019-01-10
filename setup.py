# https://packaging.python.org/tutorials/distributing-packages/

from setuptools import setup

try:
    readme = open('README.rst', 'r')
    README_TEXT = readme.read()
    readme.close()
except:
    README_TEXT = ""

setup(
    name='no_you_talk_to_the_hand',
    version='1.0.5',
    author='flashashen',
    author_email='flashashen@gmail.com',
    description='nyttth: Boss your corporate network effortlessly. Automatic and organized tunneling with sshuttle + supervisord + yaml',
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
    keywords="ssh vpn tunnel forward daemon",
    long_description=README_TEXT,
    py_modules=['no_you_talk_to_the_hand'],
    install_requires=[
        'Click',
        'supervisor',
        'pyyaml>=4.2b1',
        'jinja2',
        'six',
        'requests>=2.20.0',
        'futures',
        'sshuttle==0.78.1'
    ],

    entry_points='''
        [console_scripts]
        nyttth=no_you_talk_to_the_hand:cli
    ''',
)
