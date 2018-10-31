# Copyright (c) 2018 Evalf
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import contextlib
from . import abc, _io

class RecordLog(abc.Log):
  '''Record log messages.

  The recorded messages can be replayed to the logs that are currently active
  by :meth:`replay`. Typical usage is caching expensive operations::

      # compute
      with RecordLog() as record:
        result = compute_something_expensive()
      raw = pickle.dumps((record, result))
      # reuse
      record, result = pickle.loads(raw)
      record.replay()

  .. Note::
     Exceptions raised while in a :meth:`Log.context` are not recorded.
  '''

  def __init__(self):
    # Replayable log messages.  Each entry is a tuple of `(cmd, *args)`, where
    # `cmd` is either 'context_enter', 'context_exit', 'open_enter',
    # 'open_exit' or 'write'.  See `self.replay` below.
    self._messages = []
    self._seen = {}

  def pushcontext(self, title):
    self._messages.append(('context_enter', title))

  def popcontext(self):
    if self._messages and self._messages[-1][0] == 'context_enter':
      self._messages.pop()
    else:
      self._messages.append(('context_exit',))

  @contextlib.contextmanager
  def open(self, filename, mode, level, id):
    self._messages.append(('open_enter', filename, mode, level, id))
    try:
      data = self._seen.get(id)
      if data is not None:
        with _io.devnull(filename) as f:
          yield f
      else:
        with _io.tempfile(filename, mode) as f:
          yield f
          f.seek(0)
          data = f.read()
        if id:
          self._seen[id] = data
    finally:
      self._messages.append(('open_exit', data))

  def write(self, text, level):
    self._messages.append(('write', text, level))

  def replay(self, log=None):
    '''Replay this recorded log.

    All recorded messages and files will be written to the log that is either
    directly specified or currently active.'''

    contexts = []
    if log is None:
      from . import current as log
    for cmd, *args in self._messages:
      if cmd == 'context_enter':
        ctx = log.context(*args)
        ctx.__enter__()
        contexts.append(ctx)
      elif cmd == 'context_exit':
        ctx = contexts.pop()
        ctx.__exit__(None, None, None)
      elif cmd == 'open_enter':
        ctx = log.open(*args)
        contexts.append((ctx, ctx.__enter__()))
      elif cmd == 'open_exit':
        ctx, f = contexts.pop()
        if args[0] is not None:
          f.write(args[0])
        ctx.__exit__(None, None, None)
      elif cmd == 'write':
        log.write(*args)

# vim:sw=2:sts=2:et
