#
# Video encoding presets for TinyAVI
#

#
# For multi-pass encoding, the first string will contain the mencoder options
# for the first pass, and second string will contain the options for second pass.
#

# Video codecs
vc = {
    # XviD encoder
    "xvid" : {
        # 0 - low quality/small size
        # 1 - medium quality/medium size
        # 2 - high quality/large size
        "Quality" : {
            0 : lambda w, h, fps: { "bitrate" : (w * h * fps) / 8000 },
            1 : lambda w, h, fps: { "bitrate" : (w * h * fps) / 6000 },
            2 : lambda w, h, fps: { "bitrate" : (w * h * fps) / 4000 },
        },
        "Options" : [
            "-ovc xvid -xvidencopts psnr:turbo:trellis:vhq=2:pass=1 %(opts1)s",
            "-ovc xvid -xvidencopts psnr:turbo:trellis:vhq=2:bitrate=%(bitrate)d:pass=2 %(opts2)s"
        ],
    },
    # lavc library, MPEG4 codec
    "lavc-mpeg4" : {
        "Quality" : {
            0 : lambda w, h, fps: { "bitrate" : (w * h * fps) / 8000 },
            1 : lambda w, h, fps: { "bitrate" : (w * h * fps) / 6000 },
            2 : lambda w, h, fps: { "bitrate" : (w * h * fps) / 4000 },
        },
        "Options" : [
            "-ovc lavc -of lavf -lavcopts vcodec=mpeg4:vglobal=1:vpass=1:turbo %(opts1)s",
            "-ovc lavc -of lavf -lavcopts vcodec=mpeg4:vglobal=1:vpass=2:vbitrate=%(bitrate)d %(opts2)s"
        ],
    },
    # Encode to H.264 by using the x264 encoder
    "x264" : {
        "Quality" : {
            0 : lambda w, h, fps: { "bitrate" : (w * h * fps) / 10000 },
            1 : lambda w, h, fps: { "bitrate" : (w * h * fps) / 8000 },
            2 : lambda w, h, fps: { "bitrate" : (w * h * fps) / 6000 },
        },
        "Options" : [
            "-of lavf -ovc x264 -x264encopts bitrate=%(bitrate)d:subq=4:bframes=2:weight_b:threads=auto:pass=1",
            "-of lavf -ovc x264 -x264encopts bitrate=%(bitrate)d:subq=4:bframes=2:weight_b:threads=auto:pass=2"
        ],
    },
    # Encode to H.264 by using the high-quality x264 encoder (HD & HDR)
    "x264-hq" : {
        "Quality" : {
            0 : lambda w, h, fps: { "bitrate" : (w * h * fps) / 10000 },
            1 : lambda w, h, fps: { "bitrate" : (w * h * fps) / 8000 },
            2 : lambda w, h, fps: { "bitrate" : (w * h * fps) / 6000 },
        },
        "Options" : [
            "-ovc x264 -x264encopts bitrate=%(bitrate)d:subq=5:8x8dct:frameref=2:bframes=3:weight_b:threads=auto:pass=1",
            "-ovc x264 -x264encopts bitrate=%(bitrate)d:subq=5:8x8dct:frameref=2:bframes=3:weight_b:threads=auto:pass=2"
            #" -of lavf -lavfopts format=matroska"
        ],
    },
}

ac = {
    # Pass-through audio
    "pass" : {
        "Options" : [
            "-nosound",
            "-oac copy"
        ],
    },
    # Encode to mp3 with lame, joint-stereo
    "lame" : {
        "Quality" : {
            0 : lambda: { "quality" : 5 },
            1 : lambda: { "quality" : 3 },
            2 : lambda: { "quality" : 2 },
        },
        "Options" : [
            "-nosound",
            "-oac mp3lame -lameopts q=%(quality)d:mode=1:aq=1"
        ],
    },
    # Encode to ac3 audio
    "aac" : {
        "Quality" : {
            0 : lambda: { "quality" : 80 },
            1 : lambda: { "quality" : 100 },
            2 : lambda: { "quality" : 120 },
        },
        "Options" : [
            "-nosound",
            # For some reason without object=2 the output sound
            # is horrible, it floats and clicks.
            "-oac faac -faacopts quality=%(quality)d:object=2"
        ]
    },
    # Encode to mp2 audio
    "mp2" : {
        "Quality" : {
            0 : lambda: { "quality" : 96 },
            1 : lambda: { "quality" : 128 },
            2 : lambda: { "quality" : 160 },
        },
        "Options" : [
            "-nosound",
            "-oac lavc -lavcopts acodec=mp2:abitrate=%(quality)d"
        ]
    }
}

