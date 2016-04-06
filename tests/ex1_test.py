#!/usr/bin/python

from __future__ import division
from struct import calcsize
import fcntl
import os
import sys
import unittest
import errno
import random

#
# Globals
#
MODULE_NAME = 'my_module'
DEVICE_NAME = 'my_device'
if len(sys.argv) > 1 and os.path.exists(sys.argv[-1]):
    MODULE_PATH = sys.argv.pop()
else:
    MODULE_PATH = 'my_module.o'


#
# Utilities for calculating the IOCTL command codes.
#
sizeof = {
    'byte': calcsize('c'),
    'signed byte': calcsize('b'),
    'unsigned byte': calcsize('B'),
    'short': calcsize('h'),
    'unsigned short': calcsize('H'),
    'int': calcsize('i'),
    'unsigned int': calcsize('I'),
    'long': calcsize('l'),
    'unsigned long': calcsize('L'),
    'long long': calcsize('q'),
    'unsigned long long': calcsize('Q')
}

_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRMASK = ((1 << _IOC_NRBITS)-1)
_IOC_TYPEMASK = ((1 << _IOC_TYPEBITS)-1)
_IOC_SIZEMASK = ((1 << _IOC_SIZEBITS)-1)
_IOC_DIRMASK = ((1 << _IOC_DIRBITS)-1)

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = (_IOC_NRSHIFT+_IOC_NRBITS)
_IOC_SIZESHIFT = (_IOC_TYPESHIFT+_IOC_TYPEBITS)
_IOC_DIRSHIFT = (_IOC_SIZESHIFT+_IOC_SIZEBITS)

_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2

def _IOC(dir, _type, nr, size):
    if type(_type) == str:
        _type = ord(_type)
        
    cmd_number = (((dir)  << _IOC_DIRSHIFT) | \
        ((_type) << _IOC_TYPESHIFT) | \
        ((nr)   << _IOC_NRSHIFT) | \
        ((size) << _IOC_SIZESHIFT))

    return cmd_number

def _IO(_type, nr):
    return _IOC(_IOC_NONE, _type, nr, 0)

def _IOR(_type, nr, size):
    return _IOC(_IOC_READ, _type, nr, sizeof[size])

def _IOW(_type, nr, size):
    return _IOC(_IOC_WRITE, _type, nr, sizeof[size])

#
# Calculate the ioctl cmd number
#
MY_MAGIC = 'r'
MY_RESET   = _IOW(MY_MAGIC, 0, 'int')
MY_RESTART = _IOW(MY_MAGIC, 1, 'int')
MY_INVALID_IOCTL = _IOW(MY_MAGIC, 128, 'int')


class TestsBase(unittest.TestCase):
    _major = None
    _nodes = []
    def setUp(self):
        self._load_module(MODULE_PATH)
        try:
            self._major = self._get_major(DEVICE_NAME)
        except:
            self._unload_module(MODULE_NAME)
            raise
    def tearDown(self):
        for node in self._nodes:
            if os.path.isfile(node):
                os.unlink(node)
        self._unload_module(MODULE_NAME)
    def _load_module(self, path):
        rc = os.system('insmod %s' % path)
        self.assertEqual(rc, 0)
    def _unload_module(self, name):
        rc = os.system('rmmod %s' % name)
        self.assertEqual(rc, 0)
    def _get_major(self, devname):
        cmd = 'cat /proc/devices | grep %s | cut -f 1 -d " "' % devname
        major = os.popen(cmd).read().strip()
        self.assertNotEqual(major, '')
        return int(major)

    def _mknod(self, minor, path=None):
        if path is not None:
            if os.path.isfile(path):
                raise AssertionError("mknod fail: device path exists")
        if path is None:
            for i in range(100):
                # generate random device path
                path = '/dev/my_device_%d' % random.randrange(1<<30)
                if not os.path.isfile(path):
                    break
            else:
                raise RuntimeError("Failed finding free device path")
        cmd = 'mknod %s c %d %d' % (path, self._major, minor)
        rc = os.system(cmd)
        self.assertEqual(rc, 0)
        # save node path to cleanup
        self._nodes.append(path)
        return path
    def _rmnod(self, path):
        if os.path.exists(path):
            os.unlink(path)

    def _test_ENOTTY(self, callable):
        try:
            callable()
        except IOError, e:
            if e.errno == errno.ENOTTY:
                pass
            else:
                raise AssertionError("IOError, raised, but not ENOTTY")
        else:
            raise AssertionError("No IOError raised")
    def _test_ENOMEM(self, callable):
        try:
            callable()
        except OSError, e:
            if e.errno == errno.ENOMEM:
                pass
            else:
                raise AssertionError("OSError, raised, but not ENOMEM")
        else:
            raise AssertionError("No ENOMEM raised")

