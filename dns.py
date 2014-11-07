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

    @Route(methods="get", resource="/network/dns")
    def get(self, message, response):
        return response(data={"enable": self.model.db["enable"]})

    @Route(methods="put", resource="/network/dns")
    def put(self, message, response):
        if hasattr(message, "data") and "enable" in message.data:
            # TODO: assign message data to self.model.db
            # save db
            # self.model.save_db()
            # generate config
            # self.update_config()
            return response(code=self.rsp["code"], data=self.rsp["data"])
        return response(code=400, data={"message": "Invaild Input"})

    def update_config(self):
        # update config to /etc/resolv.conf
        pass

if __name__ == '__main__':
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("dns")

    dns = Dns(connection=Mqtt())
    dns.start()
