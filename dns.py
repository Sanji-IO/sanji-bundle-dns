#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import os
import copy
from sanji.core import Sanji
from sanji.core import Route
from sanji.model_initiator import ModelInitiator
from sanji.connection.mqtt import Mqtt

from voluptuous import Schema
from voluptuous import REMOVE_EXTRA
from voluptuous import All
from voluptuous import Any
from voluptuous import Required
from voluptuous import Optional
from voluptuous import Length

_logger = logging.getLogger("sanji.dns")


class Dns(Sanji):
    CONFIG_PATH = "/etc/resolv.conf"

    IFACE_SCHEMA = Schema({
        Required("name"): All(str, Length(1, 255)),
        Required("dns"): [Any("", All(str, Length(0, 15)))]
    }, extra=REMOVE_EXTRA)

    PUT_DB_SCHEMA = Schema({
        Required("interface"): All(str, Length(1, 255)),
        Required("dns"): [Any("", All(str, Length(0, 15)))]
    }, extra=REMOVE_EXTRA)

    PUT_DNS_SCHEMA = Schema({
        Optional("alternative"): bool,
        Optional("interface"): All(str, Length(1, 255)),
        Optional("dns"): [Any("", All(str, Length(0, 15)))],
        Optional("alternativeDNS"): [Any("", All(str, Length(0, 15)))]
    }, extra=REMOVE_EXTRA)

    def init(self, *args, **kwargs):
        try:  # pragma: no cover
            bundle_env = kwargs["bundle_env"]
        except KeyError:
            bundle_env = os.getenv("BUNDLE_ENV", "debug")

        # load configuration
        self.path_root = os.path.abspath(os.path.dirname(__file__))
        if bundle_env == "debug":  # pragma: no cover
            self.path_root = "%s/tests" % self.path_root

        try:
            self.load(self.path_root)
        except:
            self.stop()
            raise IOError("Cannot load any configuration.")

        # initialize DNS database
        self.dns_db = []
        if "alternativeDNS" in self.model.db:
            self.add_dns_list(
                {"interface": "alternative",
                 "dns": self.model.db["alternativeDNS"]})

    def run(self):
        try:
            self.update_config()
        except Exception as e:
            _logger.warning("Failed to update %s: %s" % (Dns.CONFIG_PATH, e))

    def load(self, path):
        """
        Load the configuration. If configuration is not installed yet,
        initialise them with default value.

        Args:
            path: Path for the bundle, the configuration should be located
                under "data" directory.
        """
        self.model = ModelInitiator("dns", path, backup_interval=-1)
        if self.model.db is None:
            raise IOError("Cannot load any configuration.")
        self.save()

    def save(self):
        """
        Save and backup the configuration.
        """
        self.model.save_db()
        self.model.backup_db()

    def get_dns_list(self, interface):
        """
        Get DNS list by interface from database.

        Args:
            interface: interface name for the DNS list belongs to.
        """
        for iface in self.dns_db:
            if interface == iface["interface"]:
                return iface
        return None

    def set_dns_list(self, dns, update=True):
        """
        Update DNS list by interface from database.

        Args:
            interface: interface name for the DNS list belongs to.
        """
        for iface in self.dns_db:
            if dns["interface"] == iface["interface"]:
                iface["dns"] = dns["dns"]
                return iface
        return self.add_dns_list(dns, update)

    def add_dns_list(self, dns, update=True):
        """
        Add DNS list by interface into database and update setting if
        required.

        Args:
            dns: a dictionary with "interface" and "dns" list, for example:
                {
                    "interface": "eth0",
                    "dns": ["8.8.8.8", "8.8.4.4"]
                }
        """
        iface = self.get_dns_list(dns["interface"])
        if iface:
            iface["dns"] = dns["dns"]
        else:
            self.dns_db.append(dns)

        # update config if data updated
        if update and "interface" in self.model.db \
                and dns["interface"] == self.model.db["interface"]:
            self.update_config()

    def remove_dns_list(self, interface):
        """
        Remove DNS list by interface from database.

        Args:
            interface: interface name for the DNS list belongs to.
        """
        self.dns_db[:] = \
            [i for i in self.dns_db if i.get("interface") != interface]

    def _generate_config(self):
        """
        Generate /etc/resolv.conf content.
        Priority:
            1. alternative DNS
            2. temporary DNS
            3. by interface
        """
        resolv = ""
        data = self.get_current_dns()
        if "dns" not in data:
            return resolv

        for server in data["dns"]:
            if server != "":
                resolv = resolv + ("nameserver %s\n" % server)
        return resolv

    def _write_config(self, resolv):
        """
        Write DNS configurations into DNS file (/etc/resolv.conf).

        Args:
            resolv_info: Text content for DNS information.
        """
        with open(Dns.CONFIG_PATH, "w") as f:
            f.write(resolv)

    def update_config(self):
        """
        Update the DNS configuration by settings.
        """
        self._write_config(self._generate_config())

    def get_current_dns(self):
        """
        Get current DNS settings, include alternative information.
            {
              "alternative": false,
              "alternativeDNS": ["8.8.8.8", "8.8.4.4"],
              "interface": "eth0",
              "dns": ["192.168.50.33", "192.168.50.36"]
            }
        """
        data = copy.deepcopy(self.model.db)
        if "alternative" not in data:
            data["alternative"] = False

        if data["alternative"] == True:
            data["interface"] = "alternative"
        if "interface" in data:
            dns = self.get_dns_list(data["interface"])
            if dns and "dns" in dns:
                data["dns"] = copy.copy(dns["dns"])
            elif data["alternative"] == True:
                data["dns"] = data["alternativeDNS"]
        return data

    @Route(methods="get", resource="/network/dns")
    def _get_current_dns(self, message, response):
        data = self.get_current_dns()
        return response(data=data)

    def set_current_dns(self, data):
        """
        Update current DNS configuration by message.
        """
        # add to DNS database if data include both interface and dns list
        if "interface" in data and "dns" in data:
            self.add_dns_list(data, False)

        # update settings
        self.model.db.pop("interface", None)
        self.model.db.pop("dns", None)
        self.model.db.update(data)
        if "alternative" not in self.model.db:
            self.model.db["alternative"] = False

        # update alternative
        dns = {}
        dns["interface"] = "alternative"
        if "alternativeDNS" in self.model.db:
            dns["dns"] = self.model.db["alternativeDNS"]
        else:
            dns["dns"] = []
        self.set_dns_list(dns)

        self.save()
        self.update_config()

    @Route(methods="put", resource="/network/dns")
    def _put_current_dns(self, message, response, schema=PUT_DNS_SCHEMA):
        try:
            self.set_current_dns(message.data)
        except Exception as e:
            return response(code=400, data={"message": e.message})
        return response(data=message.data)

    @Route(methods="get", resource="/network/dns/db")
    def _get_dns_database(self, message, response):
        return response(data=self.dns_db)

    def set_dns_database(self, message, response):
        """
        Update DNS database batch or by interface.
        """
        if type(message.data) is list:
            for dns in message.data:
                self.add_dns_list(dns)
        elif type(message.data) is dict:
            self.add_dns_list(message.data)
        else:
            return response(code=400,
                            data={"message": "Wrong type of DNS database."})
        return response(data=self.dns_db)

    @Route(methods="put", resource="/network/dns/db")
    def _put_dns_database(self, message, response):
        return self.set_dns_database(message, response)

    @Route(methods="put", resource="/network/interface")
    def _event_network_interface(self, message):
        """
        Listen interface event to update the dns database and settings.
        """
        if not(hasattr(message, "data")):
            raise ValueError("Data cannot be None or empty.")
        try:
            self.IFACE_SCHEMA(message.data)
        except Exception as e:
            raise e

        _logger.debug("[/network/interface] interface: %s, dns: %s"
                      % (message.data["name"], message.data["dns"]))

        dns = {"interface": message.data["name"],
               "dns": message.data["dns"]}
        self.add_dns_list(dns)


def main():
    dns = Dns(connection=Mqtt())
    dns.start()

if __name__ == '__main__':
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=0, format=FORMAT)
    _logger = logging.getLogger("sanji.dns")
    main()
