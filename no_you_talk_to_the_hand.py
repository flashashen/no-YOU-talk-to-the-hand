#!/usr/bin/python

import sys, os, json, requests, socket, time, subprocess, six
from concurrent import futures

import yaml
import supervisor
from supervisor import childutils
import click
import jinja2


import logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger('nyttth')
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)




from collections import namedtuple
CheckResult = namedtuple('CheckResult', 'name status type')



def check_tunnel(tunnel_name):

    chk = get_check_cfg(tunnel_name)

    if not chk:
        return CheckResult(tunnel_name, proc_started(get_supervisor().getProcessInfo(tunnel_name)), 'supervisor')

    # log.trace('{} check config: {} .. '.format(tunnel_name, chk))
    result = None
    try:
        type = 'url'
        if 'url' in chk and chk['url']:
            rsp = requests.head(chk['url'])
            result = rsp.status_code >= 200 and rsp.status_code < 300
        else:
            type = 'socket'
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((chk['host'],int(chk['port'])))
            result = True
            s.close()
    except Exception as e:
        result = False

    # log.trace('{}: {}'.format(tunnel_name, result))
    return CheckResult(tunnel_name, result, type)


def handle_down_tunnel(check_future):

    result = check_future.result()
    # write_stderr('{} {} check: {}\n'.format(result.name, result.type, result.status))

    if not result.status:
        try:
            # start or restart depending on supervisor status. If this is a
            # check-only tunnel (no proxy defined) then skip.
            if get_proxy_cfg(result.name):
                supervisor = get_supervisor()
                proc = supervisor.getProcessInfo(result.name)
                log.info('{} is down. will make running based on supervisor state: {}'.format(result.name, proc['statename']))
                if proc_started(proc):
                    if proc_upseconds(proc) > 60:
                        log.info('restarting {}'.format(result.name))
                        supervisor.stopProcess(result.name)
                        supervisor.startProcess(result.name)
                else:
                    log.info('starting {}'.format(result.name))
                    supervisor.startProcess(result.name)
            else:
                log.debug('{} is down. Nothing to do since there is no proxy configuration.'.format(result.name))
        except Exception as e:
            log.error(str(e))


def check_dependent_tunnels(tunnel_name = None, check_only=False):

    # if tunnel_name:
    #     log.debug('{}: checking dependent tunnels ...'.format(tunnel_name))

    tunnels = get_tunnel_dependents(tunnel_name);
    if not tunnels:
        # log.debug('no dependents\n')
        return {}


    statuses = []
    with futures.ThreadPoolExecutor(max_workers=10) as executor:
        check_futures = []
        for tunnel_name in tunnels:
            future = executor.submit(check_tunnel, tunnel_name)
            if not check_only:
                future.add_done_callback(handle_down_tunnel)
            check_futures.append(future)

        statuses = [future.result() for future in futures.as_completed(check_futures)]


    # For tunnels that are up, check dependents. This could be optimized so that only dependents are
    # checked since an up dependent implies an up antecedent (provided the dependent can be checked)
    for check_result in list(statuses):
        if check_result.status or check_only:
            statuses.extend(check_dependent_tunnels(check_result.name, check_only))

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
        results = check_dependent_tunnels()
        log.debug('Check Results:')
        for result in results:
            log.debug('{} up: {}. Check type: {}'.format(result.name, result.status, result.type))
        time.sleep(10)
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



cfg = None
def get_config(config='config.yml'):

    global cfg
    if not cfg:
        log.info('reading config from {}'.format(config))
        path = config
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
            if result[2]:
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

    supstate = get_supervisor().getAllProcessInfo()
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
@click.option('--config', '-c', default='config.yml', help='specify config file')
def start(config):
    """
    Start the supervisor daemon that keeps tunnels up
    :param eproxy:
    :param iproxy:
    :return:
    """

    get_config(os.path.expanduser(config))

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


