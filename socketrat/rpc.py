# -*- coding: utf-8 -*-

import base64
from contextlib import contextmanager
import pickle
import threading


class RPCProxy:
    
    def __init__(self, connection):
        self._connection = connection
        self._lock = threading.Lock()

    def __getattr__(self, name):
        def do_rpc(*args, **kwargs):
            with self._lock:
                req = pickle.dumps((name, args, kwargs))
                self._connection.send(req)
                response = self._connection.recv()
                response = pickle.loads(response)
                if isinstance(response, Exception):
                    raise response
                return response
        return do_rpc

    #TODO: Move this method into session.py
    #      i.e  create SessionRPCProxy.open_file
    @contextmanager
    def open_file(self, path, mode='r'):
        file_id = self.__getattr__('open_file')(path, mode)
        rfile = RemoteFile(file_id, self)
        try:
            yield rfile
        finally:
            self.close_file(file_id)


# TODO: Move to session.py
class RemoteFile:

    def __init__(self, file_id, rpc):
        self.file_id = file_id
        self.rpc = rpc

    def read(self, size):
        data = self.rpc.read_file(self.file_id, size)
        return base64.urlsafe_b64decode(data)

    def write(self, data):
        data = base64.urlsafe_b64encode(data)
        self.rpc.write_file(self.file_id, data)


class RPCHandler:
    
    def __init__(self):
        self._functions = dict()
        for attr_name in dir(self):
            if attr_name.startswith('rpc_'):
                attr = getattr(self, attr_name)
                self.register_function(attr, attr_name[4:])

    def register_function(self, func, name=None):
        if name is None:
            name = func.__name__
        self._functions[name] = func

    def register_instance(self, obj):
        for attr_name in dir(obj):
            if not attr_name.startswith('_'):
                attr = getattr(obj, attr_name)
                if callable(attr):
                    self._functions[attr_name] = attr

    def handle_connection(self, connection):
        try:
            while True:
                req = connection.recv()
                func_name, args, kwargs = pickle.loads(req)
                try:
                    rep = self._functions[func_name](*args, **kwargs)
                except Exception as e:
                    connection.send(pickle.dumps(e))
                else:
                    connection.send(pickle.dumps(rep))
        except EOFError:
            pass

