#
# This script will convert an AVI file to a tiny-resolution AVI file
# suitable for displaying on small devices such as PDAs. Being restricted
# by target resolution and file size, this script tries to keep quality
# as high as possible.
#

import re
import os
import sys
import math
import gettext
import signal
import locale
from subprocess import Popen, PIPE, STDOUT
from tinyavi import presets, FNENC, OSW


def AddFilter (val, desc, newf):
    pr (_("Adding %(desc)s filter: %(filt)s\n") % { "desc" : desc, "filt" : newf })
    if val != "": val += ","
    return val + newf

def atoi(txt):
    if not txt:
        return 0
    txt = str (txt)
    for i, c in enumerate (txt):
        if c not in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
            if i:
                return int (txt[:i])
            else:
                return 0
    return int (txt)

# Substitute %(...) macros in 's' with values from dict 'd'
# If s refers to missing keys in d, replace with empty strings
def Subst (s, d):
    while True:
        try:
            s = s % d
            break
        except KeyError,e:
            key = re.sub (r".*'([0-9a-zA-Z_]*)'", r"\1", str (e))
            d [key] = ""
    return s


class VideoParam:
    # Aspect rate
    aspect = 0
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
    # frames per second
    fps = 0

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
        pr (_("Finding video crop and size ..."))
        sys.stderr.flush ()
        DEVNULL = open (os.devnull, "rw")

        for start in (0, 150, 300, 600):
            prevl = ""
            count_equal = 0
            p = Popen ([OSW.MPLAYER, "-nomsgcolor", "-noconfig", "all", \
                        "-nouse-filedir-conf", "-identify", "-benchmark", \
                        "-vo", "null", "-nosound", "-vf", "cropdetect", \
                        "-frames", "100", "-ss", str (start), fn.encode (FNENC)], \
                        stdin = DEVNULL, stdout = PIPE, stderr = DEVNULL)
            while True:
                l = p.stdout.readline ()
                if l == prevl:
                    count_equal += 1
                else:
                    count_equal = 0
                if l == "" or (l [0:2] == "V:" and count_equal > 5):
                    break
                prevl = l
                l = re.sub (r"^V:.*\r", "", l.strip ())
                if re.match (r"^ID_VIDEO_ASPECT=", l):
                    res.aspect = float (re.sub (r".*=([.0-9]+)[^.0-9]*", r"\1", l))
                elif re.match (r"^ID_VIDEO_WIDTH=", l):
                    vw = atoi (re.sub (r".*=([0-9]+)[^0-9]*", r"\1", l))
                    if vw >= 16:
                        res.vw = vw;
                elif re.match (r"^ID_VIDEO_HEIGHT=", l):
                    vh = atoi (re.sub (r".*=([0-9]+)[^0-9]*", r"\1", l))
                    if vh >= 16:
                        res.vh = vh;
                elif re.match (r"^ID_VIDEO_FPS=", l):
                    res.fps = float (re.sub (r".*=([.0-9]+)[^.0-9]*", r"\1", l))
                elif re.match (r"^crop area", l) or re.match (r"^\[CROP\]", l):
                    bb = re.split (r"(X: *|Y: *|\()", l)
                    xx = re.split (r"\.\.", bb [2])
                    yy = re.split (r"\.\.", bb [4])

                    xx [0] = atoi (xx [0])
                    xx [1] = atoi (xx [1])
                    yy [0] = atoi (yy [0])
                    yy [1] = atoi (yy [1])

                    res.ExtendCrop (xx[0], yy[0], xx[1] - xx[0] + 1, yy[1] - yy[0] + 1)
                elif re.match (r"VDec: vo config request -", l):
                    bb = re.split (r"(- *| *x *| *\()", l)
                    if res.vw < 16:
                        res.vw = atoi (bb [2]);
                    if res.vh < 16:
                        res.vh = atoi (bb [4]);

            # Kill and close process
            OSW.Kill (p.pid)
            p.wait ()
            del p

        DEVNULL.close ()
        del DEVNULL

        if res.vw < 16 or res.vh < 16:
            pr (_("\nUNEXPECTED ERROR: video size too small\n"))
            return None

        if res.aspect == 0:
            res.aspect = float (res.vw) / res.vh
        if res.fps == 0:
            res.fps = 24.97

        pr (" (%d,%d %dx%d)\n" %(res.cx, res.cy, res.cw, res.ch))

        return res

    def AnalyseAVI (self, fn, options):
        pr (_("Analysing file %s\n") %fn)

        if not os.access (fn.encode (FNENC), os.R_OK):
            pr (_("ERROR: file `%s' does not exist or is not readable\n") %fn)
            return None

        if (options.Quality < 0) or (options.Quality > 2):
            pr (_("ERROR: Quality value is not allowed (%d)\n") % options.Quality)
            return None

        preset = None
        upper_target = options.Target.upper ()
        if presets.List.has_key (upper_target):
            preset = presets.List [upper_target]

        if not preset:
            for x in presets.List:
                if presets.List [x]["Device"].upper ().find (upper_target) >= 0:
                    preset = presets.List [x]
                    break

        if not preset:
            pr (_("ERROR: unknown target profile `%s'\n") % options.Target)
            return None

        pr (_("Using target profile `%s'\n") % preset ["Device"])

        if not options.Width:
            options.Width = preset ["VideoWidth"]
        if not options.Height:
            options.Height = preset ["VideoHeight"]
        if not options.MaxWidth:
            if preset.has_key ("MaxWidth"):
                options.MaxWidth = preset ["MaxWidth"]
            else:
                options.MaxWidth = preset ["VideoWidth"]
        if not options.MaxHeight:
            if preset.has_key ("MaxHeight"):
                options.MaxHeight = preset ["MaxHeight"]
            else:
                options.MaxHeight = preset ["VideoHeight"]

        if options.OutFile == None:
            options.OutFile = "%(dir)s/%(name)s-tiny.%(ext)s"

        fn = os.path.realpath (fn.encode (FNENC)).decode (FNENC)
        dn = os.path.dirname (fn)
        bn = os.path.splitext (os.path.basename (fn)) [0]
        ex = preset.get ("Extension", "avi")
        try:
            self.outfile = options.OutFile % {"dir": dn, "name": bn, "ext": ex}
        except:
            pr (_("Invalid output file mask:\n%s") % options.OutFile)
            return None

        if not options.Play:
            pr (_("Resulting video file: %s\n") % self.outfile)

        vp = self.FindVideoLengthCrop (fn)
        if vp == None:
            return None

        if (vp.vw == 0) or (vp.vh == 0) or (vp.cw > vp.vw) or (vp.ch > vp.vh):
            pr (_("ERROR: failed to determine video/crop width and/or height\n"))
            return None

        # Limit max width/height to cropped width/height
        if options.MaxWidth > 0 and options.MaxHeight > 0:
            tmp = int ((vp.cw + 4) / 8) * 8
            if options.MaxWidth > tmp:
                options.MaxWidth = tmp
            tmp = int ((vp.ch + 4) / 8) * 8
            if options.MaxHeight > tmp:
                options.MaxHeight = tmp

        # Compute the aspect ratio of the cropped area
        #srca = vp.aspect * ((float (vp.cw) / vp.ch) / (float (vp.vw) / vp.vh))
        srca = vp.aspect * ((float (vp.cw) * vp.vh) / (vp.ch * vp.vw))

        # Find out rescaled size of the video
        if srca > 1.0:
            vp.sw = float (vp.cw)
            vp.sh = vp.sw / srca
        else:
            vp.sh = float (vp.ch)
            vp.sw = vp.sh * srca

        # Limit rescaled size to target size
        if vp.sw > options.Width:
            vp.sh = float (options.Width * vp.sh) / vp.sw
            vp.sw = float (options.Width)
        if vp.sh > options.Height:
            vp.sw = float (options.Height * vp.sw) / vp.sh
            vp.sh = float (options.Height)

        if options.MaxWidth > 0 and options.MaxHeight > 0:
            # For wide-format video, scale it a bit so that it leaves less
            # unused space on target device screen. This makes image a bit
            # unproportional, but instead adds to the visible details
            srca = vp.sw / vp.sh
            dsta = float (options.Width) / options.Height
            aratio = (srca / dsta) - 1
            srca = (1 + (aratio / 2.0)) * dsta
            if vp.sw == float (options.Width):
                # Horizontally limited video
                vp.sh = vp.sw / srca
            elif vp.sh == float (options.Height):
                # Vertically limited video
                vp.sw = vp.sh * srca

            # See if we have bandwidth reserve, which is the case
            # if our video does not fully cover the target size.
            ratio = math.sqrt ((options.Width * options.Height) / (vp.sw * vp.sh))
            if ratio > 1:
                ratio_w = options.MaxWidth / vp.sw
                ratio_h = options.MaxHeight / vp.sh
                if ratio > ratio_w:
                    ratio = ratio_w
                if ratio > ratio_h:
                    ratio = ratio_h
                vp.sw *= ratio
                vp.sh *= ratio

        # Allow only sizes multiple of 8 (macroblock size).
        vp.sw = int ((vp.sw + 4) / 8) * 8
        vp.sh = int ((vp.sh + 4) / 8) * 8

        # Last dirty check (should never happen, but who knows)
        if options.MaxWidth > 0 and options.MaxHeight > 0:
            if vp.sw > options.MaxWidth:
                vp.sw = options.MaxWidth
            if vp.sh > options.MaxHeight:
                vp.sh = options.MaxHeight

        # Prepare the command line parameters
        if options.PassAudio:
            preset ["AudioCodec"] = "pass"
        vc = presets.vc [preset ["VideoCodec"]]
        ac = presets.ac [preset ["AudioCodec"]]

        vf = ""
        af = ""

        if options.vf:
            vf = AddFilter (vf, _("video"), options.vf)
        if options.Deint:
            vf = AddFilter (vf, _("video"), "yadif")
        need_filter = preset.get ("VideoPostproc", True)
        if need_filter:
            vf = AddFilter (vf, _("video"), "pp=ha/va/dr")
        if vp.cx != 0 or vp.cy != 0 or vp.cw != vp.vw or vp.ch != vp.vh:
            vf = AddFilter (vf, _("video"), "crop=%d:%d:%d:%d" %(vp.cw, vp.ch, vp.cx, vp.cy))
        if options.Denoise:
            vf = AddFilter (vf, _("video"), "hqdn3d=2:1:4")
        if vp.sw != vp.cw or vp.sh != vp.ch:
            vf = AddFilter (vf, _("video"), "scale=%d:%d" % (vp.sw, vp.sh))
        if options.Sharpen:
            vf = AddFilter (vf, _("video"), "unsharp=l:3x3:1")

        if options.af:
            af = AddFilter (af, _("audio"), options.af)
        if options.NormVolume:
            af = AddFilter (af, _("audio"), "volnorm=2")

        if preset.has_key ("VideoFilter"):
            for x in preset ["VideoFilter"]:
                vf = AddFilter (vf, _("video"), x)
        if preset.has_key ("AudioFilter"):
            for x in preset ["AudioFilter"]:
                af = AddFilter (af, _("audio"), x)

        vopt = "-noconfig all -vf-clr"
        aopt = ""
        if options.AudioID != None:
            aopt = aopt + " -aid %d" % options.AudioID

        if options.Play:
            # For playing we need just audio & video filters
            opts = vopt + " " + aopt
            if vf != "":
                opts += " -vf " + vf
            if af != "":
                opts += " -af " + af
            s = OSW.GenScriptPlay ({ 'opts' : opts, 'input' : OSW.Quote (fn)})
        else:
            vparm = {}
            aparm = {}

            if vc.has_key ("Quality"):
                vparm.update (vc ["Quality"] [options.Quality] (vp.sw, vp.sh, vp.fps))
            if ac.has_key ("Quality"):
                aparm.update (ac ["Quality"] [options.Quality] ())

            if preset.has_key ("VideoOptions"):
                vparm.update (preset ["VideoOptions"])
            if preset.has_key ("AudioOptions"):
                aparm.update (preset ["AudioOptions"])

            pass1opts = vopt + " " + Subst (vc ["Options"] [0], vparm)
            pass2opts = vopt + " " + Subst (vc ["Options"] [1], vparm)
            if vf != "":
                pass1opts += " -vf " + vf
                pass2opts += " -vf " + vf
            if af != "":
                pass1opts += " -af " + af
                pass2opts += " -af " + af

            pass1opts += " " + aopt + " " + Subst (ac ["Options"] [0], aparm)
            pass2opts += " " + aopt + " " + Subst (ac ["Options"] [1], aparm)

            aspect = float (vp.sw) / vp.sh

            s = OSW.GenScriptEncode ({'pass1opts' : pass1opts, 'pass2opts' : pass2opts,
                'aspect' : aspect, 'input': OSW.Quote (fn), 'output': OSW.Quote (self.outfile)})

        pr (_("Analysing finished\n"))
        return s
