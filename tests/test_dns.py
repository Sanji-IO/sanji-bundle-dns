import os
import sys
import unittest
import logging

from sanji.connection.mockup import Mockup
from sanji.message import Message
from mock import patch
from mock import mock_open
from mock import Mock


try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../')
    from dns import Dns
except ImportError as e:
    print os.path.dirname(os.path.realpath(__file__)) + '/../'
    print sys.path
    print e
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)

dirpath = os.path.dirname(os.path.realpath(__file__))


class MockLoggingHandler(logging.Handler):
    """Mock logging handler to check for expected logs.

    Messages are available from an instance's ``messages`` dict, in order,
    indexed by a lowercase log level string (e.g., 'debug', 'info', etc.).

    Ref:
        http://stackoverflow.com/questions/899067/how-should-i-verify-a-log-message-when-testing-python-code-under-nose
    """

    def __init__(self, *args, **kwargs):
        self.messages = {"debug": [], "info": [], "warning": [], "error": [],
                         "critical": []}
        super(MockLoggingHandler, self).__init__(*args, **kwargs)

    def emit(self, record):
        "Store a message from ``record`` in the instance's ``messages`` dict."
        self.acquire()
        try:
            self.messages[record.levelname.lower()].append(record.getMessage())
        finally:
            self.release()

    def reset(self):
        self.acquire()
        try:
            for message_list in self.messages.values():
                del message_list[:]
        finally:
            self.release()


class TestDnsClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestDnsClass, cls).setUpClass()
        # Assuming you follow Python's logging module's documentation's
        # recommendation about naming your module's logs after the module's
        # __name__,the following getLogger call should fetch the same logger
        # you use in the foo module
        dns_log = logging.getLogger("sanji.dns")
        cls._dns_log_handler = MockLoggingHandler(level="DEBUG")
        dns_log.addHandler(cls._dns_log_handler)
        cls.dns_log_messages = cls._dns_log_handler.messages

    def setUp(self):
        super(TestDnsClass, self).setUp()
        self._dns_log_handler.reset()  # So each test is independent

        self.name = "dns"
        self.bundle = Dns(connection=Mockup())

    def tearDown(self):
        self.bundle.dns_db[:] = []
        self.bundle.stop()
        self.bundle = None
        try:
            os.remove("%s/data/%s.json" % (dirpath, self.name))
        except OSError:
            pass

        try:
            os.remove("%s/data/%s.json.backup" % (dirpath, self.name))
        except OSError:
            pass

    @patch.object(Dns, "update_config")
    def test__run(self, mock_update_config):
        """
        run
        """
        self.bundle.run()
        mock_update_config.assert_called_once_with()

    @patch.object(Dns, "update_config")
    def test__run__update_resolv_conf_failed(self, mock_update_config):
        """
        run: failed to update resolv.conf
        """
        mock_update_config.side_effect = IOError
        self.bundle.run()
        self.assertEqual(len(self.dns_log_messages["warning"]), 1)
        self.assertIn("Failed to update", self.dns_log_messages["warning"][0])

    def test__get_dns_list(self):
        """
        get_dns_list
        """
        # arrange
        dns = {"interface": "eth0",
               "dns": ["8.8.8.8", "8.8.4.4"]}
        self.bundle.dns_db.append(dns)

        dns = {"interface": "eth1",
               "dns": ["1.1.1.1", "2.2.2.2"]}
        self.bundle.dns_db.append(dns)

        # act
        dns = self.bundle.get_dns_list("eth0")

        # assert
        self.assertEqual(self.bundle.dns_db[0], dns)

    def test__get_dns_list__cannot_find_interface(self):
        """
        get_dns_list: cannot find interface from database
        """
        # arrange
        dns = {"interface": "eth0",
               "dns": ["8.8.8.8", "8.8.4.4"]}
        self.bundle.dns_db.append(dns)

        # act
        dns = self.bundle.get_dns_list("eth1")

        # assert
        self.assertEqual(None, dns)

    def test__add_dns_list(self):
        """
        add_dns_list
        """
        dns = {"interface": "eth1",
               "dns": ["8.8.8.8", "8.8.4.4"]}
        self.bundle.add_dns_list(dns)
        self.assertEqual(self.bundle.dns_db[0], dns)

    @patch.object(Dns, "update_config")
    def test__add_dns_list__update(self, mock_update_config):
        """
        add_dns_list: update DNS list by interface
        """
        # arrange
        dns = {"interface": "eth0",
               "dns": ["8.8.8.8", "8.8.4.4"]}
        self.bundle.dns_db.append(dns)

        dns = {"interface": "eth0",
               "dns": ["1.1.1.1", "2.2.2.2"]}

        # act
        self.bundle.add_dns_list(dns)

        # assert
        self.assertEqual(len(self.bundle.dns_db), 1)
        self.assertEqual(self.bundle.dns_db[0], dns)

    def test__remove_dns_list(self):
        """
        remove_dns_list
        """
        # arrange
        dns = {"interface": "eth0",
               "dns": ["8.8.8.8", "8.8.4.4"]}
        self.bundle.dns_db.append(dns)

        dns = {"interface": "eth1",
               "dns": ["1.1.1.1", "2.2.2.2"]}
        self.bundle.dns_db.append(dns)

        # act
        self.bundle.remove_dns_list("eth0")

        # assert
        self.assertEqual(len(self.bundle.dns_db), 1)
        self.assertEqual(self.bundle.dns_db[0], dns)

    def test__remove_dns_list__empty_db(self):
        """
        remove_dns_list: remove from an empty database
        """
        # act
        self.bundle.remove_dns_list("eth0")

        # assert
        self.assertEqual(len(self.bundle.dns_db), 0)

    def test__remove_dns_list__none_to_remove(self):
        """
        remove_dns_list: no such interface to be removed
        """
        # arrange
        dns = {"interface": "eth0",
               "dns": ["8.8.8.8", "8.8.4.4"]}
        self.bundle.dns_db.append(dns)

        dns = {"interface": "eth1",
               "dns": ["1.1.1.1", "2.2.2.2"]}
        self.bundle.dns_db.append(dns)

        # act
        self.bundle.remove_dns_list("eth2")

        # assert
        self.assertEqual(len(self.bundle.dns_db), 2)

    def test__generate_config__by_interface(self):
        """
        _generate_config: generate resolv.conf content by interface
        """
        # arrange
        self.bundle.model.db = {"interface": "eth1"}

        dns = {"interface": "eth0",
               "dns": ["8.8.8.8", "8.8.4.4"]}
        self.bundle.dns_db.append(dns)

        dns = {"interface": "eth1",
               "dns": ["1.1.1.1", "2.2.2.2"]}
        self.bundle.dns_db.append(dns)

        # act
        rc = self.bundle._generate_config()

        # assert
        self.assertEqual(rc, "nameserver 1.1.1.1\n" + "nameserver 2.2.2.2\n")

    def test__generate_config__by_dns(self):
        """
        _generate_config: generate resolv.conf content by dns list
        """
        # arrange
        self.bundle.model.db = {"dns": ["8.8.8.8", "3.3.3.3"]}

        dns = {"interface": "eth0",
               "dns": ["8.8.8.8", "8.8.4.4"]}
        self.bundle.dns_db.append(dns)

        # act
        rc = self.bundle._generate_config()

        # assert
        self.assertEqual(rc, "nameserver 8.8.8.8\n" + "nameserver 3.3.3.3\n")

    def test__generate_config__without_dns(self):
        """
        _generate_config: without dns list
        """
        # arrange
        self.bundle.model.db = {"interface": "eth0"}

        # act
        rc = self.bundle._generate_config()

        # assert
        self.assertEqual(rc, "")

    def test__write_config(self):
        """
        _write_config
        """
        # arrange
        resolv = "nameserver 1.1.1.1\n" + "nameserver 2.2.2.2\n"

        # patch open
        m = mock_open()
        with patch("dns.open", m, create=True) as f:
            # act
            self.bundle._write_config(resolv)

            # assert
            f.return_value.write.assert_called_once_with(resolv)

    @patch.object(Dns, "_write_config")
    @patch.object(Dns, "_generate_config")
    def test__update_config(self, mock_generate_config, mock_write_config):
        """
        update_config: it should_be_called_once
        """

        # arrange
        mock_generate_config.return_value = \
            "nameserver 1.1.1.1\nnameserver 2.2.2.2\n"
        # act
        self.bundle.update_config()

        # assert
        mock_write_config.assert_called_once_with(
            "nameserver 1.1.1.1\nnameserver 2.2.2.2\n")

    def test__get_current_dns(self):
        """
        get_current_dns
        """
        # arrange
        self.bundle.model.db = {
            "interface": "eth0",
            "dns": ["1.1.1.1", "2.2.2.2"]
        }
        mock_func = Mock(code=200, data=None)

        # act
        self.bundle.get_current_dns(message=None, response=mock_func)

        # assert
        self.assertEqual(len(mock_func.call_args_list), 1)
        self.assertEqual(
            mock_func.call_args_list[0][1]["data"],
            {"interface": "eth0", "dns": ["1.1.1.1", "2.2.2.2"]})

    @patch.object(Dns, "update_config")
    def test__set_current_dns__by_interface(self, mock_update_config):
        """
        set_current_dns: set by interface
        """
        # arrange
        dns = {"interface": "eth0",
               "dns": ["8.8.8.8", "8.8.4.4"]}
        self.bundle.dns_db.append(dns)

        dns = {"interface": "eth1",
               "dns": ["1.1.1.1", "2.2.2.2"]}
        self.bundle.dns_db.append(dns)

        message = Message({"data": {"interface": "eth0"}})
        mock_func = Mock(code=200, data=None)

        # act
        self.bundle.set_current_dns(message=message, response=mock_func)

        # assert
        self.assertEqual(
            mock_func.call_args_list[0][1]["data"], {"interface": "eth0"})

    @patch.object(Dns, "update_config")
    def test__set_current_dns__by_dns_list(self, mock_update_config):
        """
        set_current_dns: set by DNS list
        """
        # arrange
        dns = {"dns": ["1.1.1.1", "2.2.2.2", "3.3.3.3"]}
        message = Message({"data": dns})
        mock_func = Mock(code=200, data=None)

        # act
        self.bundle.set_current_dns(message=message, response=mock_func)

        # assert
        self.assertEqual(mock_func.call_args_list[0][1]["data"], dns)

    @patch.object(Dns, "update_config")
    def test__set_current_dns__update_config_failed(self, mock_update_config):
        """
        set_current_dns: update config failed
        """
        # arrange
        mock_update_config.side_effect = IOError("Write error!")
        dns = {"dns": ["1.1.1.1", "2.2.2.2", "3.3.3.3"]}
        message = Message({"data": dns})
        mock_func = Mock(code=200, data=None)

        # act
        self.bundle.set_current_dns(message=message, response=mock_func)

        # assert
        self.assertEqual(mock_func.call_args_list[0][1]["code"], 400)

    def test__set_dns_database__add(self):
        """
        set_dns_database: add to database
        """
        # arrange
        dns = {"interface": "eth1", "dns": ["1.1.1.1", "2.2.2.2", "3.3.3.3"]}
        message = Message({"data": dns})
        mock_func = Mock(code=200, data=None)

        # act
        self.bundle.set_dns_database(message=message, response=mock_func)

        # assert
        self.assertEqual(len(mock_func.call_args_list[0][1]["data"]), 1)
        self.assertEqual(mock_func.call_args_list[0][1]["data"][0], dns)

    @patch.object(Dns, "update_config")
    def test__set_dns_database__update(self, mock_update_config):
        """
        set_dns_database: batch update
        """
        # arrange
        dns1 = {"interface": "eth0", "dns": ["1.1.1.1", "2.2.2.2", "3.3.3.3"]}
        dns2 = {"interface": "eth1", "dns": ["2.2.2.2", "3.3.3.3"]}
        self.bundle.dns_db.append(dns1)
        self.bundle.dns_db.append(dns2)

        dns = [
            {"interface": "eth0", "dns": ["8.8.8.8", "8.8.4.4"]},
            {"interface": "eth1", "dns": ["1.1.1.1", "2.2.2.2"]}
        ]
        message = Message({"data": dns})
        mock_func = Mock(code=200, data=None)

        # act
        self.bundle.set_dns_database(message=message, response=mock_func)

        # assert
        self.assertEqual(len(mock_func.call_args_list[0][1]["data"]), 2)
        self.assertEqual(mock_func.call_args_list[0][1]["data"], dns)


if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger('DNS Test')
    unittest.main()