class SimpleTests(TestsBase):
    _device = None
    def setUp(self):
        TestsBase.setUp(self)
        try:
            self._device = self._mknod(0)
        except:
            TestsBase.tearDown(self)
            raise
    def tearDown(self):
        try:
            self._rmnod(self._device)
            self._device = None
        finally:
            TestsBase.tearDown(self)

    def test_simple(self):
        hello = 'hello world'
        f = os.open(self._device, os.O_RDWR)
        try:
            fcntl.ioctl(f, MY_RESET)
            os.write(f, hello)
            self.assertEqual(hello, os.read(f, len(hello)))
        finally:
            os.close(f)
    def test_write_max(self):
        # write more than 4096
        f = os.open(self._device, os.O_RDWR)
        try:
            fcntl.ioctl(f, MY_RESET)
            for i in range(4096):
                os.write(f, 'a')
            self._test_ENOMEM(lambda: os.write(f, 'a'))
            read = os.read(f, 100000)
            self.assertEqual(read, 'a'*4096)
        finally:
            os.close(f)
    def test_write_max_once(self):
        # write more than 4096
        f = os.open(self._device, os.O_RDWR)
        try:
            fcntl.ioctl(f, MY_RESET)
            os.write(f, 'hiush')
            self._test_ENOMEM(lambda: os.write(f, 'a'*4096))
            read = os.read(f, 100000)
            self.assertEqual(read, 'hiush')
        finally:
            os.close(f)
    def test_read_no_write(self):
        f = os.open(self._device, os.O_RDWR)
        try:
            fcntl.ioctl(f, MY_RESET)
            read = os.read(f, 10)
            self.assertEqual(read, '')
        finally:
            os.close(f)
    def test_write_special(self):
        f = os.open(self._device, os.O_RDWR)
        try:
            fcntl.ioctl(f, MY_RESET)
            s = ''.join(map(chr, range(256)))
            os.write(f, s)
            self.assertEqual(os.read(f, 1000), s)
        finally:
            os.close(f)
    def test_ioctl_reset(self):
        f = os.open(self._device, os.O_RDWR)
        try:
            fcntl.ioctl(f, MY_RESET)
            s = 'lolz'
            os.write(f, s)
            self.assertEqual(os.read(f, 4096), s)
            self.assertEqual(os.read(f, 4096), '')
            fcntl.ioctl(f, MY_RESET)
            os.write(f, s)
            self.assertEqual(os.read(f, 4096), s)
            self.assertEqual(os.read(f, 4096), '')
        finally:
            os.close(f)
    def test_ioctl_restart(self):
        f = os.open(self._device, os.O_RDWR)
        try:
            fcntl.ioctl(f, MY_RESET)
            s = 'lolz'
            os.write(f, s)
            self.assertEqual(os.read(f, 4096), s)
            self.assertEqual(os.read(f, 4096), '')
            fcntl.ioctl(f, MY_RESTART)
            os.write(f, s)
            self.assertEqual(os.read(f, 4096), s+s)
            self.assertEqual(os.read(f, 4096), '')
        finally:
            os.close(f)
    def test_optional_invalid_ioctl(self):
        f = os.open(self._device, os.O_RDWR)
        try:
            fcntl.ioctl(f, MY_RESET)
            self._test_ENOTTY(lambda: fcntl.ioctl(f, MY_INVALID_IOCTL))
        finally:
            os.close(f)
    def test_open_twice(self):
        f = os.open(self._device, os.O_RDWR)
        try:
            fcntl.ioctl(f, MY_RESET)
            s = 'lolz'
            os.write(f, s)
        finally:
            os.close(f)
        
        f = os.open(self._device, os.O_RDWR)
        try:
            self.assertEqual(os.read(f, 4096), s)
        finally:
            os.close(f)

class MoarTests(TestsBase):
    def test_multiple_nodes(self):
        minors = range(10)
        devices = [self._mknod(m) for m in minors]
        try:
            # write to all devices
            for minor, dev in zip(minors, devices):
                f = os.open(dev, os.O_RDWR)
                try:
                    fcntl.ioctl(f, MY_RESET)
                    s = 'minor %d device %s' % (minor, dev)
                    os.write(f, s)
                    self.assertEqual(os.read(f, 4096), s)
                    fcntl.ioctl(f, MY_RESTART)
                finally:
                    os.close(f)
            # read
            for minor, dev in zip(minors, devices):
                f = os.open(dev, os.O_RDWR)
                try:
                    s = 'minor %d device %s' % (minor, dev)
                    self.assertEqual(os.read(f, 4096), s)
                finally:
                    os.close(f)
        finally:
            for dev in devices:
                self._rmnod(dev)

if __name__ == '__main__':
    unittest.main()
