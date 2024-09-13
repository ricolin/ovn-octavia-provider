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
from unittest import mock

from oslotest import base
from octavia_lib.api.drivers import exceptions as driver_exceptions
from ovn_octavia_provider.common import config

from ovn_octavia_provider.common import clients


class TestKeystoneSession(base.BaseTestCase):
    @mock.patch(
        'keystoneauth1.loading.register_auth_conf_options')
    @mock.patch(
        'keystoneauth1.loading.register_session_conf_options')
    def test_init(self, kl_rs, kl_ra):
        clients.KeystoneSession()
        kl_ra.assert_called_once_with(mock.ANY, 'service_auth')
        kl_rs.assert_called_once_with(mock.ANY, 'service_auth')

    @mock.patch(
        'keystoneauth1.loading.load_session_from_conf_options')
    def test_cached_session(self, kl):
        ksession = clients.KeystoneSession()
        self.assertIs(
            ksession.session,
            ksession.session)
        kl.assert_called_once_with(
            mock.ANY, 'service_auth', auth=ksession.auth)

    @mock.patch(
        'keystoneauth1.loading.load_auth_from_conf_options')
    def test_cached_auth(self, kl):
        ksession = clients.KeystoneSession()
        self.assertIs(
            ksession.auth,
            ksession.auth)
        kl.assert_called_once_with(mock.ANY, 'service_auth')


class TestNeutronAuth(base.BaseTestCase):
    def setUp(self):
        super().setUp()
        self.mock_client = mock.patch(
            'neutronclient.neutron.client.Client').start()
        self.client_args = {
            'endpoint': 'foo_endpoint',
            'region': 'foo_region',
            'endpoint_type': 'foo_endpoint_type',
            'service_name': 'foo_service_name',
            'insecure': 'foo_insecure',
            'ca_cert': 'foo_ca_cert'}
        clients.Singleton._instances = {}

    @mock.patch.object(clients, 'KeystoneSession')
    def test_init(self, mock_ks):
        clients.NeutronAuth(**self.client_args)
        self.mock_client.assert_called_once_with(
            '2.0',
            endpoint_override=self.client_args['endpoint'],
            region_name=self.client_args['region'],
            endpoint_type=self.client_args['endpoint_type'],
            service_name=self.client_args['service_name'],
            insecure=self.client_args['insecure'],
            ca_cert=self.client_args['ca_cert'],
            session=mock_ks().session)

    def test_singleton(self):
        c1 = clients.NeutronAuth(**self.client_args)
        c2 = clients.NeutronAuth(**self.client_args)
        self.assertIs(c1, c2)

    def test_singleton_exception(self):
        with mock.patch(
            'neutronclient.neutron.client.Client',
                side_effect=[RuntimeError, 'foo', 'foo']) as n_cli:
            self.assertRaises(
                RuntimeError,
                clients.NeutronAuth,
                **self.client_args)
            c2 = clients.NeutronAuth(**self.client_args)
            c3 = clients.NeutronAuth(**self.client_args)
            self.assertIs(c2, c3)
            self.assertEqual(n_cli._mock_call_count, 2)


class TestOctaviaAuth(base.BaseTestCase):
    def setUp(self):
        super().setUp()
        config.register_opts()
        self.mock_client = mock.patch(
            'openstack.connection.Connection').start()
        clients.Singleton._instances = {}

    @mock.patch.object(clients, 'KeystoneSession')
    def test_init(self, mock_ks):
        clients.OctaviaAuth()
        self.mock_client.assert_called_once_with(
            session=mock_ks().session)

    def test_singleton(self):
        c1 = clients.OctaviaAuth()
        c2 = clients.OctaviaAuth()
        self.assertIs(c1, c2)

    def test_singleton_exception(self):
        mock_client = mock.Mock()
        mock_client.lbaas_proxy = 'foo'
        with mock.patch(
            'openstack.connection.Connection',
                side_effect=[RuntimeError,
                             mock_client, mock_client]) as os_sdk:
            self.assertRaises(
                RuntimeError,
                clients.OctaviaAuth)
            c2 = clients.OctaviaAuth()
            c3 = clients.OctaviaAuth()
            self.assertIs(c2, c3)
            self.assertEqual(os_sdk._mock_call_count, 2)

    @mock.patch.object(clients, 'KeystoneSession')
    def test_get_client(self, mock_ks):
        clients.get_octavia_client()
        self.mock_client.assert_called_once_with(
            session=mock_ks().session)

    @mock.patch.object(clients, 'OctaviaAuth', side_effect=[RuntimeError])
    def test_get_client_error(self, mock_ks):
        msg = self.assertRaises(
            driver_exceptions.DriverError,
            clients.get_octavia_client)
        self.assertEqual("An unknown driver error occurred.", str(msg))

