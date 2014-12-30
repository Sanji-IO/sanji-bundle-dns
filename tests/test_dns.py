import os
import sys
import unittest
import logging

from sanji.connection.mockup import Mockup
from sanji.message import Message
from mock import patch
from mock import mock_open
from mock import Mock

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

    def test_do_get_should_return_db(self):

        # arrange
        self.dns.model.db = {"dns": ["1.1.1.1", "2.2.2.2"]}

        mock_fun = Mock(code=200, data=None)

        # act
        Dns.do_get(self.dns, message=None, response=mock_fun)

        # assert
        self.assertEqual(len(mock_fun.call_args_list), 1)
        self.assertEqual(mock_fun.call_args_list[0][1]["data"], {"dns": ["1.1.1.1", "2.2.2.2"]})

    def test_do_put_without_data_should_return_code_400(self):

        # arrange
        message = Message({})
        mock_fun = Mock(code=200, data=None)

        # act
        Dns.do_put(self.dns, message=message, response=mock_fun)

        # assert
        self.assertEqual(len(mock_fun.call_args_list), 1)
        self.assertEqual(mock_fun.call_args_list[0][1]["code"], 400)

    def test_do_put_with_invalid_data_should_return_code_400(self):

        # arrange
        message = Message({"data": {"dns": "invalid data"}})
        mock_fun = Mock(code=200, data=None)

        # act
        Dns.do_put(self.dns, message=message, response=mock_fun)

        # assert
        self.assertEqual(len(mock_fun.call_args_list), 1)
        self.assertEqual(mock_fun.call_args_list[0][1]["code"], 400)

    @patch("dns.Dns.update_config")
    def test_do_put_with_update_config_failed_should_return_code_400(self, update_config):

        # arrange
        message = Message({"data": {"dns": ["1.1.1.1", "2.2.2.2"]}})
        update_config.side_effect = Exception("update config exception")
        mock_fun = Mock(code=200, data=None)

        # act
        Dns.do_put(self.dns, message=message, response=mock_fun)

        # assert
        self.assertEqual(len(mock_fun.call_args_list), 1)
        self.assertEqual(mock_fun.call_args_list[0][1]["code"], 400)

    @patch("dns.Dns.update_config")
    def test_do_put_with_update_config_success_should_return_code_200(self, update_config):

        # arrange
        self.dns.model.db = {"dns": ["1.1.1.1", "2.2.2.2"]}
        message = Message({"data": self.dns.model.db})
        update_config.return_value = None
        mock_fun = Mock(code=400, data=None)

        # act
        Dns.do_put(self.dns, message=message, response=mock_fun)

        # assert
        self.assertEqual(len(mock_fun.call_args_list), 1)
        self.assertEqual(mock_fun.call_args_list[0][1]["data"], {"dns": ["1.1.1.1", "2.2.2.2"]})

    @patch("dns.Dns.write_config")
    @patch("dns.Dns.generate_config")
    def test_update_config_with_write_config_should_be_called_once(self, generate_config, write_config):

        # arrange
        generate_config.return_value = "nameserver 1.1.1.1\n" + \
                                       "nameserver 2.2.2.2\n"
        # act
        self.dns.update_config()

        # assert
        write_config.assert_called_once_with("nameserver 1.1.1.1\n" + \
                                             "nameserver 2.2.2.2\n")

    def test_generate_config_should_return_config_string(self):

        # arrange
        self.dns.model.db = {"dns": ["1.1.1.1", "2.2.2.2"]}

        # act
        rc = self.dns.generate_config()

        # assert
        self.assertEqual(rc, "nameserver 1.1.1.1\n" + "nameserver 2.2.2.2\n")

    def test_write_config_should_write_config_string_to_file(self):

        # arrange
        conf_str = "nameserver 1.1.1.1\n" + "nameserver 2.2.2.2\n"

        # patch open
        m = mock_open()
        with patch("dns.open", m, create=True) as f:
            # act
            self.dns.write_config(conf_str)

            # assert
            f.return_value.write.assert_called_once_with(conf_str)

if __name__ == "__main__":
    unittest.main()
