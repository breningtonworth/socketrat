# -*- coding: utf-8 -*-

import base64
from contextlib import contextmanager
import pickle
import threading

from . import connection


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

    def handle_socket(self, sock):
        conn = connection.Connection(sock)
        self.handle_connection(conn)

