#!/usr/bin/python

import sys, os, requests, socket, time, subprocess, six
from concurrent import futures

import yaml
from supervisor import childutils
import click
import jinja2


import logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = None



SAMPLE_CONFIG = """
#
#
#     Sample configuration for 'no, YOU talk to the hand' (nyttth)
#
#



#
#     Define variables
#

CORP_USER: &CORP_USER youruser
CORP_PASS: &CORP_PASS yourpass


URL_PERSONAL_PROXY_CHECK: &URL_PERSONAL_PROXY_CHECK https://twitter.com/

SUBNETS_LOCAL: &SUBNETS_LOCAL
    - 192.168.0.0/16

SUBNETS_CORP_RESTRICTED: &SUBNETS_CORP_RESTRICTED
    # Forward all private addresses as an example
    - 172.16.0.0/12
    - 10.0.0.0/8



# The jump server to access subnets not provided by simple VPN access
HOST_CORP_JUMP: &HOST_CORP_JUMP 10.1.1.1

# Once we can access the internal subnet though the initial jump server, we need
# another forward to access a secure db instance via a privileged app server
HOST_CORP_PRIVILEGED_APP: &HOST_CORP_PRIVILEGED_APP 10.1.2.1
HOST_CORP_SECURE_DB: &HOST_CORP_SECURE_DB 10.1.3.0/24

# Finally, a proxy server for all other traffic like web browsing and skype.
HOST_PERSONAL_PROXY: &HOST_PERSONAL_PROXY 192.168.1.2


log_level: DEBUG

#
#   Setup the forwarding rules (tunnels/proxies)
#
tunnels:

  # vpn is an external condition that we simply check for
  vpn:
    check:
      host: *HOST_CORP_JUMP
      port: 22

  # If vpn is up, the forward traffic to restricted corporate subnets through the jump server.
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


  # Forward everything not destined for a corporate networks though a non-corporate proxy
  personal:
    depends: vpn
    proxy:
      host: *HOST_PERSONAL_PROXY
      user:
      pass:
    # check access to Twitter to determine if corp web proxy is being properly bypassed
    check:
      # instead of an ip and port, a check target can be a url for an http check
      url: *URL_PERSONAL_PROXY_CHECK
    forwards:
      # includes and excludes. items can be ips, subnets, or lists of ip/subnets.
      include:
        - 0/0
      exclude:
        - *SUBNETS_LOCAL
        - *SUBNETS_CORP_RESTRICTED
        - *HOST_CORP_SECURE_DB
"""


SUPERVISOR_TEMPLATE = """
[unix_http_server]
file=/tmp/vpnsupervisor.sock   ; (the path to the socket file)

[supervisord]
logfile=/tmp/supervisord.log ; (main log file;default $CWD/supervisord.log)
logfile_maxbytes=50MB        ; (max main logfile bytes b4 rotation;default 50MB)
logfile_backups=10           ; (num of main logfile rotation backups;default 10)
loglevel=info                ; (log level;default info; others: debug,warn,trace)
pidfile=/tmp/supervisord.pid ; (supervisord pidfile;default supervisord.pid)
nodaemon=false               ; (start in foreground if true;default false)
minfds=1024                  ; (min. avail startup file descriptors;default 1024)
minprocs=200                 ; (min. avail process descriptors;default 200)
;environment=SSHPASS=$SSHPASS


; the below section must remain in the config file for RPC
; (supervisorctl/web interface) to work, additional interfaces may be
; added by defining them in separate rpcinterface: sections
[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///tmp/vpnsupervisor.sock ; use a unix:// URL  for a unix socket


{% for tunnel in tunnels %}
[program:{{ tunnel.name }}]
command=bash -c "{{tunnel.proxy.wrap_cmd}} sshuttle -r {{ tunnel.proxy.target}}{%for include in tunnel.forwards.include%} {{include}}{%endfor%} {%for exclude in tunnel.forwards.exclude%}-x {{exclude}} {%endfor%}"
autostart=false
autorestart=false
redirect_stderr=true
startretries=2
{% endfor %}


[program:vpnmon]
command=python -c 'import no_you_talk_to_the_hand as hand; hand.vpnmonitor()'
autostart=true
autorestart=true
redirect_stderr=true
"""


def init_logging(level = logging.INFO):
    global log
    log = logging.getLogger('nyttth')
    log.setLevel(level)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

