# no,*You* talk to the hand!

I got tired getting the 'talk to the hand page' from the corporate web proxy, forgetting to bring up tunnels, re-entering my credentials over and over, tunnels dropping silently, having tunnel/proxy config in too many places, etc. I was pretty miserable.

**no-YOU-talk-to-the-hand** really has solved all these issues for me, combining sshuttle + supervisord + yaml

The heaviest lifting for this project is done by **[sshuttle](https://github.com/sshuttle/sshuttle)** which is a godsend. SSH based tunneling is simple enough but sshuttle forwards all ports, supports included and excluded subnets, has powerful features I haven't even looked at yet, but best of all, works like a champ.



(Going forward, I'm going to ignore whatever technical differences there are between tunnels and forwards and just call them 'tunnels'. Remote ssh servers through which trafffic is forwarded, I'll call proxies. I refer to 'VPN' quite a bit, but technically this is just a 'root' tunnel in the configuraiton that specifies no proxy setup or forwards)

(Works with Linux and MacOS but not with Windows because that what sshuttle supports)

## What it does

- Sets up your tunnels automatically when your VPN connects
- Takes down your tunnels automatically when your VPN disconnects
- Keeps your tunnels up
- Organizes your tunnels with simple, YAML configuration 
- Enters passwords for you as needed ([sshpass](https://gist.github.com/arunoda/7790979) required)
- Supports multiple root VPNs. Have multiple vpns that require separate tunnels? Define them in one place and only the relevant tunnels are established 
- Supports any number of simultaneous tunnels (thanks to [sshuttle](https://github.com/sshuttle/sshuttle) )
- Supportes nested dependencies. For example: (qa_db, prod_db) -- depends --> (corp_private) -- depends --> (corp_vpn)


### Yaml replaces all your tunnel scripts/aliases, ssh setup with db tools, web proxy setup, etc.

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
        - *ALL_PRIVATE_ADDRESSES
        
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
  # on corp_restricted being established
  prod_db:
    depends: corp_restricted
    proxy:
      host: *HOST_CORP_PRIVILEGED_APP
      user: *CORP_USER
      pass: *CORP_PASS
    forwards:
      # includes and excludes. items can be ips, subnets, or lists of ip/subnets.
      include:
        - *HOST_CORP_SECURE_DB
```

## Running

#### Status - View status of all defined tunnels
 
VPN down:

``` 
$ python no_YOU_talk_to_the_hand.py status

Process:   run state       checkup
----------------------------------------------------
dbtun:     STOPPED         False
etun:      STOPPED         False
itun:      STOPPED         False
qadb:      STOPPED         False
rfindb:    STOPPED         False
vpnmon:    RUNNING         N/A
```

VPN up:

```
$ python no_YOU_talk_to_the_hand.py status
 
Process:   run state       checkup
----------------------------------------------------
dbtun:     RUNNING         True
etun:      RUNNING         True
itun:      RUNNING         True
qadb:      RUNNING         True
rfindb:    RUNNING         True
vpnmon:    RUNNING         N/A
```


#### Start - Start the supervisord process and begin managing the configured tunnels

```
$ python no_you_talk_to_the_hand.py start
```

#### Stop - Stop supervisord process and all tunnels with it

```
$ python no_you_talk_to_the_hand.py stop
```

#### Tail - output a continuous tail of the vpn monitor that checks tunnel statuses and brings them up or down as needed.

```
$ python no_YOU_talk_to_the_hand.py tail
2017-05-17 00:46:54,688 DEBUG nyttth: Check Results:
2017-05-17 00:46:54,689 DEBUG nyttth: vpn up: True. Check type: socket
2017-05-17 00:46:54,689 DEBUG nyttth: itun up: True. Check type: socket
2017-05-17 00:46:54,689 DEBUG nyttth: qadb up: True. Check type: supervisor
2017-05-17 00:46:54,689 DEBUG nyttth: dbtun up: True. Check type: supervisor
2017-05-17 00:46:54,689 DEBUG nyttth: etun up: True. Check type: url
2017-05-17 00:46:54,689 DEBUG nyttth: rfindb up: True. Check type: supervisor
2017-05-17 00:47:04,970 DEBUG nyttth: Check Results:
2017-05-17 00:47:04,970 DEBUG nyttth: vpn up: True. Check type: socket
2017-05-17 00:47:04,970 DEBUG nyttth: itun up: True. Check type: socket
2017-05-17 00:47:04,970 DEBUG nyttth: dbtun up: True. Check type: supervisor
2017-05-17 00:47:04,970 DEBUG nyttth: qadb up: True. Check type: supervisor
2017-05-17 00:47:04,970 DEBUG nyttth: etun up: True. Check type: url
2017-05-17 00:47:04,970 DEBUG nyttth: rfindb up: True. Check type: supervisor
```


## Install

For now:

- git clone https://github.com/flashashen/no-YOU-talk-to-the-hand.git
- cd no-YOU-talk-to-the-hand
- pip install -r requirements.txt

*Note* If you configure a password for any remote server then [sshpass](https://gist.github.com/arunoda/7790979) is required
