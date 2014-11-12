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

    def init(self, *args, **kwargs):
        path_root = os.path.abspath(os.path.dirname(__file__))
        self.model = ModelInitiator("dns", path_root, backup_interval=1)
        self.dns_config_path = "/etc/resolv.conf"

    @Route(methods="get", resource="/network/dns")
    def get(self, message, response):
        return response(data=self.model.db)

    @Route(methods="put", resource="/network/dns")
    def put(self, message, response):
        if hasattr(message, "data"):
            # assign message data to self.model.db
            self.model.db["dns"] = message.data["dns"]
            self.model.save_db()
            # generate config
            update_rc = self.update_config()
            if update_rc is False:
                return response(code=400, data={"message":
                                                "update config error"})
            return response(data=self.model.db)
        return response(code=400, data={"message": "Invaild Input"})

    def update_config(self):
        try:
            # generate config string
            conf_str = ""
            for server in self.model.db["dns"]:
                conf_str = conf_str + ("nameserver %s\n" % server)
            # save config string to /etc/resolv.conf
            with open(self.dns_config_path, "w") as f:
                f.write(conf_str)
            logger.info("dns config is updated")
            return True
        except Exception as e:
            logger.debug("update config file error:%s" % e)
            return False

if __name__ == '__main__':
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("dns")

    dns = Dns(connection=Mqtt())
    dns.start()
