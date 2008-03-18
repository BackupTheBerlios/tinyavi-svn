#
# This script will convert an AVI file to a tiny-resolution AVI file
# suitable for displaying on small devices such as PDAs. Being restricted
# by target resolution and file size, this script tries to keep quality
# as high as possible.
#

import re
import os
import sys
import gettext
import signal
import locale
from popen2 import Popen3
from tinyavi import FNENC


def quote(s):
    return "'" + s.replace ("'", r"'\''") + "'"


class VideoParam:
    # Video length in seconds
    length = 0
    # Aspect rate
    aspect = 1
    # Crop boundary
    cx = 9999
    cy = 9999
    cw = 0
    ch = 0
    # Video width and height
    vw = 0
    vh = 0
    # Width and height after rescaling
    sw = 0
    sh = 0

    def ExtendCrop (self, x, y, w, h):
        if w <= 0 or h <= 0:
            return
        if self.cx > x:
            self.cx = x;
        if self.cy > y:
            self.cy = y;
        if self.cw < w:
            self.cw = w;
        if self.ch < h:
            self.ch = h;

class AutoConvertAVI:
    def __init__ (self, _gettext, _print):
        global _, pr
        _ = _gettext
        pr = _print

    def FindVideoLengthCrop (self, fn):
        res = VideoParam ()
        pr (_("Finding video length, crop and size ..."))
        sys.stderr.flush ()
        prevl = ""
        # -sstep 10 -- with this option cropdetect doesn't work with many AVIs :-(
        # -speed 100 -endpos 10:0 helps a little here...
        p = Popen3 ("exec mplayer -identify -benchmark -vo null -nosound -vf cropdetect -speed 100 -endpos 10:0 " + quote (fn).encode (FNENC) + " 2>/dev/null </dev/null");
        while True:
            l = p.fromchild.readline ()
            if l == "" or (l [0:2] == "V:" and l == prevl):
                break
            prevl = l
            l = re.sub ("^V:.*\r", "", l.strip ())
            if re.match (r"^ID_LENGTH=", l):
                res.length = int (re.sub (r".*=([0-9]+)[^0-9]*", r"\1", l))
            elif re.match (r"^ID_VIDEO_ASPECT=", l):
                res.aspect = int (re.sub (r".*=([0-9]+)[^0-9]*", r"\1", l))
            elif re.match (r"^ID_VIDEO_WIDTH=", l):
                res.vw = int (re.sub (r".*=([0-9]+)[^0-9]*", r"\1", l))
            elif re.match (r"^ID_VIDEO_HEIGHT=", l):
                res.vh = int (re.sub (r".*=([0-9]+)[^0-9]*", r"\1", l))
            elif re.match (r"^crop area", l) or re.match (r"^\[CROP\]", l):
                bb = re.split (r"(X: *|Y: *|\()", l)
                xx = re.split (r"\.\.", bb [2])
                yy = re.split (r"\.\.", bb [4])

                xx [0] = int (xx [0])
                xx [1] = int (xx [1])
                yy [0] = int (yy [0])
                yy [1] = int (yy [1])

                res.ExtendCrop (xx[0], yy[0], xx[1] - xx[0] + 1, yy[1] - yy[0] + 1)

        # Kill and close process
        os.kill (p.pid, signal.SIGTERM)
        p.wait ()
        del p

        if res.length < 1:
            pr (_("\nUNEXPECTED ERROR: video length too small\n"))
            return None

        pr (" %d (%d,%d %dx%d)\n" %(res.length, res.cx, res.cy, res.cw, res.ch))

        return res

    def AddVideoFilter (self, newf):
        if self.vf != "": self.vf = self.vf + ","
        self.vf = self.vf + newf
        pr (_("Adding video filter: %s\n") %newf)

    def AnalyseAVI (self, fn, options):
        pr (_("Analysing file %s\n") %fn)

        if not os.access (fn.encode (FNENC), os.R_OK):
            pr (_("ERROR: file `%s' does not exist or is not readable\n") %fn)
            return None

        self.vf = options.vf
        self.video_opt = ""
        self.audio_opt = ""
        self.xvid_opt = "psnr:turbo:trellis:vhq=2"
        self.outfile = options.OutFile
        if self.outfile == None:
            x = os.path.splitext (fn)
            self.outfile = x [0] + "-small" + x [1]

        if options.AudioID != None:
            self.audio_opt = self.audio_opt + " -aid %d" %options.AudioID

        vp = self.FindVideoLengthCrop (fn)
        if vp == None:
            return None

        if vp.cx != 0 or vp.cy != 0 or vp.cw != vp.vw or vp.ch != vp.vh:
            self.AddVideoFilter ("crop=%d:%d:%d:%d" %(vp.cw, vp.ch, vp.cx, vp.cy))

        if options.Deint:
            self.AddVideoFilter ("kerndeint")
        if options.Denoise:
            self.AddVideoFilter ("hqdn3d=2:1:2")

        # Find out rescaled size of the video
        vp.sw = float (vp.cw)
        vp.sh = float (vp.ch)
        if vp.sw > options.Width:
            vp.sh = float (options.Width * vp.sh) / vp.sw
            vp.sw = float (options.Width)
        if vp.sh > options.Height:
            vp.sw = float (options.Height * vp.sw) / vp.sh
            vp.sh = float (options.Height)

        # For wide-format video, scale it a bit so that it's closer
        # to target screen proportions. This makes image a bit
        # unproportional, but instead adds to the visible details
        srca = vp.sw / vp.sh
        dsta = float (options.Width) / options.Height
        aratio = (srca / dsta) - 1
        srca = (1 + (aratio / 2.0)) * dsta
        if vp.sw == options.Width:
            # Horizontally limited video
            vp.sh = vp.sw / srca
        else:
            # Vertically limited video
            vp.sw = vp.sh * srca

        # Allow only sizes multiple of 16 (macroblock size).
        vp.sw = int ((vp.sw + 8) / 16) * 16
        vp.sh = int ((vp.sh + 8) / 16) * 16

        # Last dirty check (should never happen, but who knows)
        if vp.sw > options.Width:
            vp.sw = options.Width
        if vp.sh > options.Height:
            vp.sh = options.Height

        if vp.sw != vp.cw or vp.sh != vp.vh:
            self.AddVideoFilter ("scale=%d:%d" %(vp.sw, vp.sh))

        aspect = float (vp.sw) / vp.sh

        # This formula gives 200 kbits for 320x240
        bitrate = (vp.sw * vp.sh) / 384

        if options.Play:
            s = u"""#!/bin/sh
# This file has been generated by TinyAVI

mplayer %(vopts)s -vf %(vf)s -aspect %(aspect)g %(input)s
""" %{'vopts': self.video_opt, 'aspect': aspect, 'vf': self.vf, 'input': quote (fn)}
        elif options.PassAudio:
            s = u"""#!/bin/sh
# This file has been generated by TinyAVI

echo "-= STAGE 1 =-"
mencoder %(vopts)s -oac copy -ovc xvid -xvidencopts %(xvo)s:max_bframes=0:pass=1 \\
    -vf %(vf)s %(input)s -o /dev/null 2>&1 && \\
echo "-= STAGE 2 =-" && \\
mencoder %(vopts)s -oac copy -ovc xvid -xvidencopts %(xvo)s:max_bframes=0:bitrate=%(bitrate)d:pass=2 \\
    -force-avi-aspect %(aspect)g -vf %(vf)s %(input)s -o %(output)s 2>&1
""" %{'vopts': self.video_opt, 'aopts': self.audio_opt, \
        'xvo': self.xvid_opt, 'aspect': aspect, 'bitrate': bitrate, \
        'vf': self.vf, 'input': quote (fn), 'output': quote (self.outfile)}
        else:
            s = u"""#!/bin/sh
# This file has been generated by TinyAVI

echo "-= STAGE 1 =-"
mencoder -ovc xvid -xvidencopts %(xvo)s:max_bframes=0:pass=1 %(vopts)s \\
    -vf %(vf)s -nosound %(input)s -o /dev/null 2>&1 && \\
echo "-= STAGE 2 =-" && \\
mencoder -ovc xvid -xvidencopts %(xvo)s:max_bframes=0:bitrate=%(bitrate)d:pass=2 \\
    -vf %(vf)s %(vopts)s -force-avi-aspect %(aspect)g \\
    -oac mp3lame -lameopts q=8:mode=1:aq=3 %(aopts)s \\
    %(input)s -o %(output)s 2>&1
""" %{'vopts': self.video_opt, 'aopts': self.audio_opt, \
        'xvo': self.xvid_opt, 'aspect': aspect, 'bitrate': bitrate, \
        'vf': self.vf, 'input': quote (fn), 'output': quote (self.outfile)}

        pr (_("Analysing finished\n"))
        return s
