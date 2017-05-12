#!/usr/bin/python

import sys, os, json, requests, socket, time, subprocess, six
from concurrent import futures

import yaml
import supervisor
from supervisor import childutils
import click
import jinja2



def write_stdout(s):
    # only eventlistener protocol messages may be sent to stdout
    sys.stdout.write(s)
    sys.stdout.flush()

def write_stderr(s):
    sys.stderr.write(s)
    sys.stderr.flush()

#
#
# def check(target, timeout=2):
#
#     try:
#         # if not port is provided assume http(s)
#         if len(target) == 1 or not target[1]:
#             rsp = requests.head(target[0])
#             return rsp.status_code >= 200 and rsp.status_code < 300
#
#         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         s.settimeout(timeout)
#         s.connect(target)
#         s.close()
#     except:
#         return False
#
#     return True



def check_tunnel(tunnel_name):

    chk = get_check_cfg(tunnel_name)

    if not chk:
        return 'None'

    # write_stderr('checking tunnel with config: {}'.format(chk))
    try:
        if 'url' in chk and chk['url']:
            rsp = requests.head(chk['url'])
            return rsp.status_code >= 200 and rsp.status_code < 300

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((chk['host'],int(chk['port'])))
        s.close()
    except Exception as e:
        # write_stderr(str(e))
        return False

    return True



def check_dependent_tunnels(tunnel_name = None, check_only=False):

    write_stderr('checking tunnels dependent on {} ... '.format(tunnel_name))

    tunnels = get_tunnel_dependents(tunnel_name);

    if not tunnels:
        write_stderr('no dependents\n')
        return {}

    statuses = {}
    with futures.ThreadPoolExecutor(max_workers=10) as executor:
        check_futures = { tunnel_name : (executor.submit(check_tunnel, tunnel_name)) for tunnel_name in tunnels }
        statuses = { name : check_futures[name].result() for name in check_futures }

    write_stderr('statuses: {}\n'.format(statuses))

    supervisor = get_supervisor()
    for name, status in statuses.copy().iteritems():
        write_stderr('{} check status: {}\n'.format(name, status))

        # if no check is defined, then just use the supervisor state instead
        if status == 'None':
           status =  started(supervisor.getProcessInfo(name))

        if status or check_only:
            statuses.update(check_dependent_tunnels(name))
        else:
            try:
                # start or restart depending on supervisor status. If this is a
                # check-only tunnel (no proxy defined) then skip.
                if get_proxy_cfg(name):
                    proc = supervisor.getProcessInfo(name)
                    write_stderr('{} is down. will make running based on supervisor state: {}\n'.format(name, proc['statename']))
                    if started(proc):
                        if upseconds(proc) > 60:
                            write_stderr('restarting {}\n'.format(proc['name']))
                            supervisor.stopProcess(proc['name'])
                            supervisor.startProcess(proc['name'])
                    else:
                        write_stderr('starting {}\n'.format(proc['name']))
                        supervisor.startProcess(proc['name'])
                else:
                    write_stderr('{} is down. Nothing to do since there is no proxy configuration.\n'.format(name))
            except Exception as e:
                write_stderr(str(e))

    return statuses


# def emit_status_changes():
#
#     while True:
#         write_stderr('checking conditions..')
#         stats = {}
#         stats['vpn'] = check(VPN_CHECK_TARGET)
#
#         if not stats['vpn'] :
#             stats['etun'] = False
#             stats['itun'] = False
#         else:
#             stats['etun'] = check(ETUN_CHECK_TARGET)
#             stats['itun'] = check(ITUN_CHECK_TARGET)
#
#         write_stderr(json.dumps(stats) + '\n')
#         write_stdout('<!--XSUPERVISOR:BEGIN-->{}<!--XSUPERVISOR:END-->'.format(json.dumps(stats)))
#         time.sleep(5)
#
#





def started(proc):
    write_stderr('eval state for {} started status: {}\n'.format(proc['name'], proc['statename']))
    return proc['statename'] in ['RUNNING', 'STARTING', 'BACKOFF']

def upseconds(proc):
    desc = proc['description']
    if proc['statename'] == 'RUNNING' and 'uptime' in desc:
        h, m, s = desc.split('uptime ')[1].split(':')
        return int(s) + 60 * (int(m) + 60 * int(h))
    return 0

# def make_running(proc, supervisor):
#     if started(proc):
#         if upseconds(proc) > 60:
#             write_stderr('restarting {}\n'.format(proc['name']))
#             supervisor.stopProcess(proc['name'])
#             supervisor.startProcess(proc['name'])
#     else:
#         write_stderr('starting {}\n'.format(proc['name']))
#         supervisor.startProcess(proc['name'])




