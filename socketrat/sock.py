# -*- coding: utf-8 -*-

import socket
import struct
import time


class TCPClient:

    def __init__(self, addr, retry_interval=1):
        self.addr = addr
        self.retry_interval = retry_interval

    def connect_forever(self):
        while True:
            sock = socket.create_connection(self.addr)
            time.sleep(self.retry_interval)


class Connection:
    max_packet_size = 4096

    def __init__(self, sock):
        self._sock = sock
        self._header_struct = struct.Struct('!I')
        self.host, self.port = sock.getpeername()

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def close(self):
        self._sock.close()

    def send(self, message):
        message = self._header_struct.pack(len(message)) + message
        self._sock.sendall(message)

    def recv(self):
        data = self._recvall(self._header_struct.size)
        (block_length,) = self._header_struct.unpack(data)
        if block_length > self.max_packet_size:
            # Avoid MemoryError
            self.close()
            raise ConnectionClosed
        return self._recvall(block_length)

    def _recvall(self, length):
        blocks = list()
        while length:
            block = self._sock.recv(length)
            if not block:
                raise ConnectionClosed
            length -= len(block)
            blocks.append(block)
        return b''.join(blocks)


class ConnectionClosed(Exception):
    pass

