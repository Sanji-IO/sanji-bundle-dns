#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import os
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
        Optional("interface"): All(str, Length(1, 255)),
        Optional("dns"): [Any("", All(str, Length(0, 15)))]
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
        """
        resolv = ""
        dns_list = []
        if "dns" in self.model.db:
            dns_list = self.model.db["dns"]
        elif "interface" in self.model.db:
            dns = self.get_dns_list(self.model.db["interface"])
            if dns and "dns" in dns:
                dns_list = dns["dns"]

        for server in dns_list:
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

    def get_current_dns(self, message, response):
        return response(data=self.model.db)

    @Route(methods="get", resource="/network/dns")
    def _get_current_dns(self, message, response):
        return self.get_current_dns(message, response)

    def set_current_dns(self, message, response):
        """
        Update current DNS configuration by message.
        """
        # add to DNS database if data include both interface and dns list
        if "interface" in message.data and "dns" in message.data:
            self.add_dns_list(message.data, False)

        # update settings
        self.model.db.clear()
        if "interface" in message.data:
            self.model.db = {"interface": message.data["interface"]}
        elif "dns" in message.data:
            self.model.db = message.data
        self.save()

        try:
            self.update_config()
        except Exception as e:
            return response(code=400, data={"message": e.message})
        return response(data=self.model.db)

    @Route(methods="put", resource="/network/dns")
    def _put_current_dns(self, message, response, schema=PUT_DNS_SCHEMA):
        return self.set_current_dns(message, response)

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
