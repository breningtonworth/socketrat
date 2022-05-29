# -*- coding: utf-8 -*-

import struct


class Connection:

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
        #print('SOCK: {}, LENGTH: {}'.format(id(self._sock), block_length))
        if block_length > 4096:
            # A large recv length can raise a MemoryError.
            # Close connection on anything > 4096.
            #print('POTENTIAL MEMORY ERROR, CLOSING CONNECTION.')
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

