
import os, tempfile, yaml, ConfigParser
from .. import no_you_talk_to_the_hand as ny


testcfg = {
    'tunnels': {
        'testtunnel': {
            'check': {
                'url': 'https://twitter.com/'
            },
            'proxy': {
                'host': '1.1.1.1',
                'sshuttle_args': '--no-latency-control madeuparg=someval'
            },
            'forwards': {
                'include': ['2.2.2.2'],
                'exclude': ['3.3.3.3']
            }
        }
    }
}



def test_basic_config():


    fd, path = tempfile.mkstemp()
    f = os.fdopen(fd,'w')
    f.write(yaml.dump(testcfg))
    f.flush()

    cfg = ny.get_config(path)
    ny.write_supervisor_conf()

    config = ConfigParser.ConfigParser()
    config.readfp(open(cfg['supervisor.conf']))

    # from IPython import embed
    # embed()
    print(config)
    assert '--no-latency-control madeuparg=someval -r 1.1.1.1 2.2.2.2 -x 3.3.3.3' in config.get('program:testtunnel','command')

def test_status():

    check_statuses = { check_result.name:check_result.status for check_result in ny.check_dependent_tunnels(None, True) }
    assert check_statuses

    # test_basic_config()