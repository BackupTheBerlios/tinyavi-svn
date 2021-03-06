#!/usr/bin/env python

import os, sys, glob, shutil

from distutils.core import setup, Extension

VERSION = open ("VERSION").readline ().strip ()

def RemoveDir (d):
    for root, dirs, files in os.walk (d, topdown=False):
        for name in files:
            os.remove (os.path.join (root, name))
        for name in dirs:
            os.rmdir (os.path.join (root, name))
    os.rmdir (d)

op = None
for x in sys.argv [1:]:
    if x == "clean" or x == "install" or x == "build":
        op = x

# Create mo files:
mofiles = []
for pofile in glob.glob('po/*.po'):
    lang = os.path.splitext (os.path.basename (pofile)) [0]
    # Piggyback on the lib/ directory used by setup()
    path = "build/locale/" + lang
    if not os.path.exists(path):
        os.makedirs (path, 0755)
    mofile = path + "/tinyavi.mo"
    if op == "install" or op == "build":
        print "Generating", mofile
        os.system("msgfmt %s -o %s" % (pofile, mofile))
    mofiles.append (('share/locale/' + lang + '/LC_MESSAGES', [mofile]))

# Patch module version in __init__.py
ct = open ("tinyavi/__init__.py").readlines ()
for ln in range (0, len (ct)):
    if ct [ln].find ("VERSION =") >= 0:
        ct [ln] = "VERSION = \"%s\"\n" % VERSION
open ("tinyavi/__init__.py", "w").writelines (ct)

setup (name = 'tinyavi',
        version = VERSION,
        description = 'A toolkit for creation of tiny AVI files for portable devices',
        author = 'Andrew Zabolotny',
        author_email = 'zap@homelink.ru',
        url = 'http://tinyavi.berlios.de/',
        license = 'GPL',
        platforms = ['Unix'],
        classifiers = [
            'Development Status :: 5 - Production/Stable',
            'Environment :: X11 Applications',
            'Intended Audience :: End Users/Desktop',
            'License :: GNU General Public License (GPL)',
            'Operating System :: Linux',
            'Programming Language :: Python',
            'Topic :: Multimedia :: Video :: Editors',
            ],
        packages = ["tinyavi"],
        package_dir = { "tinyavi": "tinyavi/"},
        scripts = ['tavi', 'tavi-gui'],
        data_files = [
            ('share/tinyavi', ['share/gui.glade', 'share/tavi.svg']),
            ('share/applications', ['build/tinyavi.desktop']),
            ('share/pixmaps', ['share/tavi.svg'])
            ] + mofiles,
        long_description = """
TinyAVI is a set of two tools (one command-line, one GUI) which can convert
video files to a format suitable for (some) portable devices.

The GUI tool is designed to be very easy to use, it supports batch conversion
of multiple video files at once (on SMP) and integrates nicely with the GNOME."""
        )

if op == "clean":
    RemoveDir ("build/locale")