init_logging()


from collections import namedtuple
CheckResult = namedtuple('CheckResult', 'name status type')



def get_check_type(tun_chk_cfg):
    if not tun_chk_cfg:
        return 'supervisor'
    elif 'url' in tun_chk_cfg and tun_chk_cfg['url']:
        return 'url'
    else:
        return 'socket'


def check_tunnel(tunnel_name):

    chk = get_check_cfg(tunnel_name)
    type = get_check_type(chk)

    timeout = 2

    # log.trace('{} check config: {} .. '.format(tunnel_name, chk))
    result = None
    try:
        if type == 'supervisor':
            result = 'up' if proc_started(get_supervisor().getProcessInfo(tunnel_name)) else 'down'
        elif type == 'url':
            rsp = requests.head(chk['url'], timeout=timeout)
            result = 'up' if rsp.status_code >= 200 and rsp.status_code < 300 else 'down'
        elif type == 'socket':
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((chk['host'],int(chk['port'])))
            result = 'up'
            s.close()
        else:
            result =  'invalid'
    except Exception as e:
        result = 'down'

    # log.trace('{}: {}'.format(tunnel_name, result))
    return CheckResult(tunnel_name, result, type)


def handle_down_tunnel(check_future):

    result = check_future.result()
    # write_stderr('{} {} check: {}\n'.format(result.name, result.type, result.status))

    if result.status == 'down':
        try:
            # start or restart depending on supervisor status. If this is a
            # check-only tunnel (no proxy defined) then skip.
            if get_proxy_cfg(result.name):
                supervisor = get_supervisor()
                proc = supervisor.getProcessInfo(result.name)
                if proc_started(proc):
                    if proc_upseconds(proc) > 60:
                        log.info('{} is down. restarting'.format(result.name))
                        supervisor.stopProcess(result.name)
                        supervisor.startProcess(result.name)
                else:
                    log.info('{} is down. starting'.format(result.name))
                    supervisor.startProcess(result.name)
            else:
                log.debug('{} is down'.format(result.name))
        except Exception as e:
            log.error(str(e))


def stop_dependent_tunnels(tunnel_name):
    for tunnel in get_tunnel_dependents(tunnel_name):
        if proc_started(get_supervisor().getProcessInfo(tunnel)):
            log.info('{} depends on {} which is down. stopping'.format(tunnel, tunnel_name))
            get_supervisor().stopProcess(tunnel)
            # continue stopping recursively
            stop_dependent_tunnels(tunnel)


def check_dependent_tunnels(check_result_parent = None, check_only=False):

    tunnels = get_tunnel_dependents(
        check_result_parent.name if check_result_parent else None);

    if not tunnels:
        # log.debug('no dependents\n')
        return {}


    statuses = []
    if check_result_parent and not check_result_parent.status == 'up':
        # If parent is not up, then skip children
        statuses = [CheckResult(tunnel_name,'skipped',get_check_type(get_check_cfg(tunnel_name)))
            for tunnel_name in tunnels ]
    else:
        # Use a thread pool to perform the checks of child tunnels
        with futures.ThreadPoolExecutor(max_workers=10) as executor:
            check_futures = []
            for tunnel_name in tunnels:
                future = executor.submit(check_tunnel, tunnel_name)
                if not check_only:
                    future.add_done_callback(handle_down_tunnel)
                check_futures.append(future)

            statuses = [future.result() for future in futures.as_completed(check_futures)]


    # Recurse though child tunnels. If this tunnel is down then just stop everything depedning on it
    for check_result in list(statuses):
        if check_result.status != 'down' or check_only:
            statuses.extend(check_dependent_tunnels(check_result, check_only))
        else:
            # Make sure dependent tunnels are stopped. Don't bother gathering status as we may no longer use it
            stop_dependent_tunnels(check_result.name)

    return statuses



def proc_started(proc):
    # log.debug('eval state for {} started status: {}\n'.format(proc['name'], proc['statename']))
    return proc['statename'] in ['RUNNING', 'STARTING', 'BACKOFF']

def proc_upseconds(proc):
    desc = proc['description']
    if proc['statename'] == 'RUNNING' and 'uptime' in desc:
        h, m, s = desc.split('uptime ')[1].split(':')
        return int(s) + 60 * (int(m) + 60 * int(h))
    return 0


