# no, *YOU* talk to the hand!

![CircleCI](https://circleci.com/gh/flashashen/no-YOU-talk-to-the-hand.svg?style=svg)
![Python versions](https://img.shields.io/pypi/pyversions/no-YOU-talk-to-the-hand.svg)
![MIT License](https://img.shields.io/github/license/flashashen/no-YOU-talk-to-the-hand.svg)

--------------------------------------

Access all your corporate stuff and web stuff at the same time without fuss


**You want this if you're being worn out by:**

- Seeing the 'talk to the hand' page from the corporate web proxy/filter
- Tunnel/proxy setup in too many places and in too many ways
- Tunnels dropping silently
- Forgetting to manually bring up tunnels after logging onto vpn
- Re-entering ssh credentials over and over (key based auth isn't allowed everywhere)

no-YOU-talk-to-the-hand solves all these issues by providing a straight-forward combination of [sshuttle](https://github.com/sshuttle/sshuttle) for the heavy network lifting, supervisord to keep everything up and manageable, and yaml to keep it simple and organized

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


### Config.yml replaces all your tunnel scripts/aliases, ssh setup inside db tools, application specific web proxy setup, etc:

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
  
  
# Global config options  
log_level: DEBUG          # Python log level. Default is DEBUG
monitor_poll_seconds: 5   # Monitor thread wakeup (may be exceeded by a long tunnel check). Default is 20 


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
        check:
            driver: mysql+pymysql
            db:   testdb
            user: testuser
            pass: testpass
            host: 10.0.2.1
            port: '3306'
        forwards:
            # includes and excludes. items can be ips, subnets, or lists of ip/subnets.
            include:
              - *HOST_CORP_SECURE_DB
                                
  
```


## Installation
    
    $ pip install no_you_talk_to_the_hand

If pip install results in a error like 'TLSV1_ALERT_PROTOCOL_VERSION' you may first need to upgrade pip:

    $ curl https://bootstrap.pypa.io/get-pip.py | python
    
If you configure a password for any remote server then [sshpass](https://gist.github.com/arunoda/7790979) is required.

---

sshuttle requires root/admin privilege to change forward rules. If your user is prompted for sudo password, then you may encounter and error like **sudo no tty present and no askpass program specified**. A quick solution is to set the no password flag in the sudoers file. The following works currently on Macs:


    $ sudo visudo
 
.. then add 'NOPASSWD' to the admin group like this:
 
    $ %admin ALL=(ALL) NOPASSWD: ALL


---

If you check a tunnel via a sqlalchemy connection (see prod_db tunnel in sample config above) then sqlalchemy and the appropriate driver must be installed separately

## Running


### start
Start daemon to begin managing the configured tunnels (in ~/.nyttth/config.yml)

```
$ nyttth start
```


### stop
Stop daemon along with any tunnels that are running

```
$ nyttth stop
```


### status
Help:
```
    $ nyttth status --help
    
    Usage: nyttth status [OPTIONS]
    
      View status of all configured tunnels
    
    Options:
      -t, --tunnel [qadb|riskdb|itun|dbtun|etun|vpn|rfindb]
                                      specify a specific tunnel
      -s, --skip                      skip tunnel health checks
      --help                          Show this message and exit.
```
 
Example with VPN down:

``` 
    $ nyttth status
    
    Process   Depends   Proc State                  Conn Check
    ----------------------------------------------------------
    vpn                 N/A                         down      
    itun      vpn       STOPPED   Not started       skipped      
    dbtun     itun      STOPPED   Not started       skipped      
    etun      vpn       STOPPED   Not started       skipped      
    qadb      vpn       STOPPED   Not started       skipped      

```

Example with VPN up:

```
    $ nyttth status
    
    Process   Depends   Proc State                            Conn Check
    --------------------------------------------------------------------
    vpn                 N/A                                   up      
    itun      vpn       RUNNING   pid 1595, uptime 0:09:28    up      
    dbtun     itun      RUNNING   pid 1603, uptime 0:09:23    up      
    etun      vpn       RUNNING   pid 1565, uptime 0:09:33    up      
    qadb      vpn       RUNNING   pid 2692, uptime 0:00:04    up      
      
```

### tail

Help:

```
    $ nyttth tail --help
    
    Usage: nyttth tail [OPTIONS]
    
    
      Use system tail command to display logs. If a specific tunnel is not specified 
      then all logs will be tailed including the supervisord main log and the vpnmon 
      tunnel monitor process.
    
    
    Options:
      -t, --tunnel [qadb|itun|dbtun|etun|vpn]
                                      specify a specific tunnel to tail. If not
                                      specified all tunnels and the tunnel monitor
                                      (monitor) will be tailed
      -f, --wait                      wait for additional data
      -n, --lines INTEGER             number of lines to display
      --help                          Show this message and exit.


```

Tail output for a single (example) tunnel:

```
$ nyttth tail -f -t itun
  server: warning: closed channel 158 got cmd=TCP_STOP_SENDING len=0
  server: warning: closed channel 159 got cmd=TCP_STOP_SENDING len=0
  server: warning: closed channel 160 got cmd=TCP_STOP_SENDING len=0
  server: warning: closed channel 148 got cmd=TCP_STOP_SENDING len=0
  server: warning: closed channel 162 got cmd=TCP_STOP_SENDING len=0
  server: warning: closed channel 164 got cmd=TCP_STOP_SENDING len=0

```

When VPN Connects:

```
$ nyttth tail -f | grep nyttth
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

When VPN Disconnects:

```
$ nyttth tail -f | grep nyttth
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

### ctl 
Run supervisorctl console

```
$ nyttth ctl
```


## Notes

This project uses sshuttle version 0.78.1. Subsequent versions define PF (Packet Filter) exclusions in a way that breaks when there are exclusions in multiple instances of sshuttle.   

Python 3 is not supported because supervisord does not

This docs ignores whatever technical differences there are between tunnels and forwards and just uses the word 'tunnels'. 

Remote ssh servers through which trafffic is forwarded, are referred to as proxies. 

The term 'VPN' refers to a 'root' tunnel in the configuration that specifies no proxy setup or forwards. It exsits to check an external condition (reachable network endpoint)and does not really have to be a true VPN
