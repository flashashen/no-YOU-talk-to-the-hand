# no, *You* talk to the hand !

Work VPN killing you? If you're bad at organizing your ssh tunnels and of tired manually setting up your web proxy to avoid the 'talk to the hand' message when you want to check your private email or jfiddle or similar malicious site then yaml + sshuttle + supervisord make a nice combination to organize and automate all your indirections due to corporate network security. 

(I'm going to ignore the technical differences between tunnels, proxies forwards and just lump them all into 'tunnels')


## Features

- Establishes automatically when VPN connect is detected
- Bypass corporate web proxy without fooling with system settings or Firefox (thanks to [sshuttle](https://github.com/sshuttle/sshuttle) )
- Supports any number of simultaneous tunnels/proxies/forwards (thanks to [sshuttle](https://github.com/sshuttle/sshuttle) )
- YAML based configuration for defining your forwarding / proxy rules
- Supports multiple roots. Have multiple vpns that require separate tunnels? Define them in one place and only the related tunnels are started when you connect
- Supportes nested dependencies. For example, a tunnel from an app server to database can wait until an antecedent tunnel to the production network is established via a jump server


An example configuration:

```yaml
tunnels:

  vpn:
    check:
      host: *HOST_CORP_JUMP
      port: 22


  # Forward everything not destined for a corporate networks though a non-corporate proxy
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
  corporate:
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
        - *HOST_CORP_SECURE_DB

  # another forward to access a secure server from a whitelisted machine. A common scenario is accessing
  # a database that only allows connections from specific application servers.
  whitelisted:
    depends: corporate
    proxy:
      host: *HOST_CORP_PRIVILEGED_APP
      user: *CORP_USER
      pass: *CORP_PASS
    # Skip the check config since there is no direct way to test since it's not simply ssh access we're looking
    # for, but rather access to a whiltelisted service that we don't generically know how to talk to.
    forwards:
      # includes and excludes. items can be ips, subnets, or lists of ip/subnets.
      include:
        - *HOST_CORP_SECURE_DB
```


## Install

For now:

- git clone https://github.com/flashashen/no-YOU-talk-to-the-hand.git
- pip install -r requirements.txt


## Running

#### Help - Run the script with no parameters 

>python no_you_talk_to_the_hand.py

#### Start - Start the supervisord process and begin managing the configured tunnels

>python no_you_talk_to_the_hand.py start

#### Stop - Stop supervisord process and all tunnels with it

>python no_you_talk_to_the_hand.py stop

#### Tail - output a continuous tail of the vpn monitor that checks tunnel statuses and brings them up or down as needed.

>python no_you_talk_to_the_hand.py tail