# Note1: It is adviced that target width and height must be multiple of 16!
# Note2: Preset IDs MUST BE UPPERCASE!
List = {
    "CD2": {
        "Device"        : "Cowon D2",
        "VideoWidth"    : 320,
        "VideoHeight"   : 240,
        "VideoCodec"    : "xvid",
        "AudioCodec"    : "lame"
    },

    "AV": {
        "Device"        : "Aero Vision",
        "Comment"       : "photo frame",
        "VideoWidth"    : 400,
        "VideoHeight"   : 240,
        "MaxWidth"      : 800,
        "MaxHeight"     : 480,
        "VideoCodec"    : "xvid",
        "AudioCodec"    : "lame",
        "VideoOptions"  : {
            "opts1"     : "-xvidencopts max_bframes=0",
            "opts2"     : "-xvidencopts max_bframes=0"
        }
    },

    "N8X0": {
        "Device"        : "Nokia N8x0",
        "Comment"       : "GStreamer engine",
        "VideoWidth"    : 400,
        "VideoHeight"   : 240,
        "MaxWidth"      : 800,
        "MaxHeight"     : 480,
        "VideoCodec"    : "xvid",
        "AudioCodec"    : "lame",
        "VideoOptions"  : {
            "opts1"     : "-xvidencopts max_bframes=0",
            "opts2"     : "-xvidencopts max_bframes=0"
        }
    },

    "N8X0MP": {
        "Device"        : "Nokia N8x0",
        "Comment"       : "MPlayer engine - best",
        "VideoWidth"    : 512,
        "VideoHeight"   : 304,
        "MaxWidth"      : 800,
        "MaxHeight"     : 480,
        "VideoCodec"    : "xvid",
        "AudioCodec"    : "lame"
    },

    "IPOD": {
        "Device"        : "iPOD",
        "Comment"       : "untested",
        "VideoWidth"    : 320,
        "VideoHeight"   : 240,
        "VideoCodec"    : "xvid",
        "AudioCodec"    : "aac"
    },

    "PSPMP4": {
        "Device"        : "Sony PSP",
        "Comment"       : "MPEG4, untested",
        "VideoWidth"    : 480,
        "VideoHeight"   : 272,
        "VideoCodec"    : "lavc-mpeg4",
        "VideoFilter"   : [ "harddup" ],
        "AudioCodec"    : "aac",
        "AudioFilter"   : [ "lavcresample=24000" ],
        "VideoOptions"  : {
            "opts1"     : "-lavfopts format=psp",
            "opts2"     : "-lavfopts format=psp"
        },
        "Extension"     : "mp4"
    },

    "PSP264": {
        "Device"        : "Sony PSP",
        "Comment"       : "H264, untested",
        "VideoWidth"    : 480,
        "VideoHeight"   : 272,
        "VideoCodec"    : "x264",
        "AudioCodec"    : "aac",
        "AudioFilter"   : [ "lavcresample=48000" ],
        "VideoOptions"  : {
            "opts1"     : "-lavfopts format=psp",
            "opts2"     : "-lavfopts format=psp"
        },
        "Extension"     : "avi"
    },

    "HDR": {
        "Device"        : "Generic HDR",
        "Comment"       : "HD Ready Video",
        "VideoWidth"    : 1280,
        "VideoHeight"   : 720,
        "MaxWidth"      : 0,
        "MaxHeight"     : 0,
        "VideoCodec"    : "x264-hq",
        "AudioCodec"    : "pass",
        "VideoPostproc" : False,
        "Extension"     : "avi" # "mkv"
    },

    "HD": {
        "Device"        : "Generic HD",
        "Comment"       : "HD Video",
        "VideoWidth"    : 1920,
        "VideoHeight"   : 1080,
        "MaxWidth"      : 0,
        "MaxHeight"     : 0,
        "VideoCodec"    : "x264-hq",
        "AudioCodec"    : "pass",
        "VideoPostproc" : False,
        "Extension"     : "avi" # "mkv"
    },

    "TX8X0": {
        "Device"        : "teXet T-8X0",
        "Comment"       : "models 800, 810, 820, 840",
        "VideoWidth"    : 320,
        "VideoHeight"   : 240,
        "VideoCodec"    : "xvid",
        "AudioCodec"    : "mp2",
        "AudioFilter"   : [ "lavcresample=44100" ],
        "AudioOptions"  : {
            "opts1"     : "",
            "opts2"     : "-srate 44100"
        },
        "VideoOptions"  : {
            "opts1"     : "-ofps 22 -xvidencopts max_bframes=0:quant_type=h263",
            "opts2"     : "-ofps 22 -xvidencopts max_bframes=0:quant_type=h263"
        }
    },

    "NX910": {
        "Device"        : "NEXX NF-910",
        "VideoWidth"    : 160,
        "VideoHeight"   : 128,
        "VideoCodec"    : "xvid",
        "AudioCodec"    : "lame",
        "VideoOptions"  : {
            "opts1"     : "-ofps 25/2",
            "opts2"     : "-ofps 25/2"
        },
    }
}
