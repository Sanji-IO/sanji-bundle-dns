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
        self.update_config()

    @Route(methods="get", resource="/network/dns")
    def get(self, message, response):
        return response(data=self.model.db)

    @Route(methods="put", resource="/network/dns")
    def put(self, message, response):
        if not(hasattr(message, "data")):
            return response(code=400, data={"message": "Invaild Input"})
        # assign message data to self.model.db
        if not(isinstance(message.data["dns"], list)):
            return response(code=400, data={"message": "Invalid Data"})
        self.model.db["dns"] = message.data["dns"]
        self.model.save_db()
        # generate config
        update_rc = self.update_config()
        if update_rc is False:
            return response(code=400, data={"message":
                                            "update config error"})
        return response(data=self.model.db)

    def update_config(self):
        try:
            # generate config string
            conf_str = self.generate_config()
            # write config string to CONFIG_PATH
            self.write_config(conf_str)
            logger.info("dns config is updated")
            return True
        except Exception as e:
            logger.debug("update config file error:%s" % e)
            return False

    def generate_config(self):
        conf_str = ""
        for server in self.model.db["dns"]:
            conf_str = conf_str + ("nameserver %s\n" % server)
        return conf_str

    def write_config(self, conf_str):
        try:
            with open(Dns.CONFIG_PATH, "w") as f:
                f.write(conf_str)
                f.close()
        except Exception as e:
            raise e


def main():
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=0, format=FORMAT)

    dns = Dns(connection=Mqtt())
    dns.start()

if __name__ == '__main__':
    logger = logging.getLogger("dns")
    main()
