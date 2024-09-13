#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import sys

from oslo_config import cfg
from oslo_log import log as logging
from ovn_octavia_provider.common import config as ovn_conf
from ovn_octavia_provider import driver

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def setup_conf():
    conf = cfg.CONF
    ovn_conf.register_opts()
    logging.register_options(CONF)

    try:
        CONF(project='octavia')
    except TypeError:
        LOG.error('Error parsing the configuration values. Please verify.')
        raise
    return conf


def main():
    setup_conf()

    # Method can be call like
    # `octavia-ovn-db-sync-util lb_filter_key1=lb_filter_value1`
    # which loadbalancer filter keys limits to Loadbalancer API allowence in
    # https://docs.openstack.org/api-ref/load-balancer/v2/#list-load-balancers
    args = sys.argv[1:]
    lb_filters = {}
    if '--debug' in args:
        cfg.CONF.set_override('debug', True)
        args.remove('--debug')
    else:
        cfg.CONF.set_override('debug', False)
    logging.setup(CONF, 'octavia_ovn_db_sync_util')
    for arg in args:
        if '=' not in arg:
            LOG.warn(
                f"Unsupported argument '{arg}', add load balancer list "
                "filter with <project_id>=<project1> <key2>=<value2>... "
                f"etc. Ignore argument {arg}")
        ar = arg.split('=', maxsplit=1)
        if len(ar) == 2:
            key, value = ar
            lb_filters[key] = value

    ovn_driver = driver.OvnProviderDriver()
    ovn_driver.sync(**lb_filters)
    sys.exit(0)
