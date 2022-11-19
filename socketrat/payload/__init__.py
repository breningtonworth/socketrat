# -*- coding: utf-8 -*-

import platform

if platform.system() == 'Windows':
    from .windows import *
elif platform.system() == 'Linux':
    from .linux import *

