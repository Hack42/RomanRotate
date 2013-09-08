#!/usr/bin/env python

import sys
import os
import re
import getopt
import ctypes
import shutil

libc = ctypes.CDLL('libc.so.6')

def debug(argv):
    global verbose
    if verbose:
        print >>sys.stderr, "DBG: %s" % argv

def dec2rom(input):
   """
   Convert a decimal to Roman numerals.
   """
   assert(isinstance(input, int)), "expected integer, got %s" % type(input)
   assert(-1 < input < 4000), "Argument must be between 0 and 3999"   
   ints = (1000, 900,  500, 400, 100,  90, 50,  40, 10,  9,   5,  4,   1)
   nums = ('M',  'CM', 'D', 'CD','C', 'XC','L','XL','X','IX','V','IV','I')
   result = ""
   for i in range(len(ints)):
      count = int(input / ints[i])
      result += nums[i] * count
      input -= ints[i] * count
   return result


def rom2dec(input):
   """
   Convert a roman numeral to a decimal.
   """
   assert(isinstance(input, basestring)), "expected string, got %s" % type(input)
   assert(re.match(r'^[MDCLXVI]*$', input)), "not a valid roman numeral: %s" % input
   input = input.upper()
   nums = ['M', 'D', 'C', 'L', 'X', 'V', 'I']
   ints = [1000, 500, 100, 50,  10,  5,   1]
   retValue = 0
   for i in range(len(input)):
      value = ints[nums.index(input[i])]
      # If the next place holds a larger number, this value is negative.
      try:
         if ints[nums.index(input[i +1])] > value:
            value *= -1
      except IndexError:
         # there is no next place.
         pass
      retValue += value
   # Easiest test for validity...
   if dec2rom(retValue) == input:
      return retValue
   else:
      raise ValueError, 'input is not a valid roman numeral: %s' % input

def keys(value):
    if re.match(r'([MDCLXVI]*)', value):
        debug("Roman: %s, Decimal %s" % (value, rom2dec(value)))
        return((rom2dec(value), value))
    else:
        return((value, dec2rom(value)))

def usage():
    print """
    Usage:          %s [-v] [-h] [-d delimiter] [-l] [-t] file [file]
    Description:    Performs logrotation with roman numbering.

    -v              Verbose, show debug output
    -h              Help, show this usage
    -d delimiter    delimiter between filename and roman extension
                    deault; '.'
    -l              List the rotates files ordered by number
    -t              Reverse rotation or list
                    Attention: this might cause loss of data in the most recent logfile!

    file            the filename without numbers, i.e. "logfile.log" or "/path/to/logfile.log"
    """ % sys.argv[0]

class FileList(set):
    def __init__(self, directory, filename, delimiter):
        if(directory!=''):
            self._directory = directory
        else:
            self._directory = '.'
        self._filename = filename
        self._delimiter = delimiter
        debug('Getting files for %s in directory %s' % (self._filename, self._directory))
        for file in os.listdir(self._directory):
            try:
                parts = re.split(r'(%s)([%s]*)([MCXDVIL]*)' % (self._filename, self._delimiter), file)
                if parts[1] == self._filename:
                    debug('Adding: %s %s' % (file, parts))
                    self.add(keys(parts[3]) + (parts[1], file,))
            except Exception, err:
                debug(err)
                debug('Ignoring: %s' % file)
                pass

    def sort(self, reverse=False):
       return sorted(self, key=lambda file: file[0], reverse=reverse)

if __name__ == "__main__":
    global verbose
    verbose = False
    listOnly = False
    reverse = False
    delimiter = '.'
    optlist, args = getopt.getopt(sys.argv[1:], 'lthvd:')
    for option, value in optlist:
        if(option == '-v'):
            verbose = True
        if(option == '-l'):
            listOnly = True
        if(option == '-t'):
            reverse = True
        if(option == '-d'):
            delimiter = optarg
        if(option == '-h'):
            usage()
            exit
    debug('Verbose is on')
    debug('Filenames: %s' % args)
    for item in args:
        debug('Processing: %s' % item)
        myList = FileList(os.path.dirname(item), os.path.basename(item), delimiter)
        if listOnly:
            for file in myList.sort(reverse):
                print file[3]
        else:
            for file in myList.sort(not reverse):
                number = dec2rom(file[0] - (+1 if reverse else -1))
                filename = file[2] + (("." + number) if number != "" else "")
                if file[3] == item and filename == '%s.I' % item:
                    # make sure all cached writes are flushed to disk, sync twice
                    libc.sync()
                    libc.sync()
                    # Copy the logfile and truncate it. This way it keeps
                    # it's original inode.
                    shutil.copy2(file[3], filename)
                    open(file[3], 'w').close()
                    libc.sync()
                else:
                    debug('renaming %s to %s.' % (file[3], "%s" % filename))
                    os.rename(file[3], "%s" % filename)
