# no You talk to the hand !

This script controls a supervisord daemon, which in turns controls processes that manage
tunnels that should run whenever the GD vpn is connected

The main inputs required are the proxy targets. These can be provided via start command parameters
(>nyttth start --help) or in ~/.nyttth.yml. An example config file looks like this


ETUN_PROXY_TARGET: 192.168.1.12
ITUN_PROXY_TARGET: paul.nelson@fsd-jp01.an.local
ITUN_PROXY_PASSWORD: mypass


## Install

A few python dependencies are required. To install them and also to install the OS script run the following
pip install -r requirements.txt


## Running

#### Help

>python no_you_talk_to_the_hand.py

#### Start

>python no_you_talk_to_the_hand.py start

#### Stop

>python no_you_talk_to_the_hand.py stop
