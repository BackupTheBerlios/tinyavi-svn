#
# Graphical User Interface for TinyAVI
#

import os
import sys
import locale
import fcntl
import time
import tempfile
import subprocess
import pickle
import re
import pygtk
import gtk
import gtk.glade
import gobject
from tinyavi import VERSION,FNENC

# This is the GUI application class itself
class TinyAviGui:
    def __init__ (self, _gettext):
        global _
        _ = _gettext

        # Figure out our installation paths
        self.DATADIR = os.path.join (os.path.dirname (os.path.abspath (
            sys.argv [0])), "share")
        if not os.path.exists (self.DATADIR):
            self.DATADIR = os.path.join (os.path.normpath (sys.prefix), "share/tinyavi")
            if not os.path.exists (self.DATADIR):
                self.DATADIR = os.path.join (os.path.normpath (os.path.join (
                    os.path.dirname (os.path.abspath (sys.argv [0])), "..")), "share/tinyavi")

        if not os.path.exists (self.DATADIR):
            raise SystemExit, _("FATAL: Could not find data directory")

        self.BINDIR = os.path.dirname (os.path.abspath (sys.argv [0]))

        self.configfile = gobject.filename_from_utf8 (os.path.expanduser("~/.config"))
        if not os.access (self.configfile, os.F_OK):
            os.makedirs (self.configfile, 0700)
        self.configfile = os.path.join (self.configfile, "tinyavi-gui.conf")

        try:
            self.glade = gtk.glade.XML(self.DATADIR + "/gui.glade")
        except RuntimeError, msg:
            raise SystemExit, msg
        self.MainWindow = self.glade.get_widget ("MainWindow")
        self.VideoList = self.glade.get_widget ("VideoList")
        self.SpinCPUs = self.glade.get_widget ("SpinCPUs")
        self.Log = self.glade.get_widget ("Log")
        self.SpinVideoWidth = self.glade.get_widget ("SpinVideoWidth")
        self.SpinVideoHeight = self.glade.get_widget ("SpinVideoHeight")
        self.EntryOutputFileMask = self.glade.get_widget ("EntryOutputFileMask")
        self.SpinCPUs = self.glade.get_widget ("SpinCPUs")
        self.CheckDeinterlace = self.glade.get_widget ("CheckDeinterlace")
        self.CheckDenoise = self.glade.get_widget ("CheckDenoise")
        self.CheckAudioPassthrough = self.glade.get_widget ("CheckAudioPassthrough")

        self.Queue = {}
        self.Logs = {}
        self.CurrentLog = ""

        self._Stopped = _("Stopped")
        self._Queued = _("Queued")
        self._Playing = _("Playing")
        self._Done = _("Done")
        self._Error = _("Error")
        self._Aborted = _("Aborted")

        self.ProgressRE = re.compile (".*\(\s*([0-9]*)%\).*")
        self.StageRE = re.compile ("-=\s*STAGE\s*([0-9]*)")

        self.glade.signal_autoconnect ({
            "on_MainWindow_destroy" : self.on_MainWindow_destroy,
            "on_VideoList_cursor_changed" : self.on_VideoList_cursor_changed,
            "on_ButtonPlay_clicked" : self.on_ButtonPlay_clicked,
            "on_ButtonConvert_clicked" : self.on_ButtonConvert_clicked,
            "on_ButtonStop_clicked" : self.on_ButtonStop_clicked,
            "on_ButtonAdd_clicked" : self.on_ButtonAdd_clicked,
            "on_ButtonConvertAll_clicked" : self.on_ButtonConvertAll_clicked,
            "on_ButtonStopAll_clicked" : self.on_ButtonStopAll_clicked,
            "on_ButtonAbout_clicked" : self.on_ButtonAbout_clicked,
            "on_ComboVideoSize_changed" : self.on_ComboVideoSize_changed
        })

        # Initialize the list view
        self.ListStore = gtk.ListStore (str, str, str, float)

        for x in range(1, len (sys.argv)):
            self.AddFile (sys.argv [x].decode (FNENC))

        self.VideoList.set_model (self.ListStore)
        self.VideoList.get_selection ().set_mode (gtk.SELECTION_MULTIPLE)

        column = gtk.TreeViewColumn (_("Video file name"), gtk.CellRendererText (), text = 1)
        column.set_sizing (gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_resizable (True)
        column.set_min_width (300)
        self.VideoList.append_column (column)

        column = gtk.TreeViewColumn (_("Status"), gtk.CellRendererProgress (), text = 0, value = 3)
        column.set_sizing (gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_resizable (True)
        column.set_min_width (150)
        self.VideoList.append_column (column)

        # Initialize file open dialog filters
        afd = self.glade.get_widget ("AddFileDialog")

        filt = gtk.FileFilter ()
        filt.set_name (_("Video files"))
        filt.add_mime_type ("video/*")
        afd.add_filter (filt)

        filt = gtk.FileFilter ()
        filt.set_name (_("All files"))
        filt.add_pattern ("*")
        afd.add_filter (filt)

        try:
            cf = open (self.configfile, "r")
            cfg = pickle.load (cf)
            cf.close ()
            self.SpinVideoWidth.set_value (cfg ["VideoWidth"])
            self.SpinVideoHeight.set_value (cfg ["VideoHeight"])
            self.EntryOutputFileMask.set_text (cfg ["OutFileMask"])
            self.SpinCPUs.set_value (cfg ["NumCPUs"])
            self.CheckDeinterlace.set_active (cfg ["Deinterlace"])
            self.CheckDenoise.set_active (cfg ["Denoise"])
            self.CheckAudioPassthrough.set_active (cfg ["AudioPass"])
        except:
            # no config file yet
            pass

        self.MainWindow.show_all ()

        gobject.timeout_add (500, self.TimerTick)

        self.LogWrite ("", _("TinyAVI GUI started ...\nNow add some files to the queue and press `Convert All'\n"))

    def on_MainWindow_destroy (self, win):
        self.on_ButtonStopAll_clicked (win)
        # Save config file
        try:
            cfg = self.GetConfig ()
            cf = open (self.configfile, "w")
            pickle.dump (cfg, cf)
            cf.close ()
        except:
            # Oh well...
            pass

        gtk.main_quit ()

    def on_ButtonPlay_clicked (self, but):
        for idx in self.GetSelected ():
            self.ListStore [idx][0] = self._Playing

    def on_ButtonConvert_clicked (self, but):
        for idx in self.GetSelected ():
            self.QueueFile (self.ListStore [idx])

    def on_ButtonStop_clicked (self, but):
        for idx in self.GetSelected ():
            self.ConvertStop (self.ListStore [idx], self._Aborted)

    def on_ButtonAdd_clicked (self, but):
        afd = self.glade.get_widget ("AddFileDialog")

        if afd.run () == gtk.RESPONSE_ACCEPT:
            for fn in afd.get_filenames ():
                self.AddFile (fn.decode (FNENC))

        afd.unselect_all ()
        afd.hide ()

    def on_ButtonConvertAll_clicked (self, but):
        for fi in self.ListStore:
            if not fi [2] in self.Queue:
                self.QueueFile (fi)

    def on_ButtonStopAll_clicked (self, but):
        for fi in self.ListStore:
            if fi [2] in self.Queue or fi [0] == self._Queued:
                self.ConvertStop (fi, self._Aborted)

    def on_ComboVideoSize_changed (self, cb):
        sz = cb.get_active_text().split ('x')
        self.SpinVideoWidth.set_value (float (sz [0]))
        self.SpinVideoHeight.set_value (float (sz [1]))

    def on_VideoList_cursor_changed (self, tv):
        c = tv.get_cursor () [0][0]
        s = self.GetSelected ()
        if c in s:
            self.LogSwitch (self.ListStore [c][2])

    def on_ButtonAbout_clicked (self, but):
        abd = self.glade.get_widget ("AboutDialog")
        abd.set_version (VERSION)
        abd.run ()
        abd.hide ()

    def FindFile(self, fn):
        for i in range (0, len (self.ListStore)):
            if self.ListStore [i][2] == fn:
                return i
        return -1

    def AddFile (self, fn):
        idx = self.FindFile (fn)
        val = (self._Stopped, os.path.basename(fn), fn, 0.0)
        if idx >= 0:
            self.ConvertStop (self.ListStore [idx])
            self.ListStore [idx] = val
        else:
            self.ListStore.append (val)

    def QueueFile (self, fi):
        if fi [3] < 100:
            fi [0] = self._Queued
            fi [3] = 0.0

    def GetSelected (self):
        sel = self.VideoList.get_selection ().get_selected_rows() [1]
        return [x [0] for x in sel]

    def LogWrite (self, log, s):
        if self.Logs.has_key (log):
            self.Logs [log] = self.Logs [log] + s
        else:
            self.Logs [log] = s

        if log == self.CurrentLog:
            b = self.Log.get_buffer ()
            b.insert (b.get_end_iter (), s)
            b.place_cursor (b.get_end_iter ())
            self.Log.scroll_mark_onscreen (b.get_mark ("insert"))

    def LogSwitch (self, log):
        if not self.Logs.has_key (log):
            self.Logs [log] = ""

        self.CurrentLog = log
        b = self.Log.get_buffer ()
        b.set_text (self.Logs [log])
        b.place_cursor (b.get_end_iter ())
        self.Log.scroll_mark_onscreen (b.get_mark ("insert"))

    # Read config from settings controls
    def GetConfig (self):
        cfg = {}
        cfg ["VideoWidth"] = int (self.SpinVideoWidth.get_value ())
        cfg ["VideoHeight"] = int (self.SpinVideoHeight.get_value ())
        cfg ["OutFileMask"] = self.EntryOutputFileMask.get_text ().strip ()
        cfg ["NumCPUs"] = int (self.SpinCPUs.get_value ())
        cfg ["Deinterlace"] = self.CheckDeinterlace.get_active ()
        cfg ["Denoise"] = self.CheckDenoise.get_active ()
        cfg ["AudioPass"] = self.CheckAudioPassthrough.get_active ()
        return cfg

    # Return the command line used to launch tinyavi
    def BuildCmdline (self, fn):
        cfg = self.GetConfig ()
        cmdl = [ os.path.join (self.BINDIR, "tavi"),
            "-W" + str (int (cfg ["VideoWidth"])), "-H" + str (int (cfg ["VideoHeight"])) ]
        if cfg ["Deinterlace"]:
            cmdl.append ("-D")
        if cfg ["Denoise"]:
            cmdl.append ("-d")
        if cfg ["AudioPass"]:
            cmdl.append ("-p")

        fn = os.path.realpath (fn)
        cmdl.append (fn.encode (FNENC))

        dn = os.path.dirname (fn)
        bn = os.path.basename (fn).rsplit ('.', 1)
        if len (bn) > 1:
            ex = bn [1]
        else:
            ex = ""
        bn = bn [0]
        try:
            ofn = cfg ["OutFileMask"] % {"dir": dn, "name": bn, "ext": ex}
            cmdl.append ("-o" + ofn.encode (FNENC))
        except:
            d = gtk.MessageDialog (self.MainWindow, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
                gtk.BUTTONS_OK, _("Invalid output file mask:\n%s") % cfg ["OutFileMask"])
            d.run ()
            d.destroy ()
            return None

        return cmdl

    # This is the worker function, called at regular intervals
    # It manages the conversion queue
    def TimerTick (self):
        in_queue = 0
        for i in range (0, len (self.ListStore)):
            fi = self.ListStore [i]
            if fi [2] in self.Queue:
                if self.Progress (fi):
                    in_queue = in_queue + 1

        i = 0
        num_cpus = self.SpinCPUs.get_value ()
        while i < len (self.ListStore) and in_queue < num_cpus:
            fi = self.ListStore [i]
            if not fi [2] in self.Queue:
                if fi [0] == self._Queued:
                    if self.ConvertStart (fi) and self.Progress (fi):
                        in_queue = in_queue + 1
                elif fi [0] == self._Playing:
                    if self.PlayStart (fi) and self.Progress (fi):
                        in_queue = in_queue + 1
            i = i + 1

        return True

    def RemoveDir (self, d):
        for root, dirs, files in os.walk (d, topdown=False):
            for name in files:
                os.remove (os.path.join (root, name))
            for name in dirs:
                os.rmdir (os.path.join (root, name))
        os.rmdir (d)

    def PlayStart (self, fi):
        try:
            cmdl = self.BuildCmdline (fi [2])
            if not cmdl:
                self.ConvertStop (fi, self._Error)
                return False

            cmdl.append ("-P")
            p = subprocess.Popen(cmdl, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            fcntl.fcntl (p.stdout, fcntl.F_SETFL, os.O_NDELAY)
            fcntl.fcntl (p.stderr, fcntl.F_SETFL, os.O_NDELAY)
            self.Queue [fi [2]] = [p, "", None, 1]
        except:
            self.ConvertStop (fi, self._Error)
            return False
        return True

    def ConvertStart (self, fi):
        # Don't convert files which are already converted
        if fi [3] >= 100:
            return False

        try:
            cmdl = self.BuildCmdline (fi [2])
            if not cmdl:
                self.ConvertStop (fi, self._Error)
                return False

            tmpdir = tempfile.mkdtemp ()
            p = subprocess.Popen(cmdl, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                cwd=tmpdir)
            fcntl.fcntl (p.stdout, fcntl.F_SETFL, os.O_NDELAY)
            fcntl.fcntl (p.stderr, fcntl.F_SETFL, os.O_NDELAY)
            self.Queue [fi [2]] = [p, "", tmpdir, 1]
        except:
            self.ConvertStop (fi, self._Error)
            return False
        return True

    def ConvertStop (self, fi, status = None):
        if self.Queue.has_key (fi [2]):
            q = self.Queue [fi [2]]
            q [0].stdout.close ()
            q [0].stderr.close ()
            del self.Queue [fi [2]]
            if q [2]:
                self.RemoveDir (q [2])
            else:
                # Stop playing, restore old status
                if fi [3] < 100:
                    fi [0] = self._Stopped
                else:
                    fi [0] = self._Done
                return True

        if status:
            fi [0] = status
        else:
            fi [0] = self._Stopped
        fi [3] = 0.0
        return True

    def Progress (self, fi):
        q = self.Queue [fi [2]]

        try:
            txt = q [0].stderr.read (10*1024)
        except:
            txt = ""
        for l in txt.splitlines (True):
            self.LogWrite (fi [2], l.decode (locale.getpreferredencoding ()))

        try:
            txt = q [1] + q [0].stdout.read (10*1024)
        except:
            txt = q [1]
        if txt == "":
            if q [0].poll () != None:
                status = self._Done
                if q [0].returncode != 0:
                    status = self._Error
                self.ConvertStop (fi, status)
                if q [0].returncode == 0 and q [2]:
                    fi [3] = 100.0
                return False
        else:
            eol = ("\n\r".find (txt [-1]) >= 0)
            txt = txt.splitlines (True)
            if eol:
                q [1] = ""
            else:
                q [1] = txt [-1]
                del txt [-1]

            for l in txt:
                r = self.ProgressRE.match (l)
                if r:
                    fi [3] = (float (r.group (1)) / 2) + (q [3] - 1) * 50
                    fi [0] = "%d%%" %int (fi [3])
                else:
                    r = self.StageRE.match (l)
                    if r:
                        q [3] = int (r.group (1))

        return True
