# Copyright (C) 2015 Sebastian Pipping <sebastian@pipping.org>
# Licensed under GPL v2 or later

import errno
import os


def which(command):
    if '/' in command:
        return command

    for folder in os.environ['PATH'].split(':'):
        candidate = os.path.join(folder, command)

        if not os.path.isfile(candidate):
            continue

        if not os.access(candidate, os.X_OK):
            raise OSError(errno.EPERM, 'File "%s" not executable' % candidate)

        return candidate

    raise OSError(errno.ENOENT, 'Command "%s" not found' % command)
