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
        self.assertEqual(mock_fun.call_args_list[0][1]["data"],
                         {"dns": ["1.1.1.1", "2.2.2.2"]})

    def test_do_hook_route_with_data_error_should_return_code_400(self):

        # arrange
        message = Message({"data": {}})
        mock_fun = Mock(code=200, data=None)

        # act
        Dns.do_hook_route(self.dns, message=message, response=mock_fun)

        # assert
        self.assertEqual(mock_fun.call_args_list[0][1]["code"], 400)

    @patch("dns.Dns.update_config")
    def test_do_hook_route_with_update_config_failed(self, update_config):
        """
        test_do_hook_route_with_update_config_failed_should return code 400
        """

        # arrange
        message = Message({"data": {
            "interface": "eth1"
            }
        })

        mock_fun = Mock(code=200, data=None)
        update_config.side_effect = Exception("update failed")

        # act
        Dns.do_hook_route(self.dns, message=message, response=mock_fun)

        # assert
        self.assertEqual(mock_fun.call_args_list[0][1]["code"], 400)

    @patch("dns.Dns.update_config")
    def test_do_hook_route_should_return_code_200(self, update_config):

        # arrange
        message = Message({"data": {
            "interface": "eth1",
            }
        })
        self.dns.model.db = {"route_interface": "eth0",
                             "dns_list":
                             {"eth0": [],
                              "eth1": ["1.1.1.1", "2.2.2.2", "3.3.3.3"],
                              "wwlan0": []
                              },
                             "dns": []
                             }

        mock_fun = Mock(code=200, data=None)
        update_config.return_value = True
        check_data = {"route_interface": "eth1",
                      "dns_list":
                      {"eth0": [],
                       "eth1": ["1.1.1.1", "2.2.2.2", "3.3.3.3"],
                       "wwlan0": []},
                      "dns": ["1.1.1.1", "2.2.2.2", "3.3.3.3"]}

        # act
        Dns.do_hook_route(self.dns, message=message, response=mock_fun)

        # assert
        self.assertEqual(mock_fun.call_args_list[0][1]["data"], check_data)

    def test_listen_cellular_event_with_data_failed(self):
        '''
        test_listen_cellular_event_with_data_failed
        should raise ValueError exception
        '''

        # arrange
        message = Message({})
        except_flag = 0
        self.dns.model.db = {"route_interface": "eth0",
                             "dns_list":
                             {"eth0": [],
                              "eth1": [],
                              "wwlan0": []
                              },
                             "dns": []
                             }

        # act
        try:
            Dns.listen_cellular_event(self.dns, message=message, test=True)
        except ValueError:
            except_flag = 1

        # assert
        self.assertEqual(except_flag, 1)

    def test_listen_cellular_event(self):

        # arrange
        message = Message({"data": {
            "name": "wwlan0",
            "dns": ["168.95.1.1", "168.95.1.2"]
            }
        })

        self.dns.model.db = {"route_interface": "wwlan0",
                             "dns_list":
                             {"eth0": [],
                              "eth1": [],
                              "wwlan0": []
                              },
                             "dns": ["168.95.1.1", "168.95.1.2"]
                             }

        check_data = {"route_interface": "wwlan0",
                      "dns_list":
                      {"eth0": [],
                       "eth1": [],
                       "wwlan0": ["168.95.1.1", "168.95.1.2"]},
                      "dns": ["168.95.1.1", "168.95.1.2"]}

        # act
        Dns.listen_cellular_event(self.dns, message=message, test=True)

        # assert
        self.assertEqual(self.dns.model.db, check_data)

    def test_listen_cellular_event_with_update_cellular_event_failed(self):

        # arrange
        message = Message({"data": {
            "name": "wwlan0",
            }
        })

        self.dns.model.db = {"route_interface": "wwlan0",
                             "dns_list":
                             {"eth0": [],
                              "eth1": [],
                              "wwlan0": []
                              },
                             "dns": ["168.95.1.1", "168.95.1.2"]
                             }

        except_flag = 0

        # act
        try:
            Dns.listen_cellular_event(self.dns, message=message, test=True)
        except Exception:
            except_flag = 1

        # assert
        self.assertEqual(except_flag, 1)

    def test_listen_ethernet_event_with_data_failed(self):
        """
        test_listen_cellular_event_with_data_failed
        should raise ValueError exception
        """

        # arrange
        message = Message({})
        except_flag = 0

        self.dns.model.db = {"route_interface": "eth0",
                             "dns_list":
                             {"eth0": [],
                              "eth1": [],
                              "wwlan0": []
                              },
                             "dns": []
                             }

        # act
        try:
            Dns.listen_ethernet_event(self.dns, message=message, test=True)
        except ValueError:
            except_flag = 1

        # assert
        self.assertEqual(except_flag, 1)

    def test_listen_ethernet_event(self):

        # arrange
        message = Message({"data": {
            "name": "eth1",
            "dns": ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
            }
        })

        self.dns.model.db = {"route_interface": "eth1",
                             "dns_list":
                             {"eth0": [],
                              "eth1": [],
                              "wwlan0": []
                              },
                             "dns": ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
                             }

        check_data = {"route_interface": "eth1",
                      "dns_list":
                      {"eth0": [],
                       "eth1": ["1.1.1.1", "2.2.2.2", "3.3.3.3"],
                       "wwlan0": []},
                      "dns": ["1.1.1.1", "2.2.2.2", "3.3.3.3"]}

        # act
        Dns.listen_ethernet_event(self.dns, message=message, test=True)

        # assert
        self.assertEqual(self.dns.model.db, check_data)

    def test_listen_ethernet_event_with_update_ethernet_event_failed(self):

        # arrange
        message = Message({"data": {
            "name": "eth1",
            }
        })

        self.dns.model.db = {"route_interface": "eth1",
                             "dns_list":
                             {"eth0": [],
                              "eth1": [],
                              "wwlan0": []
                              },
                             "dns": ["1.1.1.1", "2.2.2.2", "3.3.3.3"]
                             }
        except_flag = 0
        # act
        try:
            Dns.listen_ethernet_event(self.dns, message=message, test=True)
        except:
            except_flag = 1

        # assert
        self.assertEqual(except_flag, 1)

    @patch("dns.Dns.write_config")
    @patch("dns.Dns.generate_config")
    def test_update_config(self, generate_config, write_config):
        """
        test_update_config, it should_be_called_once
        """

        # arrange
        generate_config.return_value = "nameserver 1.1.1.1\n" + \
                                       "nameserver 2.2.2.2\n"
        # act
        self.dns.update_config()

        # assert
        write_config.assert_called_once_with("nameserver 1.1.1.1\n" +
                                             "nameserver 2.2.2.2\n")

    def test_generate_config_should_return_config_string(self):

        # arrange
        self.dns.model.db = {"route_interface": "eth1",
                             "dns_list":
                             {"eth0": [],
                              "eth1": ["1.1.1.1", "2.2.2.2"],
                              "wwlan0": []},
                             "dns": ["1.1.1.1", "2.2.2.2"]}

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
