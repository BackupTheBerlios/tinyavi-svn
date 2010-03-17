#
# Module initialization
#

import os
import locale

# The following line is automatically replaced in setup.py
VERSION = "0.2.4"

# Detect filename encoding: this exactly mimics the behaviour of glib
FNENC = os.getenv ("G_FILENAME_ENCODING")
if not FNENC:
    if os.getenv ("G_BROKEN_FILENAMES"):
        FNENC = locale.getpreferredencoding ()
    else:
        FNENC = "UTF-8"

if os.name == "nt":
    from tinyavi import osw_windows
    OSW = osw_windows
else:
    from tinyavi import osw_posix
    OSW = osw_posix
