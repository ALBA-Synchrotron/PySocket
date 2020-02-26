# -*- coding: utf-8 -*-
#
# This file is part of the PySocket project
#
#
#
# Distributed under the terms of the GPL license.
# See LICENSE.txt for more info.

""" Python Socket Device Server

Reimplementation of C++ Socket Device in python
"""

# PyTango imports
import PyTango
from PyTango import DebugIt
from PyTango.server import run
from PyTango.server import Device, DeviceMeta
from PyTango.server import attribute, command
from PyTango.server import device_property
from PyTango import AttrQuality, DispLevel, DevState
from PyTango import AttrWriteType, PipeWriteType
# Additional import
# PROTECTED REGION ID(PySocket.additionnal_import) ENABLED START #
import socket, traceback, time, asyncio, select
# PROTECTED REGION END #    //  PySocket.additionnal_import

__all__ = ["PySocket", "main"]


class PySocket(Device):
    """
    Reimplementation of C++ Socket Device in python
    """
    __metaclass__ = DeviceMeta
    # PROTECTED REGION ID(PySocket.class_variable) ENABLED START #
    
    def process_exception(self, e=None, tr = None, throw = True):
        exc = tr or str(e) or traceback.format_exc()
        exc = "Unable to connect to %s:%s\n%s" % (
            self.Hostname, self.Port, exc)
        self.set_status(exc)
        self.process_state(DevState.FAULT)
        self.error_stream(exc)
        if throw and e:
            raise e
        
    def process_state(self, state):
        old = self.get_state()
        self.info_stream('%s => %s' % (old,state))
        self.set_state(state)
        self.push_change_event('State',self.get_state())        
        
    # PROTECTED REGION END #    //  PySocket.class_variable

    # -----------------
    # Device Properties
    # -----------------

    Hostname = device_property(
        dtype='str',
        mandatory=True
    )

    Port = device_property(
        dtype='int',
        mandatory=True
    )

    Readtimeout = device_property(
        dtype='int16', default_value=250
    )

    AutoReconnect = device_property(
        dtype='bool', default_value=False
    )

    Encoding = device_property(
        dtype='str', default_value="utf-8"
    )

    # ----------
    # Attributes
    # ----------

    hostname = attribute(
        dtype='str',
    )

    port = attribute(
        dtype='int',
    )

    # ---------------
    # General methods
    # ---------------

    def init_device(self):
        Device.init_device(self)
        # PROTECTED REGION ID(PySocket.init_device) ENABLED START #
        self.info_stream('init_device()')

        if not hasattr(self,'sobj'):
            self.sobj = None
            self.set_change_event('State',True,False)
            self.process_state(DevState.CLOSE)
            self.buffer = ''
            
        self.info_stream('init_device(): done')
        # PROTECTED REGION END #    //  PySocket.init_device

    def always_executed_hook(self):
        # PROTECTED REGION ID(PySocket.always_executed_hook) ENABLED START #
        pass
        # PROTECTED REGION END #    //  PySocket.always_executed_hook

    def delete_device(self):
        # PROTECTED REGION ID(PySocket.delete_device) ENABLED START #
        self.info_stream('delete_device()')
        self.Close()
        # PROTECTED REGION END #    //  PySocket.delete_device

    # ------------------
    # Attributes methods
    # ------------------

    def read_hostname(self):
        # PROTECTED REGION ID(PySocket.hostname_read) ENABLED START #
        return ''
        # PROTECTED REGION END #    //  PySocket.hostname_read

    def read_port(self):
        # PROTECTED REGION ID(PySocket.port_read) ENABLED START #
        return 0
        # PROTECTED REGION END #    //  PySocket.port_read


    # --------
    # Commands
    # --------

    @command(
    )
    @DebugIt()
    def Reconnect(self):
        # PROTECTED REGION ID(PySocket.Reconnect) ENABLED START #
        try:
            self.Close()
            self.sobj = socket.socket()
            self.sobj.setblocking(False)
            self.sobj.settimeout(1e-3*self.Readtimeout)
            argin = (str(self.Hostname),int(self.Port))
            self.info_stream('Reconnect(%s)' % str(argin))
            self.sobj.connect(argin)
            self.process_state(DevState.OPEN)
            self.info_stream('Reconnected!')
        except Exception as e:
            self.process_exception(e,traceback.format_exc(),True)
        # PROTECTED REGION END #    //  PySocket.Reconnect

    @command(
    dtype_in='str', 
    )
    @DebugIt()
    def Write(self, argin):
        # PROTECTED REGION ID(PySocket.Write) ENABLED START #
        self.info_stream('Write(%s(%s))' % (type(argin),argin))
        
        try:
            if self.AutoReconnect:
                if self.get_state() != DevState.OPEN or not self.Check():
                    self.Reconnect()
            
            self.sobj.send((str(argin).encode(self.Encoding)))

        except Exception as e:
            self.process_exception(e,traceback.format_exc(),True)
            
        # PROTECTED REGION END #    //  PySocket.Write

    @command(
    dtype_in='str', 
    doc_in="Command string.", 
    dtype_out='str', 
    doc_out="Answer string.", 
    )
    @DebugIt()
    def WriteAndRead(self, argin):
        # PROTECTED REGION ID(PySocket.WriteAndRead) ENABLED START #
        self.Write(argin)
        return self.Read()
        # PROTECTED REGION END #    //  PySocket.WriteAndRead

    @command(
    dtype_out='str', 
    )
    @DebugIt()
    def Read(self):
        # PROTECTED REGION ID(PySocket.Read) ENABLED START #
        return self.ReadUntil(None)
        # PROTECTED REGION END #    //  PySocket.Read

    @command(
    dtype_in='str', 
    doc_in="This is the terminator", 
    dtype_out='str', 
    doc_out="This is the read string.", 
    )
    @DebugIt()
    def ReadUntil(self, argin):
        # PROTECTED REGION ID(PySocket.ReadUntil) ENABLED START #
        self.info_stream('ReadUntil(%s): buffer = %s' % (argin,self.buffer))

        if self.AutoReconnect:
            if self.get_state() != DevState.OPEN or not self.Check():
                self.Reconnect()

        try:
            t0 = time.time()
            argout = ''
            tt = max((self.Readtimeout/100e3,.001)) #250ms => 2.5ms wait
            while 1:
                time.sleep(tt)
                if self.buffer:
                    r = self.buffer
                else:
                    # if timeout is reached, exception will raise here
                    r = self.sobj.recv(1024).decode(self.Encoding)

                self.buffer = ''
                if argin and argin in r:
                    self.info_stream('ReadUntil(%s): %s' % (
                        argin, r))                    
                    r = r.split(argin,1)                    
                    argout, self.buffer = argout+r[0], r[1]
                    self.info_stream('ReadUntil(%s): argout/buffer: %s / %s' 
                        % (argin, argout, self.buffer))
                    break
                elif not argin and not r and not self.Readtimeout:
                    break
                else:
                    argout += r
                #if time.time()-t0 > self.Readtimeout:
                    #raise socket.timeout()
        except socket.timeout as e:
            self.info_stream('Socket Timeout after %d ms' 
                             % (1e3*(time.time()-t0)))
        except Exception as e:
            self.process_exception(e,traceback.format_exc(),True)
        return argout
        # PROTECTED REGION END #    //  PySocket.ReadUntil

    @command(
    )
    @DebugIt()
    def Close(self):
        # PROTECTED REGION ID(PySocket.Close) ENABLED START #
        if self.sobj is not None:
            try:
                self.sobj.close()
                self.sobj = None
                self.process_state(DevState.CLOSE)
            except Exception as e:
                self.process_exception(e,traceback.format_exc(),True)
        # PROTECTED REGION END #    //  PySocket.Close

    @command(
    dtype_out='bool', 
    doc_out="Return whether socket is available", 
    )
    @DebugIt()
    def Check(self):
        # PROTECTED REGION ID(PySocket.Check) ENABLED START #
        check = select.select([self.sobj],[self.sobj],[])
        self.info_stream('Check(): %s' % str(check))
        if not any(check):
            self.process_exception(tr='Check():Socket closed on server side?')
            
        return self.get_state() not in (DevState.FAULT,DevState.CLOSE)
        # PROTECTED REGION END #    //  PySocket.Check

# ----------
# Run server
# ----------


def main(args=None, **kwargs):
    # PROTECTED REGION ID(PySocket.main) ENABLED START #
    return run((PySocket,), args=args, **kwargs)
    # PROTECTED REGION END #    //  PySocket.main

if __name__ == '__main__':
    main()
