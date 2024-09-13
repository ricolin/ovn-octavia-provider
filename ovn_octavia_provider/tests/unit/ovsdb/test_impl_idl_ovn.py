#
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
#

import os
from unittest import mock

from netaddr import core as net_core
from neutron.tests import base
from ovs.db import idl as ovs_idl
from ovsdbapp.backend import ovs_idl as real_ovs_idl
from ovsdbapp.backend.ovs_idl import idlutils

from ovn_octavia_provider.common import config as ovn_config
from ovn_octavia_provider.ovsdb import impl_idl_ovn

basedir = os.path.dirname(os.path.abspath(__file__))
schema_files = {
    'OVN_Northbound': os.path.join(basedir,
                                   '..', 'schemas', 'ovn-nb.ovsschema'),
    'OVN_Southbound': os.path.join(basedir,
                                   '..', 'schemas', 'ovn-sb.ovsschema')}


class TestOvnNbIdlForLb(base.BaseTestCase):

    def setUp(self):
        super().setUp()
        ovn_config.register_opts()
        # TODO(haleyb) - figure out why every test in this class generates
        # this warning, think it's in relation to reading this schema file:
        # sys:1: ResourceWarning: unclosed file <_io.FileIO name=1 mode='wb'
        # closefd=True> ResourceWarning: Enable tracemalloc to get the object
        # allocation traceback
        self.mock_gsh = mock.patch.object(
            idlutils, 'get_schema_helper',
            side_effect=lambda x, y: ovs_idl.SchemaHelper(
                location=schema_files['OVN_Northbound'])).start()
        self.idl = impl_idl_ovn.OvnNbIdlForLb()

    def test__get_ovsdb_helper(self):
        self.mock_gsh.reset_mock()
        self.idl._get_ovsdb_helper('foo')
        self.mock_gsh.assert_called_once_with('foo', 'OVN_Northbound')

    def test_setlock(self):
        with mock.patch.object(impl_idl_ovn.OvnNbIdlForLb,
                               'set_lock') as set_lock:
            self.idl = impl_idl_ovn.OvnNbIdlForLb(event_lock_name='foo')
        set_lock.assert_called_once_with('foo')


class TestOvnSbIdlForLb(base.BaseTestCase):

    def setUp(self):
        super().setUp()
        ovn_config.register_opts()
        # TODO(haleyb) - figure out why every test in this class generates
        # this warning, think it's in relation to reading this schema file:
        # sys:1: ResourceWarning: unclosed file <_io.FileIO name=1 mode='wb'
        # closefd=True> ResourceWarning: Enable tracemalloc to get the object
        # allocation traceback
        self.mock_gsh = mock.patch.object(
            idlutils, 'get_schema_helper',
            side_effect=lambda x, y: ovs_idl.SchemaHelper(
                location=schema_files['OVN_Southbound'])).start()
        self.idl = impl_idl_ovn.OvnSbIdlForLb()

    @mock.patch.object(real_ovs_idl.Backend, 'autocreate_indices', mock.Mock(),
                       create=True)
    def test_start_reuses_connection(self):
        with mock.patch('ovsdbapp.backend.ovs_idl.connection.Connection',
                        side_effect=lambda x, timeout: mock.Mock()):
            idl1 = impl_idl_ovn.OvnSbIdlForLb()
            ret1 = idl1.start()
            id1 = id(ret1.ovsdb_connection)
            idl2 = impl_idl_ovn.OvnSbIdlForLb()
            ret2 = idl2.start()
            id2 = id(ret2.ovsdb_connection)
            self.assertEqual(id1, id2)

    @mock.patch('ovsdbapp.backend.ovs_idl.connection.Connection')
    def test_stop(self, mock_conn):
        mock_conn.stop.return_value = False
        with (
            mock.patch.object(
                self.idl.notify_handler, 'shutdown')) as mock_notify, (
                mock.patch.object(self.idl, 'close')) as mock_close:
            self.idl.start()
            self.idl.stop()
        mock_notify.assert_called_once_with()
        mock_close.assert_called_once_with()

    @mock.patch('ovsdbapp.backend.ovs_idl.connection.Connection')
    def test_stop_no_connection(self, mock_conn):
        mock_conn.stop.return_value = False
        with (
            mock.patch.object(
                self.idl.notify_handler, 'shutdown')) as mock_notify, (
                mock.patch.object(self.idl, 'close')) as mock_close:
            self.idl.stop()
        mock_notify.assert_called_once_with()
        mock_close.assert_called_once_with()

    def test_setlock(self):
        with mock.patch.object(impl_idl_ovn.OvnSbIdlForLb,
                               'set_lock') as set_lock:
            self.idl = impl_idl_ovn.OvnSbIdlForLb(event_lock_name='foo')
        set_lock.assert_called_once_with('foo')


