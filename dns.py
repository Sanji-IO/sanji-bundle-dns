#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import os
from sanji.core import Sanji
from sanji.core import Route
from sanji.model_initiator import ModelInitiator
from sanji.connection.mqtt import Mqtt

logger = logging.getLogger()


class Dns(Sanji):
    CONFIG_PATH = "/etc/resolv.conf"

    def init(self, *args, **kwargs):
        path_root = os.path.abspath(os.path.dirname(__file__))
        self.model = ModelInitiator("dns", path_root, backup_interval=1)

    def run(self):
        self.update_config()

    @Route(methods="get", resource="/network/dns")
    def get(self, message, response):
        return self.do_get(message, response)

    def do_get(self, message, response):
        return response(data=self.model.db)

    @Route(methods="put", resource="/network/routes/default")
    def hook_route(self, message, response):
        return self.do_hook_route(message, response)

    def do_hook_route(self, message, response):
        '''
        if interface in interface list, then update corresponding
        dns data to /etc/resolv.conf
        '''

        try:
            self.model.db["route_interface"] = message.data["interface"]
            self.model.save_db()
        except (ValueError, KeyError):
            logger.warning("Invalid input")
            return response(code=400, data={"message": "Invalid input"})

        try:
            self.update_config()
            logger.info("update dns config success")
            return response(data=self.model.db)
        except Exception as e:
            logger.debug("updata dns config failed:" + str(e))
            return response(code=400, data={"message":
                                            "update config error"})

    @Route(resource="/network/cellulars")
    def listen_cellular_event(self, message):
        '''
        listen cellular dns and then update dns list to db
        '''

        if not(hasattr(message, "data")):
            raise ValueError("listen cellular event didn't has data")

        logger.debug("listen cellular event: %s" % message.data)
        iface_name = message.data["name"]

        try:
            self.model.db["dns_list"][iface_name] = message.data["dns"]
            self.model.save_db()
        except Exception as e:
            raise ValueError("update cellular event data error: %s" % str(e))

    @Route(methods="put", resource="/network/interfaces")
    def listen_ethernet_event(self, message):
        '''
        listen ethernet dns and then updata dns list to db
        '''

        if not(hasattr(message, "data")):
            raise ValueError("listen ethernet event didn't has data")

        logger.debug("listen ethernet event %s" % message.data)
        iface_name = message.data["name"]

        try:
            self.model.db["dns_list"][iface_name] = message.data["dns"]
            self.model.save_db()
        except Exception as e:
            raise ValueError("updata ethernet event data error: %s" % str(e))

    def update_config(self):
        conf_str = self.generate_config()

        # write config string to CONFIG_PATH
        self.write_config(conf_str)

    def generate_config(self):
        conf_str = ""
        route_interface = self.model.db["route_interface"]
        for server in self.model.db["dns_list"][route_interface]:
            conf_str = conf_str + ("nameserver %s\n" % server)
        return conf_str

    def write_config(self, conf_str):
        with open(Dns.CONFIG_PATH, "w") as f:
            f.write(conf_str)


def main():
    dns = Dns(connection=Mqtt())
    dns.start()

if __name__ == '__main__':
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("dns")
    main()
