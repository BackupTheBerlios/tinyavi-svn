#
# Operating System Wrapper for WINDOWS
#

import os
import ctypes


SRCPATH = os.path.abspath (os.path.dirname (sys.argv [0]))

MPLAYER = os.path.join (SRCPATH, "mplayer", "mplayer.exe")
if not os.access (MPLAYER, 0):
    MPLAYER = "mplayer.exe"

MENCODER = os.path.join (SRCPATH, "mplayer", "mencoder.exe")
if not os.access (MENCODER, 0):
    MENCODER = "mencoder.exe"


def Quote (self, s):
    return '"' + s.replace ('"', r'\"') + '"'


def Kill (self, pid):
    handle = ctypes.windll.kernel32.OpenProcess (1, False, pid)
    ctypes.windll.kernel32.TerminateProcess (handle, -1)
    ctypes.windll.kernel32.CloseHandle (handle)


def GenScriptPlay (opts):
    opts ["mplayer"] = MPLAYER
    return u"""@echo off
rem This file has been generated by TinyAVI

%(mplayer)s %(opts)s -noaspect %(input)s 2>&1
""" %opts


def GenScriptEncode (opts):
    opts ["mencoder"] = MENCODER
    opts ["devnull"] = os.devnull
    return u"""@echo off
rem This file has been generated by TinyAVI

echo "-= STAGE 1 =-"
%(mencoder)s %(pass1opts)s %(input)s -o %(devnull)s 2>&1 && \
echo "-= STAGE 2 =-" && \
%(mencoder)s %(pass2opts)s -force-avi-aspect %(aspect)s %(input)s -o %(output)s 2>&1
""" %opts