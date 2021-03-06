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
import ConfigParser
import re
import pygtk
import gtk
import gtk.glade
import gobject
import urllib
from tinyavi import VERSION,FNENC,presets

#-----------------------------------------------------------------------------
#                          The GUI application class
#-----------------------------------------------------------------------------
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

        # Load the widgets from the Glade file
        try:
            self.glade = gtk.glade.XML(self.DATADIR + "/gui.glade")
        except RuntimeError, msg:
            raise SystemExit, msg

        # Cache most used widgets into variables
        for widget in "MainWindow", "VideoList", "PresetList", "SpinCPUs", "Log", \
                      "SpinVideoWidth", "SpinVideoHeight", "EntryOutputFileMask", \
                      "EntryOutDirHBox", "EntryOutDir", "ButtonOutDirSelect", \
                      "SpinCPUs", "CheckDeinterlace", "CheckDenoise", \
                      "CheckSharpen", "CheckAudioPassthrough", "CheckAudioNormalize", \
                      "EncodeQuality", "ComboVideoSize", "AdvancedSettingsVBox",  \
                      "VideoFiltersEntry", "AudioFiltersEntry", "EntryOutputHBox", \
                      "VideoFiltersHBox", "AudioFiltersHBox":
            setattr (self, widget, self.glade.get_widget (widget))

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

        self.EncodeQuality.set_active (1)

        self.glade.signal_autoconnect ({
            "on_MainWindow_destroy" : self.on_MainWindow_destroy,
            "on_VideoList_cursor_changed" : self.on_VideoList_cursor_changed,
            "on_ButtonPlay_clicked" : self.on_ButtonPlay_clicked,
            "on_ButtonConvert_clicked" : self.on_ButtonConvert_clicked,
            "on_ButtonStop_clicked" : self.on_ButtonStop_clicked,
            "on_ButtonAdd_clicked" : self.on_ButtonAdd_clicked,
            "on_ButtonRemove_clicked" : self.on_ButtonRemove_clicked,
            "on_ButtonAbout_clicked" : self.on_ButtonAbout_clicked,
            "on_ComboVideoSize_changed" : self.on_ComboVideoSize_changed,
            "on_SpinVideoSize_changed" : self.on_SpinVideoSize_changed,
            "on_PresetList_changed" : self.on_PresetList_changed,
            "on_ButtonOutDirSelect_clicked" : self.on_ButtonOutDirSelect_clicked,
            "on_VideoList_drag_data_received" : self.on_VideoList_drag_data_received,
            "on_VideoList_button_press_event" : self.on_VideoList_button_press_event
        })

        # Initialize the list view
        self.InitListView ()

        # Load the list of presets
        self.InitPresetList ()

        # Set default number of CPUs
        self.SpinCPUs.set_value (self.NumCPUs ())

        # Load config file
        self.cfg = TinyAviConfig (self.configfile)
        self.cfg.SetupControls (self)

        self.MainWindow.show_all ()

        if not self.cfg.Advanced:
            self.AdvancedSettingsVBox.hide ()
            self.VideoFiltersHBox.hide ()
            self.AudioFiltersHBox.hide ()
            self.EntryOutputHBox.hide ()
        else:
            self.EntryOutDirHBox.hide ()

        # Initialize file open dialog filters
        afd = self.glade.get_widget ("AddFileDialog")
        afd.add_filter (self.MakeFilter (_("Video files"), "video/*", "application/x-flash-video", "application/vnd.rn-realmedia"))
        afd.add_filter (self.MakeFilter (_("All files"), "@*"))

        # Start the worker 'thread'
        gobject.timeout_add (500, self.TimerTick)

        self.LogWrite ("", _("TinyAVI GUI started ...\nNow add some files to the queue and press `Convert All'\n"))


    def ErrorMsg (self, msg):
        d = gtk.MessageDialog (self.MainWindow, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
            gtk.BUTTONS_OK, msg)
        d.run ()
        d.destroy ()


    def MakeFilter (self, name, *tpe):
        filt = gtk.FileFilter ()
        filt.set_name (name)
        for x in tpe:
            if x [0] == "@":
                filt.add_pattern (x [1:])
            else:
                filt.add_mime_type (x)
        return filt


    def InitListView (self):
        self.ListStore = gtk.ListStore (str, str, str, float)

        for x in range(1, len (sys.argv)):
            self.AddFile (self.Uri2Filename (sys.argv [x]).decode (FNENC))

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

        self.VideoList.enable_model_drag_dest(
            [('text/uri-list', 0, 0)],
             gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY)


    def InitPresetList (self):
        self.PresetListStore = gtk.ListStore (str)
        cell = gtk.CellRendererText ()
        self.PresetList.pack_start (cell, True)
        self.PresetList.add_attribute (cell, 'text', 0)

        k = presets.List.keys ()
        k.sort ()
        for x in k:
            y = presets.List [x].get ("Comment")
            if y:
                y = " (" + y + ")"
            else:
                y = ""
            self.PresetListStore.append ([presets.List [x]["Device"] + y])

        self.PresetList.set_model (self.PresetListStore)
        self.PresetList.set_active (0)


    # ------------------------- # Event handlers # ------------------------- #


    def on_MainWindow_destroy (self, win):
        for fi in self.ListStore:
            if fi [2] in self.Queue or fi [0] == self._Queued:
                self.ConvertStop (fi, self._Aborted)
        # Read the values of the controls
        self.cfg.ReadControls (self)
        # Save config file
        if not self.cfg.Save (self.configfile):
            self.ErrorMsg (_("Failed to save configuration file:\n%s") % self.configfile)

        gtk.main_quit ()


    def on_ButtonPlay_clicked (self, but):
        for idx in self.GetSelectedFiles ():
            self.ListStore [idx][0] = self._Playing


    def on_ButtonConvert_clicked (self, but):
        for idx in self.GetSelectedFiles ():
            self.QueueFile (self.ListStore [idx])


    def on_ButtonStop_clicked (self, but):
        for idx in self.GetSelectedFiles ():
            self.ConvertStop (self.ListStore [idx], self._Aborted)


    def on_ButtonAdd_clicked (self, but):
        afd = self.glade.get_widget ("AddFileDialog")

        if afd.run () == gtk.RESPONSE_ACCEPT:
            for fn in afd.get_filenames ():
                self.AddFile (fn.decode (FNENC))

        afd.unselect_all ()
        afd.hide ()


    def on_ButtonRemove_clicked (self, but):
        self.on_ButtonStop_clicked (but)
        r = self.ListStore.get_iter_first ()
        c = 0
        for idx in self.GetSelectedFiles ():
            while c < idx:
                c += 1
                r = self.ListStore.iter_next (r)

            fn = self.ListStore.get_value (r, 2)
            if self.Logs.has_key (fn):
                del self.Logs [fn]

            self.ListStore.remove (r)
            c += 1


    def on_ComboVideoSize_changed (self, cb):
        txt = cb.get_active_text()
        if txt:
            sz = txt.split ('x')
            self.SpinVideoWidth.set_value (float (sz [0]))
            self.SpinVideoHeight.set_value (float (sz [1]))


    def on_SpinVideoSize_changed (self, sb):
        sz = str (long (self.SpinVideoWidth.get_value ())) + "x" + \
             str (long (self.SpinVideoHeight.get_value ()))
        self.SelectItem (self.ComboVideoSize, sz)
        if self.SelectedItem (self.ComboVideoSize) != sz:
            self.ComboVideoSize.set_active (-1)


    def on_VideoList_cursor_changed (self, tv):
        c = tv.get_cursor () [0][0]
        s = self.GetSelectedFiles ()
        if c in s:
            self.LogSwitch (self.ListStore [c][2])


    def on_VideoList_drag_data_received (self, tv, context, x, y, selection, info, etime):
        for x in selection.data.split ():
            self.AddFile (self.Uri2Filename (x).decode (FNENC))


    def on_VideoList_button_press_event (self, tv, event):
        if (event.type != gtk.gdk.BUTTON_PRESS) or (event.button != 3):
            return False

        model = tv.get_model ()
        if model.get_iter_first ():
            if len (tv.get_selection ().get_selected_rows () [1]) == 0:
                tv.get_selection ().select_all ()
            else:
                tv.get_selection ().unselect_all ()

        return True


    def on_ButtonAbout_clicked (self, but):
        abd = self.glade.get_widget ("AboutDialog")
        abd.set_version (VERSION)
        abd.run ()
        abd.hide ()


    def on_PresetList_changed (self, list):
        targ = self.GetTarget (self.SelectedItem (list))

        preset = presets.List.get (targ)
        if not preset:
            # should never happen
            return

        self.SpinVideoWidth.set_value (preset ["VideoWidth"])
        self.SpinVideoHeight.set_value (preset ["VideoHeight"])


    def on_ButtonOutDirSelect_clicked (self, but):
        dsd = self.glade.get_widget ("DirSelDialog")

        if dsd.run () == gtk.RESPONSE_ACCEPT:
            for fn in dsd.get_filenames ():
                self.cfg.OutDir = fn.decode (FNENC)

        dsd.unselect_all ()
        dsd.hide ()
        self.UpdateFileMask ()
        self.EntryOutDir.set_text (self.cfg.OutDir)


    # -------------------- # Application log handling # -------------------- #


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


    # ---------------------- # Timer ticker function # ---------------------- #


    def FindFile(self, fn):
        for i in range (0, len (self.ListStore)):
            if self.ListStore [i][2] == fn:
                return i
        return -1


    def AddFile (self, fn):
        if not os.path.isfile (fn):
            return

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


    # Return the command line used to launch tinyavi
    def BuildCmdline (self, fn):
        self.cfg.ReadControls (self)
        cmdl = [ os.path.join (self.BINDIR, "tavi"),
            "-W" + str (self.cfg.Width), "-H" + str (self.cfg.Height),
            "-t" + self.GetTarget (self.SelectedItem (self.PresetList)) ]
        if self.cfg.Deinterlace:
            cmdl.append ("-D")
        if self.cfg.Denoise:
            cmdl.append ("-d")
        if self.cfg.AudioPass:
            cmdl.append ("-p")
        if self.cfg.Normalize:
            cmdl.append ("-n")
        if self.cfg.Sharpen:
            cmdl.append ("-S")
        if self.cfg.VFilters:
            cmdl.append ("-V" + self.cfg.VFilters)
        if self.cfg.AFilters:
            cmdl.append ("-A" + self.cfg.AFilters)

        fn = os.path.realpath (fn)
        cmdl.append (fn.encode (FNENC))
        cmdl.append ("-o" + self.cfg.OutFileMask.encode (FNENC))

        return cmdl


    # This is the worker function, called at regular intervals
    # It manages the conversion queue
    def TimerTick (self):
        in_queue = 0
        for i in range (0, len (self.ListStore)):
            fi = self.ListStore [i]
            if fi [2] in self.Queue:
                if self.Progress (fi):
                    in_queue += 1

        i = 0
        num_cpus = self.SpinCPUs.get_value ()
        while i < len (self.ListStore) and in_queue < num_cpus:
            fi = self.ListStore [i]
            if not fi [2] in self.Queue:
                if fi [0] == self._Queued:
                    if self.ConvertStart (fi) and self.Progress (fi):
                        in_queue += 1
                elif fi [0] == self._Playing:
                    if self.PlayStart (fi) and self.Progress (fi):
                        in_queue += 1
            i += 1

        return True


    def PlayStart (self, fi):
        try:
            cmdl = self.BuildCmdline (fi [2])
            if not cmdl:
                self.ConvertStop (fi, self._Error)
                return False

            cmdl.append ("-P")
            p = subprocess.Popen (cmdl, close_fds=True, stdin=subprocess.PIPE, \
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
            p = subprocess.Popen(cmdl, close_fds=True, stdin=subprocess.PIPE, \
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=tmpdir)
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
            q [0].stdin.close ()
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


    # ------------------------ # Utility methods # ------------------------- #


    def RemoveDir (self, d):
        for root, dirs, files in os.walk (d, topdown=False):
            for name in files:
                os.remove (os.path.join (root, name))
            for name in dirs:
                os.rmdir (os.path.join (root, name))
        os.rmdir (d)


    def SelectItem (self, widget, text):
        def check (model, path, iter, data):
            if model.get_value (iter, 0) == data:
                widget.set_active_iter (iter)
                return True
            return False

        widget.get_model ().foreach (check, text)


    def SelectedItem (self, widget):
        iter = widget.get_active_iter ()
        if not iter:
            return ""
        return widget.get_model ().get_value (iter, 0)


    def GetSelectedFiles (self):
        sel = self.VideoList.get_selection ().get_selected_rows() [1]
        if len (sel) == 0:
            self.VideoList.get_selection ().select_all ()
            sel = self.VideoList.get_selection ().get_selected_rows() [1]
        return [x [0] for x in sel]


    def Uri2Filename (self, uri):
        path = urllib.url2pathname (uri) # escape special chars
        path = path.strip('\r\n\x00') # remove \r\n and NULL

        # get the path to file
        if path.startswith('file:\\\\\\'): # windows
            path = path[8:] # 8 is len('file:///')
        elif path.startswith('file://'): # nautilus, rox
            path = path[7:] # 7 is len('file://')
        elif path.startswith('file:'): # xffm
            path = path[5:] # 5 is len('file:')
        return path


    def NumCPUs (self):
        """Source: http://www.artima.com/weblogs/viewpost.jsp?thread=230001"""
        # Linux, Unix and MacOS:
        if hasattr (os, "sysconf"):
            if os.sysconf_names.has_key ("SC_NPROCESSORS_ONLN"):
                # Linux & Unix:
                ncpus = os.sysconf("SC_NPROCESSORS_ONLN")
                if isinstance(ncpus, int) and ncpus > 0:
                    return ncpus
                else: # OSX:
                    return int(os.popen2("sysctl -n hw.ncpu")[1].read())
        # Windows:
        if os.environ.has_key("NUMBER_OF_PROCESSORS"):
            ncpus = int(os.environ["NUMBER_OF_PROCESSORS"]);
            if ncpus > 0:
                return ncpus
        return 1 # Default

    def UpdateFileMask(self):
        # In Simple UI mode transform outdir to outfilemask
        if not self.cfg.Advanced:
            if self.cfg.OutDir == "":
                self.cfg.OutFileMask = "%(dir)s/%(name)s-tiny.%(ext)s"
            else:
                self.cfg.OutFileMask = self.cfg.OutDir + "/%(name)s.%(ext)s"


    def GetTarget (self, dev):
        try:
            x = dev.index ('(')
            comm = dev [x + 1:-1]
            dev = dev [:x - 1]
        except:
            comm = None

        for x in presets.List:
            if (presets.List [x].get ("Device") == dev) and \
               (presets.List [x].get ("Comment") == comm):
                return x

        return None


#-----------------------------------------------------------------------------
#                          The program config storage
#-----------------------------------------------------------------------------
class TinyAviConfig:
    # Attribute name, type, GUI widget, config file section
    # Take care of the proper sequence, the controls will be filled
    # exactly in the sequence they are listed here.
    attrs = [
        ['OutFileMask', 's', 'EntryOutputFileMask',   'TinyAVI'],
        ['OutDir',      's', 'EntryOutDir',           'TinyAVI'],
        ['NumCPUs',     'i', 'SpinCPUs',              'TinyAVI'],
        ['Preset',      'l', 'PresetList',            'TinyAVI'],
        ['Quality',     'l', 'EncodeQuality',         'TinyAVI'],
        ['Advanced',    'F', None,                    'TinyAVI'],
        ['Width',       'i', 'SpinVideoWidth',        'Video'  ],
        ['Height',      'i', 'SpinVideoHeight',       'Video'  ],
        ['Deinterlace', 'b', 'CheckDeinterlace',      'Video'  ],
        ['Denoise',     'b', 'CheckDenoise',          'Video'  ],
        ['Sharpen',     'b', 'CheckSharpen',          'Video'  ],
        ['VFilters',    's', 'VideoFiltersEntry',     'Video'  ],
        ['AudioPass',   'b', 'CheckAudioPassthrough', 'Audio'  ],
        ['Normalize',   'b', 'CheckAudioNormalize',   'Audio'  ],
        ['AFilters',    's', 'AudioFiltersEntry',     'Audio'  ]
    ]


    upgrade_attrs = [
        ['VideoWidth',  'Encoder', 'Width',       'Video'],
        ['VideoHeight', 'Encoder', 'Height',      'Video'],
        ['Deinterlace', 'Encoder', 'Deinterlace', 'Video'],
        ['Denoise',     'Encoder', 'Denoise',     'Video'],
        ['AudioPass',   'Encoder', 'AudioPass',   'Audio'],
        ['Quality',     'Encoder', 'Quality',     'TinyAVI']
    ]


    # Initialize the config object
    def __init__ (self, fn):
        self.vault = ConfigParser.RawConfigParser ()
        self.Read (fn)


    # Read the config from a file
    def Read (self, fn):
        try:
            self.vault.read (fn)
        except:
            # hmm, broken config file/very old version
            pass

        # Upgrade old config version, if needed
        if self.vault.has_section ('Encoder'):
            for x in self.upgrade_attrs:
                if not self.vault.has_option (x [3], x [2]) and \
                   self.vault.has_option (x [1], x [0]):
                    if not self.vault.has_section (x [3]):
                        self.vault.add_section (x [3])
                    self.vault.set (x [3], x [2], self.vault.get (x [1], x [0]))

            self.vault.remove_section ('Encoder')

        # Copy config file values to local attributes
        for attr in self.attrs:
            try:
                setattr (self, attr [0],
                    {
                        's': lambda: self.vault.get (attr [3], attr [0]),
                        'l': lambda: self.vault.getint (attr [3], attr [0]),
                        'i': lambda: self.vault.getint (attr [3], attr [0]),
                        'b': lambda: self.vault.getboolean (attr [3], attr [0]),
                        'F': lambda: self.vault.getboolean (attr [3], attr [0]),
                    } [attr [1]] ())
            except ConfigParser.NoSectionError:
                # no section in config file
                pass
            except ConfigParser.NoOptionError:
                # no such option in file, will set to default later
                pass
            except ValueError:
                # invalid value type, just ignore it
                pass


    def Save (self, fn):
        # Copy config values to config file
        for attr in self.attrs:
            try:
                # Create config section, if it does not exist yet
                if not self.vault.has_section (attr [3]):
                    self.vault.add_section (attr [3])

                self.vault.set (attr [3], attr [0], getattr (self, attr [0]))
            except AttributeError:
                # option value undefined, skip it
                pass

        # self.vault.write (fn) quietly ignores write errors ...
        try:
            f = file (fn, "w")
            self.vault.write (f)
            f.close ()
        except IOError:
            return False

        return True


    # Set up the controls according to the state stored in this object
    def SetupControls (self, gui):
        for attr in self.attrs:
            if hasattr (self, attr [0]):
                if attr [2]:
                    {
                        's': lambda: getattr (gui, attr [2]).set_text (getattr (self, attr [0])),
                        'l': lambda: getattr (gui, attr [2]).set_active (getattr (self, attr [0])),
                        'i': lambda: getattr (gui, attr [2]).set_value (getattr (self, attr [0])),
                        'b': lambda: getattr (gui, attr [2]).set_active (getattr (self, attr [0])),
                    } [attr [1]] ()
            elif attr [1] == 'F':
                # Boolean with default value 'False'
                setattr (self, attr [0], False)
            else:
                # If we don't have this value, read it from GUI
                self.ReadControl (gui, attr)
        # Pretend that the video width/height has changed, to set up the WxY combobox
        gui.on_SpinVideoSize_changed (None)


    # Read the state of the controls
    def ReadControls (self, gui):
        for attr in self.attrs:
            self.ReadControl (gui, attr)

        gui.UpdateFileMask ()


    # Read the state of a single control
    def ReadControl (self, gui, attr):
        if attr [2]:
            setattr (self, attr [0],
                {
                    's': lambda: getattr (gui, attr [2]).get_text ().strip (),
                    'l': lambda: getattr (gui, attr [2]).get_active (),
                    'i': lambda: int (getattr (gui, attr [2]).get_value ()),
                    'b': lambda: bool (getattr (gui, attr [2]).get_active ())
                } [attr [1]] ())
