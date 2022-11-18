# -*- coding: utf-8 -*-

import socketserver

from .payload import PayloadRPCDispatcher


class PayloadRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        self.server.handle_request(self.request)


class TCPBindPayload(socketserver.TCPServer, PayloadRPCDispatcher):

    def __init__(self, addr, requestHandler=PayloadRequestHandler,
            logRequests=True, allow_none=False, encoding=None,
            bind_and_activate=True, use_builtin_types=False):
        self.logRequests = logRequests

        #PayloadRPCDispatcher.__init__(self, allow_none, encoding, use_builtin_types)
        PayloadRPCDispatcher.__init__(self)
        socketserver.TCPServer.__init__(self, addr, requestHandler, bind_and_activate)

