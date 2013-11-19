import json
import requests

from go.vumitools.tests.utils import GoTestCase
from go.base.tests.utils import FakeResponse, FakeRpcResponse, FakeServer


class TestFakeResponse(GoTestCase):
    def test_json_content(self):
        resp = FakeResponse(data={'foo': 'bar'})
        self.assertEqual(resp.json, {'foo': 'bar'})

    def test_plain_content(self):
        resp = FakeResponse(content='foo')
        self.assertEqual(resp.content, 'foo')

    def test_error_raising(self):
        resp = FakeResponse(code=500)
        self.assertRaises(requests.exceptions.HTTPError, resp.raise_for_status)


class TestFakeRpcResponse(GoTestCase):
    def test_rpc_response_data(self):
        resp = FakeRpcResponse(id='some-id', result={'foo': 'bar'})
        self.assertEqual(resp.json, {
            'jsonrpc': '2.0',
            'id': 'some-id',
            'result': {'foo': 'bar'}
        })

    def test_rpc_error_response_data(self):
        resp = FakeRpcResponse(id='some-id', error=':(')
        self.assertEqual(resp.json, {
            'jsonrpc': '2.0',
            'id': 'some-id',
            'result': None,
            'error': ':('
        })


class TestFakeServer(GoTestCase):
    def setUp(self):
        super(TestFakeServer, self).setUp()
        self.server = FakeServer()

    def tearDown(self):
        super(TestFakeServer, self).tearDown()
        self.server.tear_down()

    def test_request_catching(self):
        requests.request('get', 'http://some.place')
        requests.get('http://some.place')
        requests.post('http://some.place')
        requests.put('http://some.place')
        requests.head('http://some.place')
        requests.patch('http://some.place')
        requests.options('http://some.place')
        requests.delete('http://some.place')

        self.assertEqual(self.server.get_requests(), [
            {'method': 'get', 'url': 'http://some.place'},
            {'method': 'get', 'url': 'http://some.place'},
            {'method': 'post', 'url': 'http://some.place'},
            {'method': 'put', 'url': 'http://some.place'},
            {'method': 'head', 'url': 'http://some.place'},
            {'method': 'patch', 'url': 'http://some.place'},
            {'method': 'options', 'url': 'http://some.place'},
            {'method': 'delete', 'url': 'http://some.place'}])

    def test_request_catching_for_json_data_loading(self):
        requests.put('http://some.place', data=json.dumps({'foo': 'bar'}))
        self.assertEqual(self.server.get_requests(), [{
            'method': 'put',
            'url': 'http://some.place',
            'data': {'foo': 'bar'},
        }])

    def test_request_response_setting(self):
        resp = FakeResponse()
        self.server.set_response(resp)

        self.assertEqual(resp, requests.request('get', 'http://some.place'))
        self.assertEqual(resp, requests.get('http://some.place'))
        self.assertEqual(resp, requests.post('http://some.place'))
        self.assertEqual(resp, requests.put('http://some.place'))
        self.assertEqual(resp, requests.head('http://some.place'))
        self.assertEqual(resp, requests.patch('http://some.place'))
        self.assertEqual(resp, requests.options('http://some.place'))
        self.assertEqual(resp, requests.delete('http://some.place'))