def vpnmonitor():

    while True:
        #
        #
        # headers, payload = childutils.listener.wait()
        log.debug('checking tunnels')
        results = check_dependent_tunnels()
        # for result in results:
        #     log.debug('{} check: {}'.format(result.name, result.status))
        time.sleep(6)
        # childutils.listener.ok()



# def supervisor_already_running():
#     import socket
#     running = False
#     s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
#     try:
#         s.connect('unix:///tmp/vpnsupervisor.sock')
#         running = True
#     except Exception as e:
#         print e
#     finally:
#         s.close()
#
#     return running


def propmt_yn():
    # raw_input returns the empty string for "enter"
    yes = set(['yes','y', 'ye', ''])
    no = set(['no','n'])

    while True:
        choice = raw_input().lower()
        if choice in yes:
            return True
        elif choice in no:
            return False
        else:
            sys.stdout.write("Please respond with 'yes' or 'no'")


cfg = None
def get_config(config='~/.nyttth/config.yml'):

    global cfg
    if not cfg:
        cfgpath = os.path.expanduser(config)
        log.debug('reading config from {}'.format(cfgpath))
        cfg = dict()

        if os.path.isfile(cfgpath):
            with open(cfgpath, 'r') as stream:
                cfg = yaml.load(stream)
        else:
            print 'config not found at {}. Create y/n?'.format(cfgpath)
            if propmt_yn():
                import errno
                try:
                    os.makedirs(os.path.dirname(cfgpath))
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise
                with open(cfgpath, 'w') as cfg_file:
                    cfg_file.write(SAMPLE_CONFIG)
                print 'Sample configuration has been written to {}.\n You will need to edit '.format(cfgpath) + \
                      'this configuration with real values from your networking environment. Exiting.'
            else:
                print 'Exiting'
            exit()
        if 'log_level' in cfg:
            # print('setting log level to {}'.format(cfg['log_level']))
            log.setLevel(logging.getLevelName(cfg['log_level']))

        cfg['basedir'] = os.path.dirname(cfgpath)
        cfg['supervisor.conf'] = os.path.join(cfg['basedir'],'supervisord.conf')

    return cfg

def get_proxy_cfg(tunnel_name):
    return get_config()['tunnels'][tunnel_name]['proxy'] if 'proxy' in get_config()['tunnels'][tunnel_name] else {}

def get_check_cfg(tunnel_name):
    return get_config()['tunnels'][tunnel_name]['check'] if 'check' in get_config()['tunnels'][tunnel_name] else {}

def get_forwards_cfg(tunnel_name):
    return get_config()['tunnels'][tunnel_name]['forwards']

def get_includes(tunnel_name):
    forwards = get_forwards_cfg(tunnel_name)
    if 'include' in forwards:
        # flatten accounting for strings as well as lists in the outer includes list
        return [item for sublist in forwards['include'] for item in ([sublist] if isinstance(sublist, six.string_types) else sublist) ]
    return []

def get_excludes(tunnel_name):
    forwards = get_forwards_cfg(tunnel_name)
    if 'exclude' in forwards:
        # flatten accounting for strings as well as lists in the outer includes list
        return [item for sublist in forwards['exclude']  for item in ([sublist] if isinstance(sublist, six.string_types) else sublist) ]
    return []


def get_tunnel_dependents(tunnel_name = None):

    tunnels = get_config()['tunnels']
    if not tunnel_name:
        return [ x for x in tunnels if 'depends' not in tunnels[x] or not tunnels[x]['depends'] ]
    else:
        return [ x for x in tunnels if 'depends' in tunnels[x] and tunnels[x]['depends'] == tunnel_name ]








def get_tmpl_ctx_proxy(tunnel_name):

    proxy = get_proxy_cfg(tunnel_name)
    derived = {}
    derived['wrap_cmd'] = 'sshpass -p {}'.format(proxy['pass']) if 'pass' in proxy and proxy['pass'] else ''
    derived['target'] = '{user}@{host}'.format(**proxy) if 'user' in proxy and proxy['user'] else proxy['host']
    return derived


def get_tmpl_ctx():

    return { 'tunnels' :
        [{
            'name': item,
            'proxy': get_tmpl_ctx_proxy(item),
            'forwards': {'include': get_includes(item), 'exclude': get_excludes(item)}}
        for item in get_config()['tunnels'] if 'proxy' in get_config()['tunnels'][item] ]}