class TestAddBackendToIPPortMapping(base.BaseTestCase):

    def setUp(self):
        super().setUp()
        ovn_config.register_opts()
        self.mock_gsh = mock.patch.object(
            idlutils, 'get_schema_helper',
            side_effect=lambda x, y: ovs_idl.SchemaHelper(
                location=schema_files['OVN_Northbound'])).start()
        self.backend_ip = '1.2.3.4'
        self.backend_ip_ipv6 = 'e80::4868:1b06:5551:f707'
        self.lb_uuid = 'lb_uuid'
        self.port_name = 'port_name'
        self.src_ip = '1.2.3.5'
        self.src_ip_ipv6 = 'e80::4868:1b06:5552:f707'
        self.idl = impl_idl_ovn.OvnNbIdlForLb()

    def test_mapping_error_ip(self):
        lb = mock.MagicMock()
        lb.ip_port_mappings = {}
        self.assertRaises(
            net_core.AddrFormatError, impl_idl_ovn.AddBackendToIPPortMapping,
            self.idl, self.lb_uuid, backend_ip='wrong_ip_format',
            port_name=self.port_name, src_ip='wrong_ip_format',
            is_sync=False)

    def test_mapping(self):
        lb = mock.MagicMock()
        lb.ip_port_mappings = {}
        pm = impl_idl_ovn.AddBackendToIPPortMapping(
            self.idl, self.lb_uuid, backend_ip=self.backend_ip,
            port_name=self.port_name, src_ip=self.src_ip,
            is_sync=False)
        pm.api = mock.MagicMock()
        pm.api.lookup.return_value = lb
        pm.run_idl(mock.Mock())
        pm.api.lookup.assert_called_once_with('Load_Balancer', self.lb_uuid)
        lb.setkey.assert_called_once_with(
            'ip_port_mappings', self.backend_ip,
            f'{self.port_name}:{self.src_ip}')

    def test_mapping_ipv6(self):
        lb = mock.MagicMock()
        lb.ip_port_mappings = {}
        pm = impl_idl_ovn.AddBackendToIPPortMapping(
            self.idl, self.lb_uuid, backend_ip=self.backend_ip_ipv6,
            port_name=self.port_name, src_ip=self.src_ip_ipv6,
            is_sync=False)
        pm.api = mock.MagicMock()
        pm.api.lookup.return_value = lb
        pm.run_idl(mock.Mock())
        pm.api.lookup.assert_called_once_with('Load_Balancer', self.lb_uuid)
        lb.setkey.assert_called_once_with(
            'ip_port_mappings', f'[{self.backend_ip_ipv6}]',
            f'{self.port_name}:[{self.src_ip_ipv6}]')

    def test_mapping_is_sync_exist(self):
        lb = mock.MagicMock()
        lb.ip_port_mappings = {}
        lb.ip_port_mappings[self.backend_ip] = (
            f"{self.port_name}:{self.src_ip}")
        pm = impl_idl_ovn.AddBackendToIPPortMapping(
            self.idl, self.lb_uuid, backend_ip=self.backend_ip,
            port_name=self.port_name, src_ip=self.src_ip,
            is_sync=True)
        pm.api = mock.MagicMock()
        pm.api.lookup.return_value = lb
        pm.run_idl(mock.Mock())
        pm.api.lookup.assert_called_once_with('Load_Balancer', self.lb_uuid)
        lb.setkey.assert_not_called()

    def test_mapping_exception(self):
        ovn_lb = mock.MagicMock(uuid='foo')
        lb = mock.MagicMock()
        lb.ip_port_mappings = {}
        lb.ip_port_mappings[self.backend_ip] = (
            f"{self.port_name}:{self.src_ip}")
        pm = impl_idl_ovn.AddBackendToIPPortMapping(
            self.idl, ovn_lb, backend_ip=self.backend_ip,
            port_name=self.port_name, src_ip=self.src_ip,
            is_sync=False)
        pm.api = mock.MagicMock()
        pm.api.lookup.side_effect = [OSError]
        with mock.patch.object(impl_idl_ovn, 'LOG') as m_l:
            pm.run_idl(mock.Mock())
            m_l.exception.assert_called_once_with(
                f"Error adding backend {self.backend_ip} "
                f"to ip_port_mappings for LB uuid {ovn_lb.uuid}")
        lb.setkey.assert_not_called()

    def test_mapping_is_sync_not_exist(self):
        lb = mock.MagicMock()
        lb.ip_port_mappings = {}
        pm = impl_idl_ovn.AddBackendToIPPortMapping(
            self.idl, self.lb_uuid, backend_ip=self.backend_ip,
            port_name=self.port_name, src_ip=self.src_ip,
            is_sync=True)
        pm.api = mock.MagicMock()
        pm.api.lookup.return_value = lb
        pm.run_idl(mock.Mock())
        pm.api.lookup.assert_called_once_with('Load_Balancer', self.lb_uuid)
        lb.setkey.assert_called_once_with(
            'ip_port_mappings', self.backend_ip,
            f'{self.port_name}:{self.src_ip}')
