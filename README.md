# no, *YOU* talk to the hand!

Access all your corporate stuff and web stuff at the same time without fuss

**You want this if you're being worn out by:**
- Seeing the 'talk to the hand' page from the corporate web proxy/filter
- Re-entering ssh credentials over and over (key based auth isn't allowed everywhere)
- Tunnel/proxy setup in too many places and in too many ways
- Not having application specific tunnels (dbvis, datagrip) available from the console
- Tunnels dropping silently
- Forgetting to manually bring up tunnels after logging onto vpn

no-YOU-talk-to-the-hand really has **solved all these issues** for me, by providing a straight-forward combination of [sshuttle](https://github.com/sshuttle/sshuttle) for the heavy network lifting, supervisord to keep everything up and manageable, and yaml to keep it simple and organized

Works with Linux and MacOS but **not MS Windows** due to sshuttle though there is a workaround for windows described [here](http://sshuttle.readthedocs.io/en/stable/windows.html)


## What it does

- *Sets up your tunnels automatically* when your VPN connects
- *Takes down your tunnels automatically* when your VPN disconnects
- *Keeps your tunnels up* when they should be up
- *Organizes your tunnels* with a single, simple, YAML configuration 
- *Enters passwords for you* as needed ([sshpass](https://gist.github.com/arunoda/7790979) required for now)
- Supports *multiple VPNs (roots)*. Have different vpns that require separate tunnels? Define them in one place and only tunnels dependent on the vpn that is up are established 
- Supports any number of *simultaneous tunnels* (thanks to [sshuttle](https://github.com/sshuttle/sshuttle) )
- Supportes *nested dependencies*. For example: (qa_db, prod_db) -- depends --> (corp_private) -- depends --> (corp_vpn)


### Yaml replaces all your tunnel scripts/aliases, ssh setup inside db tools, application specific web proxy setup, etc.

```yaml

HOST_PERSONAL_PROXY: &HOST_PERSONAL_PROXY 192.168.1.X
PROXY_USER: &PROXY_USER proxy.username

CORP_USER: &CORP_USER company.username
CORP_PASS: &CORP_PASS pA$$wuuuurd
  
# Define the corporate subnets. SUBNETS_CORP_ALL encompasses addresses that will already be sent
# through your default network interace to the compnay network. This var is defined for exclusion 
# from other tunnels which will override your system defaults. SUBNETS_CORP_RESTRICTED is used
# to forward a subset of corporate traffic through a jump server in order to reach hosts that are 
# not reachable directly on the VPN. 
SUBNETS_CORP_ALL: &SUBNETS_CORP_ALL
    - "10.0.0.0/8"
SUBNETS_CORP_RESTRICTED: &SUBNETS_CORP_RESTRICTED 
    - "10.0.1.0/24"
    - "10.0.2.0/24"
    
# Define several special destinations on the corporate network. HOST_CORP_JUMP defines the host 
# through which all protected subnets must be accessed. HOST_CORP_PRIVILEGED_APP and HOST_CORP_SEURE_DB
# define an application server and database where the database can only be reached from the
# application server. Reaching the database will require a nested tunnel
HOST_CORP_JUMP: &HOST_CORP_JUMP 10.0.0.1
HOST_CORP_PRIVILEGED_APP: &HOST_CORP_PRIVILEGED_APP 10.0.1.1
HOST_CORP_SECURE_DB: &HOST_CORP_SECURE_DB 10.0.2.1
  
  
tunnels:
  
    # Watch for connection to corporate VPN. This is the 'root', external tunnel
    # In this configuraiton, if the corporate jump server is available, then the vpn is up
    vpn:
        check:
            host: *HOST_CORP_JUMP
            port: 22
    
      
    # Bypass corporate network policies for web browsing, skype, streaming music, etc. 
    # You must have a proxy server available that is outside the corporate network. If 
    # you don't have one, this project is still useful for accessing restricted 
    # resources within the corporate network.
    personal:
        depends: vpn
        proxy:
            host: *HOST_PERSONAL_PROXY
            user: *PROXY_USER
            pass:
        check:
            # instead of an ip and port, a check target can be a url for an http check
            url: https://twitter.com/

        forwards:
            # includes and excludes. items can be ips, subnets, or lists of ip/subnets.
            include:
                # By default, forward everything through the personal proxy
                - 0/0
            exclude:
                # exclude home network and anything corporate 
                - 192.168.0.0/16
                - *SUBNETS_CORP_ALL
                   
    # Forward traffic destined for restricted subnets through a corporate jump server.
    corp_sec:
        depends: vpn
        proxy:
            host: *HOST_CORP_JUMP
            user: *CORP_USER
            pass: *CORP_PASS
        # verify by checking ssh access to the privileged app server
        check:
            # If the application server is reachable, this tunnel is up
            host: *HOST_CORP_PRIVILEGED_APP
            port: 22
        forwards:
            # Include anything destined for a secured corporate subnet
            include:
              - *SUBNETS_CORP_RESTRICTED
   
    # Tunnel to access a secure db server from a privileged app server. This tunnel depends 
    # on corp_restricted being established. For traffic destined for the DB, this rule will 
    # fire first and the traffic will be forwarded through the APP server, however traffic 
    # destined for the APP server is forwarded through the JUMP server. 
    prod_db:
        depends: corp_sec
        proxy:
            host: *HOST_CORP_PRIVILEGED_APP
            user: *CORP_USER
            pass: *CORP_PASS
        forwards:
            # includes and excludes. items can be ips, subnets, or lists of ip/subnets.
            include:
              - *HOST_CORP_SECURE_DB
                                
  
```


## Installation

```pip install no_you_talk_to_the_hand```


*Note* If you configure a password for any remote server then [sshpass](https://gist.github.com/arunoda/7790979) is required

## Running

Below are some sample commands.

**Note:** Before running a configuration file called config.yml must be created in the project directory. Look at sample_config.yml as a start.


#### Start - Start the supervisord process and begin managing the configured tunnels

```
$ nyttth start
```


#### Stop - Stop supervisord process and all tunnels with it

```
$ nyttth stop
```


#### Status - View status of all defined tunnels
 
when VPN is down:

``` 
$ nyttth status

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
$ nyttth status

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
$ nyttth tail
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


## Notes

This docs ignores whatever technical differences there are between tunnels and forwards and just uses the word 'tunnels'. 

Remote ssh servers through which trafffic is forwarded, are referred to as proxies. 

The term 'VPN' refers to a 'root' tunnel in the configuration that specifies no proxy setup or forwards. It exsits to check an external condition (reachable network endpoint)and does not really have to be a true VPN