def generate_supervisor_conf(ctx):
    return jinja2.Template(SUPERVISOR_TEMPLATE).render(ctx)


def write_supervisor_conf():
    with open(cfg['supervisor.conf'], 'w') as f:
        f.write(jinja2.Template(SUPERVISOR_TEMPLATE).render(get_tmpl_ctx()))


def get_supervisor():
    return childutils.getRPCInterface({'SUPERVISOR_SERVER_URL':'unix:///tmp/vpnsupervisor.sock'}).supervisor


@click.group()
def cli():
    """This script controls a supervisord daemon, which in turns controls processes that manage
       tunnels that should run whenever the vpn is connected
   """
    pass

# @cli.command('install')
# def install():
#     """
#     Run this to install dependencies and a script runnable from anywhere. It must be run from src directory
#
#     :return:
#     """
#     output = subprocess.check_output("pip install --editable .")



@cli.command('refreshconfig')
def write_config():
    write_supervisor_conf()
    get_supervisor().reloadConfig()




def write_stdout(s):
    sys.stdout.write(s)
    sys.stdout.flush()


@cli.command('tail')
@click.option('--tunnel', '-t', default='vpnmon', help='specify a specific tunnel to tail. If not specified the vpn monitor will be tailed')
def tail(tunnel):

    numbytes = 100
    result = get_supervisor().tailProcessStdoutLog(tunnel, 0, numbytes)
    offset = result[1]

    while True:
        result = get_supervisor().tailProcessStdoutLog(tunnel, offset, numbytes)
        # If more data was written to the log or if we've failed to read whats already there
        if result[1] > offset or result[2] :
            # if result[2]:
                # All the data has not been read. Re-read entire buffer. If the entire buffer is not
                # read then we get the latter part and the data at teh beginning (at the offset) is
                # skipped
            result = get_supervisor().tailProcessStdoutLog(tunnel, offset, result[1]-offset)

            # all the data should have been read. Set the new offset to the end of the file
            offset = result[1]
            write_stdout(result[0])

        else:
            time.sleep(0.5)



@cli.command('status')
def status():

    check_statuses = { check_result.name:check_result.status for check_result in check_dependent_tunnels(None, True) }
    sup_states = { proc['name']:proc for proc in get_supervisor().getAllProcessInfo() }

    out = [ {'name':name,
            'state':sup_states[name]['statename'] if name in sup_states else 'N/A',
            'checkup': check_statuses[name],
            'depends':config['depends'] if 'depends' in config else ''}
        for name, config in get_config()['tunnels'].iteritems() ]


    out.sort()
    longest = len(max(get_config()['tunnels'], key=lambda t: len(t)))
    header = 'Process'.ljust(longest + 4) + 'Depends'.ljust(10) + 'State'.ljust(10) + 'Check'.ljust(10)

    print('')
    print(header)
    print ''.ljust(len(header),'-')
    for info in sorted(out,key=lambda x: x['depends']):
        print info['name'].ljust(longest + 4) + info['depends'].ljust(10) + info['state'].ljust(10) + info['checkup'].ljust(10)
    print('')


@cli.command('stop')
def stop():
    """
    Shutdown the supervisor
    :return:
    """
    try:
        childutils.getRPCInterface({'SUPERVISOR_SERVER_URL':'unix:///tmp/vpnsupervisor.sock'}).supervisor.shutdown()
    except Exception as e:
        if not 'No such' in str(e):
            raise
        else:
            print 'Supervisor does not appear to be running'
            return

    print('Supervisor stopped')



@cli.command('start')
@click.option('--config', '-c', default='~/.nyttth/config.yml', help='specify config file')
def start(config):
    """
    Start the supervisor daemon that keeps tunnels up
    :param eproxy:
    :param iproxy:
    :return:
    """

    cfg = get_config(config)
    write_supervisor_conf()


    try :
        subprocess.call("supervisord".format(cfg['basedir']), cwd=cfg['basedir'])

    except Exception as e:
        if 'already listening' in str(e):
            print('Supervisor appears to already be running')
        else:
            print str(e)

        return 1

    print("Supervisor is running.")


if __name__ == '__main__':
    cli()


