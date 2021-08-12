# -*- coding: utf-8 -*-

import struct


class Connection:

    def __init__(self, sock):
        self._sock = sock
        self.host, self.port = sock.getpeername()

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def send(self, msg):
        msg = struct.pack('>I', len(msg)) + msg
        self._sock.sendall(msg)

    def recv(self):
        raw_msglen = self._recvall(4)
        msglen = struct.unpack('>I', raw_msglen)[0]
        return self._recvall(msglen)

    def _recvall(self, n):
        data = b''
        while len(data) < n:
            packet = self._sock.recv(n - len(data))
            if not packet:
                raise ConnectionClosed
            data += packet
        return data

    def close(self):
        self._sock.close()


class ConnectionClosed(Exception):
    pass

