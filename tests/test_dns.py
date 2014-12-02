import os
import sys
import unittest
import logging

from sanji.connection.mockup import Mockup
from sanji.message import Message
from mock import patch
from mock import mock_open

logger = logging.getLogger()

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../')
    from dns import Dns
except ImportError as e:
    print e
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)


class TestDnsClass(unittest.TestCase):

    def setUp(self):
        self.dns = Dns(connection=Mockup())

    def tearDown(self):
        self.dns.stop()
        self.dns = None

    def test_get(self):
        # case 1: check code
        def resp(code=200, data=None):
            self.assertEqual(code, 200)
        self.dns.get(message=None, response=resp, test=True)

    @patch("dns.Dns.update_config")
    def test_put1(self, update_config):
        # case 1: message donsn't has data attribute
        message = Message({})

        def resp(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invaild Input"})
        self.dns.put(message=message, response=resp, test=True)

    @patch("dns.Dns.update_config")
    def test_put2(self, update_config):
        # case 2: update_rc=False
        message = Message({"data": {"dns": ["1.1.1.1", "2.2.2.2"]}})
        update_config.return_value = False

        def resp1(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "update config error"})
        self.dns.put(message=message, response=resp1, test=True)

    @patch("dns.Dns.update_config")
    def test_put3(self, update_config):
        # case 3: update_rc=True
        message = Message({"data": {"dns": ["1.1.1.1", "2.2.2.2"]}})
        update_config.return_value = True

        def resp2(code=200, data=None):
            self.assertEqual(code, 200)
            self.assertEqual(data, {"dns": ["1.1.1.1", "2.2.2.2"]})
        self.dns.put(message=message, response=resp2, test=True)

    @patch("dns.Dns.update_config")
    def test_put4(self, update_config):
        # case 4: Invalid data
        message = Message({"data": {"dns": "invalid data"}})

        def resp(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invalid Data"})
        self.dns.put(message=message, response=resp, test=True)

    @patch("dns.Dns.write_config")
    @patch("dns.Dns.generate_config")
    def test_update_config1(self, generate_config, write_config):
        # write_config success
        generate_config.return_value = "nameserver 1.1.1.1\n" + \
                                       "nameserver 2.2.2.2\n"
        rc = self.dns.update_config()
        self.assertEqual(rc, True)

    @patch("dns.Dns.write_config")
    @patch("dns.Dns.generate_config")
    def test_update_config2(self, generate_config, write_config):
        # write_config failed
        generate_config.return_value = "nameserver 1.1.1.1\n" + \
                                       "nameserver 2.2.2.2\n"
        write_config.side_effect = Exception("error exception!")
        rc = self.dns.update_config()
        self.assertEqual(rc, False)

    def test_generate_config(self):
        self.dns.model.db = {"dns": ["1.1.1.1", "2.2.2.2"]}
        rc = self.dns.generate_config()
        self.assertEqual(rc, "nameserver 1.1.1.1\n" + "nameserver 2.2.2.2\n")

    def test_write_config1(self):
        # case 1: open success
        conf_str = "nameserver 1.1.1.1\n" + "nameserver 2.2.2.2\n"
        # patch open
        m = mock_open()
        with patch("dns.open", m, create=True) as f:
            self.dns.write_config(conf_str)
            f.return_value.write.assert_called_once_with(conf_str)

if __name__ == "__main__":
    unittest.main()
