# no,*YOU* talk to the hand!


**You want this if you're being worn out by:**
- Seeing the 'talk to the hand page' from the corporate web proxy
- Re-entering ssh credentials over and over (key based auth isn't allowed everywhere)
- Tunnel/proxy setup in too many places and in too many ways
- Not having application specific tunnels (dbvis, datagrip) available from the console
- Tunnels dropping silently
- Forgetting to manually bring up tunnels after logging onto vpn

no-YOU-talk-to-the-hand really has **solved all these issues** for me, by providing a straight-forward combination of [sshuttle](https://github.com/sshuttle/sshuttle) for the heavy network lifting, supervisord to keep everything up and manageable, and yaml to keep it simple and organized

Works with Linux and MacOS but **not MS Windows** because that is what sshuttle supports

## What it does

- *Sets up your tunnels automatically* when your VPN connects
- *Takes down your tunnels automatically* when your VPN disconnects
- *Keeps your tunnels up* when they should be up
- *Organizes your tunnels* with a single, simple, YAML configuration 
- *Enters passwords for you* as needed ([sshpass](https://gist.github.com/arunoda/7790979) required for now)
- Supports *multiple root VPNs*. Have different vpns that require separate tunnels? Define them in one place and only tunnels dependent on the vpn that is up are established 
- Supports any number of *simultaneous tunnels* (thanks to [sshuttle](https://github.com/sshuttle/sshuttle) )
- Supportes *nested dependencies*. For example: (qa_db, prod_db) -- depends --> (corp_private) -- depends --> (corp_vpn)


### Yaml replaces all your tunnel scripts/aliases, ssh setup inside db tools, application specific web proxy setup, etc.

```yaml
    
# Watch for connection to corporate VPN. This is the 'root', external tunnel
vpn:
    check:
        host: *HOST_CORP_JUMP
        port: 22

# Bypass corporate network for web browsing, skype, streaming music, etc. 
# Anything at a public ip.
personal:
depends: vpn
proxy:
  host: *HOST_PERSONAL_PROXY
  port: 22
forwards:
    # includes and excludes. items can be ips, subnets, or lists of ip/subnets.
    include:
    - 0/0
    exclude:
    - *ALL_PRIVATE_ADDRESSES
    
# Forward traffic destined for restricted subnets through a corporate jump server.
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

Below are some sample commands.

**Note:** Before running a configuration file called config.yml must be created in the project directory. Look at sample_config.yml as a start.


#### Start - Start the supervisord process and begin managing the configured tunnels

```
$ python no_you_talk_to_the_hand.py start
```


#### Stop - Stop supervisord process and all tunnels with it

```
$ python no_you_talk_to_the_hand.py stop
```


#### Status - View status of all defined tunnels
 
when VPN is down:

``` 
$ python no_YOU_talk_to_the_hand.py status

Process   Depends   State     Check     
----------------------------------------
vpn                 N/A       down      
rfindb    itun      STOPPED   skipped   
dbtun     vpn       STOPPED   skipped   
etun      vpn       STOPPED   skipped   
itun      vpn       STOPPED   skipped   
qadb      vpn       STOPPED   skipped   
```

when VPN is up:

```
$ python no_YOU_talk_to_the_hand.py status

Process   Depends   State     Check     
----------------------------------------
vpn                 N/A       up        
rfindb    itun      RUNNING   up        
dbtun     vpn       RUNNING   up        
etun      vpn       RUNNING   up        
itun      vpn       RUNNING   up        
qadb      vpn       RUNNING   up        
```

#### Tail - Tail the tunnel monitor that checks tunnel statuses and brings them up or down as needed.

when VPN Disconnects:

```
$ python no_YOU_talk_to_the_hand.py tail
2017-05-17 11:51:44,701 DEBUG nyttth: checking tunnels
2017-05-17 11:51:55,000 DEBUG nyttth: checking tunnels
2017-05-17 11:52:05,265 DEBUG nyttth: checking tunnels
2017-05-17 11:52:07,269 DEBUG nyttth: vpn is down
2017-05-17 11:52:07,274 INFO nyttth: qadb depends on vpn which is down. stopping
2017-05-17 11:52:07,281 INFO nyttth: itun depends on vpn which is down. stopping
2017-05-17 11:52:07,286 INFO nyttth: rfindb depends on itun which is down. stopping
2017-05-17 11:52:07,292 INFO nyttth: dbtun depends on vpn which is down. stopping
2017-05-17 11:52:07,299 INFO nyttth: etun depends on vpn which is down. stopping
2017-05-17 11:52:17,306 DEBUG nyttth: checking tunnels
2017-05-17 11:52:19,310 DEBUG nyttth: vpn is down
2017-05-17 11:52:29,324 DEBUG nyttth: checking tunnels
2017-05-17 11:52:31,329 DEBUG nyttth: vpn is down
2017-05-17 11:52:41,340 DEBUG nyttth: checking tunnels
2017-05-17 11:52:43,345 DEBUG nyttth: vpn is down
```

when VPN Connects:

```
2017-05-17 11:52:53,357 DEBUG nyttth: checking tunnels
2017-05-17 11:52:53,497 INFO nyttth: qadb is down. starting
2017-05-17 11:52:53,498 INFO nyttth: dbtun is down. starting
2017-05-17 11:52:53,907 INFO nyttth: etun is down. starting
2017-05-17 11:52:55,493 INFO nyttth: itun is down. starting
2017-05-17 11:53:06,527 DEBUG nyttth: checking tunnels
2017-05-17 11:53:06,814 INFO nyttth: rfindb is down. starting
2017-05-17 11:53:17,826 DEBUG nyttth: checking tunnels
2017-05-17 11:53:28,129 DEBUG nyttth: checking tunnels

```


## Install

For now:

- git clone https://github.com/flashashen/no-YOU-talk-to-the-hand.git
- cd no-YOU-talk-to-the-hand
- pip install -r requirements.txt

*Note* If you configure a password for any remote server then [sshpass](https://gist.github.com/arunoda/7790979) is required

## Notes

This docs ignores whatever technical differences there are between tunnels and forwards and just uses the word 'tunnels'. 

Remote ssh servers through which trafffic is forwarded, are referred to as proxies. 

VP, but technically this is just a 'root' tunnel in the configuration that specifies no proxy setup or forwards
