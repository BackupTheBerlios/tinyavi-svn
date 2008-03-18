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

# Create mo files:
mofiles = []
for pofile in glob.glob('po/*.po'):
    lang = os.path.splitext (os.path.basename (pofile)) [0]
    path = "build/mo/" + lang
    if not os.path.exists(path):
        os.makedirs (path, 0755)
    mofile = path + "/tinyavi.mo"
    print "Generating", mofile
    os.system("msgfmt %s -o %s" % (pofile, mofile))
    mofiles.append (('share/locale/' + lang + '/LC_MESSAGES', [mofile]))

# Patch module version in __init__.py
ct = open ("tinyavi/__init__.py").readlines ()
for ln in range (0, len (ct)):
    if ct [ln].find ("VERSION =") >= 0:
        ct [ln] = "VERSION = \"%s\"\n" % VERSION
open ("tinyavi/__init__.py", "w").writelines (ct)

try:
    setup (name = 'tinyavi',
            version = VERSION,
            description = 'A toolkit for creation of tiny AVI files for portable devices',
            author = 'Andrew Zabolotny',
            author_email = 'zap@homelink.ru',
            url = 'http://tinyavi.berlios.de/',
            classifiers = [
                'Development Status :: 4 - Beta',
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
                ('share/doc/tinyavi-' + VERSION, ['README', 'CHANGELOG', 'TRANSLATORS']),
                ('share/applications', ['tavi.desktop']),
                ('share/pixmaps', ['share/tavi.svg'])
                ] + mofiles
            )
except SystemExit, msg:
    print msg

# Cleanup
RemoveDir("build")
