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

import abc, functools, warnings, contextlib
from . import _io

class Closing(abc.ABC):
  '''Base class for enterable objects that close upon exit.

  A subclass should define the :meth:`close` method for cleanup that returns a
  true value if the object was found to be open.'''

  @abc.abstractmethod
  def close(self):
    raise NotImplementedError

  def __enter__(self):
    return self

  def __exit__(self, *args):
    self.close()

  def __del__(self):
    if self.close():
      warnings.warn('unclosed object {!r}'.format(self), ResourceWarning)

class ClosingGenerator(Closing):
  '''Enterable generator that close upon exit.

  Generator wrapper that tracks whether the generator was exhausted or closed
  manually to enable a destruction warning.'''

  @classmethod
  def compose(cls, f):
    return functools.wraps(f)(lambda *args, **kwargs: cls(f(*args, **kwargs)))

  def __init__(self, gen):
    self._gen = gen

  def __iter__(self):
    return self

  def __next__(self):
    if not self._gen:
      raise StopIteration
    try:
      return next(self._gen)
    except StopIteration:
      self._gen = None
      raise

  def close(self):
    if self._gen:
      self._gen.close()
      self._gen = None
      return True

class Log(abc.ABC):
  '''Abstract base class for log objects.

  A subclass must define a :meth:`context` method that handles a context
  change, a :meth:`write` method that logs a message, and an :meth:`open`
  method that returns a file context.'''

  @abc.abstractmethod
  def pushcontext(self, title):
    raise NotImplementedError

  @abc.abstractmethod
  def popcontext(self):
    raise NotImplementedError

  @abc.abstractmethod
  def write(self, text, level):
    raise NotImplementedError

  @abc.abstractmethod
  def open(self, filename, mode, level, id):
    raise NotImplementedError

  @contextlib.contextmanager
  def context(self, text):
    self.pushcontext(text)
    try:
      yield
    finally:
      self.popcontext()

  @ClosingGenerator.compose
  def iter(self, title, iterable, length=None):
    if length is None:
      try:
        length = len(iterable)
      except:
        pass
    iterator = iter(iterable)
    i = 0
    while True:
      text = '{} {}'.format(title, i)
      if length:
        text += ' ({:.0f}%)'.format(100 * (i+.5) / length)
      self.pushcontext(text)
      try:
        val = next(iterator)
      except StopIteration:
        return
      else:
        yield val
      finally:
        self.popcontext()
      i += 1

  def _factory(level):

    def print(self, *args, sep=' '):
      '''Write message to log.

      Args
      ----
      *args : tuple of :class:`str`
          Values to be printed to the log.
      sep : :class:`str`
          String inserted between values, default a space.
      '''
      self.write(sep.join(map(str, args)), level)

    def file(self, name, mode, *, id=None):
      '''Open file in logger-controlled directory.

      Args
      ----
      filename : :class:`str`
      mode : :class:`str`
          Should be either ``'w'`` (text) or ``'wb'`` (binary data).
      id :
          Bytes identifier that can be used to decide a priori that a file has
          already been constructed. Default: None.
      '''
      return self.open(name, mode, level, id)

    name = ['debug', 'info', 'user', 'warning', 'error'][level]
    print.__name__ = name
    print.__qualname__ = 'Log.' + name
    file.__name__ = name + 'file'
    file.__qualname__ = 'Log.' + name + 'file'
    return print, file

  debug,   debugfile   = _factory(0)
  info,    infofile    = _factory(1)
  user,    userfile    = _factory(2)
  warning, warningfile = _factory(3)
  error,   errorfile   = _factory(4)

  del _factory

# vim:sw=2:sts=2:et
