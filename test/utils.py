#!/usr/bin/env python
#
# Copyright 2016 WebAssembly Community Group participants
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import contextlib
import os
import shutil
import signal
import subprocess
import sys
import tempfile

# Get signal names from numbers in Python
# http://stackoverflow.com/a/2549950
SIGNAMES = dict((k, v) for v, k in reversed(sorted(signal.__dict__.items()))
                       if v.startswith('SIG') and not v.startswith('SIG_'))

class Error(Exception):
  pass


class Executable(object):
  def __init__(self, exe, *before_args, **kwargs):
    self.exe = exe
    self.before_args = list(before_args)
    self.after_args = []
    self.error_cmdline = kwargs.get('error_cmdline', True)
    self.clean_stdout = kwargs.get('clean_stdout')
    self.clean_stderr = kwargs.get('clean_stderr')

  def RunWithArgs(self, *args):
    cmd = [self.exe] + self.before_args + list(args) + self.after_args
    cmd_str = ' '.join(cmd)

    err_cmd_str = cmd_str
    if not self.error_cmdline:
      err_cmd_str = os.path.basename(self.exe)

    try:
      process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
      stdout, stderr = process.communicate()
      if self.clean_stdout:
        stdout = self.clean_stdout(stdout)
      if self.clean_stderr:
        stderr = self.clean_stderr(stderr)
      sys.stdout.write(stdout)
      if process.returncode < 0:
        # Terminated by signal
        signame = SIGNAMES.get(-process.returncode, '<unknown>')
        raise Error('Signal raised running "%s": %s\n%s' % (
                    err_cmd_str, signame, stderr))
      elif process.returncode > 0:
        raise Error('Error running "%s":\n%s' % (err_cmd_str, stderr))
    except OSError as e:
      raise Error('Error running "%s": %s' % (err_cmd_str, str(e)))

  def AppendArg(self, arg):
    self.after_args.append(arg)

  def AppendOptionalArgs(self, option_dict):
    for option, value in option_dict.iteritems():
      if value:
        self.AppendArg(option)


@contextlib.contextmanager
def TempDirectory(out_dir, prefix=None):
  if out_dir:
    out_dir_is_temp = False
    if not os.path.exists(out_dir):
      os.makedirs(out_dir)
  else:
    out_dir = tempfile.mkdtemp(prefix=prefix)
    out_dir_is_temp = True

  try:
    yield out_dir
  finally:
    if out_dir_is_temp:
      shutil.rmtree(out_dir)


def ChangeExt(path, new_ext):
  return os.path.splitext(path)[0] + new_ext


def ChangeDir(path, new_dir):
  return os.path.join(new_dir, os.path.basename(path))


def Hexdump(data):
  DUMP_OCTETS_PER_LINE = 16
  DUMP_OCTETS_PER_GROUP = 2

  p = 0
  end = len(data)
  lines = []
  while p < end:
    line_start = p
    line_end = p +  DUMP_OCTETS_PER_LINE
    line = '%07x: ' % p
    while p < line_end:
      for i in xrange(DUMP_OCTETS_PER_GROUP):
        if p < end:
          line += '%02x' % ord(data[p])
        else:
          line += '  '
        p += 1
      line += ' '
    line += ' '
    p = line_start
    for i in xrange(DUMP_OCTETS_PER_LINE):
      if p >= end:
        break
      x = data[p]
      o = ord(x)
      if o >= 32 and o < 0x7f:
        line += '%c' % x
      else:
        line += '.'
      p += 1
    line += '\n'
    lines.append(line)

  return lines
