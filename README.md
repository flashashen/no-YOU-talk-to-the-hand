# no, *You* talk to the hand !

Work VPN killing you? Bad at organizing all your ssh tunnels? Tired of fooling with your web proxy settings? Tried to check your private email and been told by a cute corporate mascot to talk to the hand? If so, then yaml + sshuttle + supervisord make a nice combination to organize and automate all your indirections (all those wasted hours) necessitated by corporate network security. 

Works with Linux and MacOS since sshuttle does.

(I'm going to ignore whatever technical differences between tunnels, proxies forwards and just lump them all into 'tunnels')


## Features

- Establishes automatically when VPN connect is detected
- Enters passwords for you if configured to do so. ([sshpass](https://gist.github.com/arunoda/7790979) required)
- Bypass corporate web proxy without fooling with system proxy settings or Firefox (thanks to [sshuttle](https://github.com/sshuttle/sshuttle) )
- Supports any number of simultaneous tunnels (thanks to [sshuttle](https://github.com/sshuttle/sshuttle) )
- YAML based configuration for defining your tunnels
- Supports multiple root VPNs. Have multiple vpns that require separate tunnels? Define them in one place and only the relevant tunnels are established when your is connected
- Supportes nested dependencies. For example, a tunnel from an app server to database can wait until a pre-requisite tunnel to the production network is established


An example configuration excerpt:

```yaml

  # Watch for connection to corporate VPN
  vpn:
    check:
      host: *HOST_CORP_JUMP
      port: 22

  # Bypass corporate network for web browsing, skype, streaming music, etc.
  personal:
    depends: vpn
    proxy:
      host: *HOST_PERSONAL_PROXY
     forwards:
      # includes and excludes. items can be ips, subnets, or lists of ip/subnets.
      include:
        - 0/0
      exclude:
        - *SUBNETS_CORP_RESTRICTED
        
  # Forward traffic to restricted corporate subnets through the jump server.
  corp_restricted:
    depends: vpn
    proxy:
      host: *HOST_CORP_JUMP
      user: *CORP_USER
      pass: *CORP_PASS
    # verify by checking ssh access to the privileged app server
    check:
      host: *HOST_CORP_PRIVILEGED_APP
      port: 22
    forwards:
      # includes and excludes. items can be ips, subnets, or lists of ip/subnets.
      include:
        - *SUBNETS_CORP_RESTRICTED
      exclude:
        - *HOST_CORP_SEURE_DB

  # Tunnel to access a secure db server from a privliged app server. This tunnel depends 
  # on the 
  prod_db:
    depends: corporate
    proxy:
      host: *HOST_CORP_PRIVILEGED_APP
      user: *CORP_USER
      pass: *CORP_PASS
    forwards:
      # includes and excludes. items can be ips, subnets, or lists of ip/subnets.
      include:
        - *HOST_CORP_SECURE_DB
```


## Install

For now:

- git clone https://github.com/flashashen/no-YOU-talk-to-the-hand.git
- cd no-YOU-talk-to-the-hand
- pip install -r requirements.txt

*Note* If you configure a password for the remote server then [sshpass](https://gist.github.com/arunoda/7790979) is required

## Running

#### Help - Run the script with no parameters 

>python no_you_talk_to_the_hand.py

#### Start - Start the supervisord process and begin managing the configured tunnels

>python no_you_talk_to_the_hand.py start

#### Stop - Stop supervisord process and all tunnels with it

>python no_you_talk_to_the_hand.py stop

#### Tail - output a continuous tail of the vpn monitor that checks tunnel statuses and brings them up or down as needed.

>python no_you_talk_to_the_hand.py tail