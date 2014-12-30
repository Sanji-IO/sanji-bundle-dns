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

    @Route(methods="put", resource="/network/dns")
    def put(self, message, response):
        return self.do_put(message, response)

    def do_put(self, message, response):
        if not(hasattr(message, "data")):
            logger.debug("Invalid Input")
            return response(code=400, data={"message": "Invalid Input"})

        if not(isinstance(message.data["dns"], list)):
            logger.debug("Invalid Data")
            return response(code=400, data={"message": "Invalid Data"})
        self.model.db["dns"] = message.data["dns"]
        self.model.save_db()

        try:
            self.update_config()
            logger.info("update dns config success")
        except Exception as e:
            logger.debug("updata dns config failed:" + str(e))
            return response(code=400, data={"message":
                                            "update config error"})
        return response(data=self.model.db)

    def update_config(self):

        # generate config string
        conf_str = self.generate_config()

        # write config string to CONFIG_PATH
        self.write_config(conf_str)

    def generate_config(self):
        conf_str = ""
        for server in self.model.db["dns"]:
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