def vpnmonitor():

    # headers, payload = childutils.listener.wait()
    # childutils.listener.ready()
    # check_dependent_tunnels()
    # childutils.listener.ok()

    # vpnlaststatus = None
    # rpc = childutils.getRPCInterface({'SUPERVISOR_SERVER_URL':'unix:///tmp/vpnsupervisor.sock'})
    #
    while True:
        #
        #
        headers, payload = childutils.listener.wait()
        check_dependent_tunnels()
        time.sleep(6)
        childutils.listener.ok()
    #
    #     # write_stderr('headers:' + str(headers) + "'\n")
    #     # write_stderr('payload:' + payload + "'\n")
    #
    #     if headers['eventname'] == 'PROCESS_COMMUNICATION_STDOUT':
    #
    #         pheaders, pdata = childutils.eventdata(payload)
    #         # write_stderr('secondary header: ' + str(pheaders) + "'\n")
    #         stats = json.loads(pdata)
    #
    #         procs = {proc['name'] : proc for proc in rpc.supervisor.getAllProcessInfo()}
    #         write_stderr('stats: ' + str(stats) + "'\n")
    #
    #         if not stats['vpn']:
    #             if started(procs['itun']):
    #                 write_stderr('vpn is down. stopping internal tunnel\n')
    #                 rpc.supervisor.stopProcess('itun')
    #             if started(procs['etun']):
    #                 write_stderr('vpn is down. stopping external tunnel\n')
    #                 rpc.supervisor.stopProcess('etun')
    #
    #         else:
    #             # write_stderr('value of itun, etun are {} and {}\n'.format(stats['itun'], stats['etun']))
    #             if not stats['itun']:
    #                 make_running(procs['itun'], rpc.supervisor)
    #
    #             if not stats['etun']:
    #                 make_running(procs['etun'], rpc.supervisor)
    #
    #     childutils.listener.ok()


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





cfg = None
def get_config():

    global cfg
    if not cfg:
        path = 'config.yml'
        cfg = dict()
        if os.path.isfile(path):
            with open(path, 'r') as stream:
                cfg = yaml.load(stream)

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
    return jinja2.Environment(loader=jinja2.FileSystemLoader('./')).get_template('supervisord.conf.j2').render(ctx)


def write_supervisor_conf():
    with open('supervisord.conf', 'w') as f:
        f.write(generate_supervisor_conf(get_tmpl_ctx()))


def get_supervisor():
    return childutils.getRPCInterface({'SUPERVISOR_SERVER_URL':'unix:///tmp/vpnsupervisor.sock'}).supervisor


@click.group()
def cli():
    """This script controls a supervisord daemon, which in turns controls processes that manage
       tunnels that should run whenever the GD vpn is connected

       The main inputs required are the proxy targets. These can be provided via start command parameters
        (>nyttth start --help) or in ~/.nyttth.yml. An example config file looks like this

        \b
        ETUN_PROXY_TARGET: 192.168.1.12
        ITUN_PROXY_TARGET: paul.nelson@fsd-jp01.an.local
        ITUN_PROXY_PASSWORD: mypass
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


@cli.command('tail')
def tail():
    print(childutils.getRPCInterface({'SUPERVISOR_SERVER_URL':'unix:///tmp/vpnsupervisor.sock'}).supervisor.tailProcessStderrLog('vpnmon', 0, 1000)[0])

@cli.command('status')
def tail():

    check_statuses = check_dependent_tunnels(None, True)

    supstate = childutils.getRPCInterface({'SUPERVISOR_SERVER_URL':'unix:///tmp/vpnsupervisor.sock'}).supervisor.getAllProcessInfo()
    print '\nProcess:\trun state\tup\n----------------------------------------------------'
    for proc in supstate:
        print '{}:\t\t{}\t\t{}'.format(
            proc['name'],proc['statename'],
            check_statuses[proc['name']] if proc['name'] in check_statuses else 'N/A')
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
def start():
    """
    Start the supervisor daemon that keeps tunnels up
    :param eproxy:
    :param iproxy:
    :return:
    """

    # if supervisor_already_running():
    #     print 'Supervisord is already running.'
    #     return 0

    #
    # config = get_config()
    write_supervisor_conf()

    # for tunnel in config['tunnels']:
    #     p = get_proxy_cfg(tunnel)
    #     if 'pass' in p and p['pass']
    #

    try :

        subprocess.call("supervisord")

    except Exception as e:
        if 'already listening' in e.output:
            print('Supervisor appears to already be running')
        else:
            print e.output

        return 1

    print("Supervisor is running. Run supervisorctl for an interactive shell if you're curious")


if __name__ == '__main__':
    cli()


