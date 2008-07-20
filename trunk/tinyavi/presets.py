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
            "-ovc x264 -x264encopts bitrate=%(bitrate)d:frameref=6:analyse=all:me=umh:subme=7:trellis=2:bframes=1:subq=7:brdo:mixed_refs:weight_b:bime:no_fast_pskip:direct_pred=auto:mixed_refs:nr=200:threads=auto:turbo=2:pass=1",
            "-ovc x264 -x264encopts bitrate=%(bitrate)d:frameref=6:analyse=all:me=umh:subme=7:trellis=2:bframes=1:subq=7:brdo:mixed_refs:weight_b:bime:no_fast_pskip:direct_pred=auto:mixed_refs:nr=200:threads=auto:pass=2"
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
    "lavc-aac" : {
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
    }
}

# Note1: It is adviced that target width and height must be multiple of 16!
# Note2: Aliase MUST BE UPPERCASE!
List = {
    "Cowon D2": {
        "Alias"         : "CD2",
        "VideoWidth"    : 320,
        "VideoHeight"   : 240,
        "MaxWidth"      : 320,
        "MaxHeight"     : 240,
        "VideoCodec"    : "xvid",
        "AudioCodec"    : "lame",
        "Extension"     : "avi"
    },

    "Aero Vision photo frame": {
        "Alias"         : "AV",
        "VideoWidth"    : 400,
        "VideoHeight"   : 240,
        "MaxWidth"      : 800,
        "MaxHeight"     : 480,
        "VideoCodec"    : "xvid",
        "AudioCodec"    : "lame",
        "VideoOptions"  : {
            "opts1"    : "-xvidencopts max_bframes=0",
            "opts2"    : "-xvidencopts max_bframes=0"
        },
        "Extension"     : "avi"
    },

    "Nokia N8x0 (GStreamer engine)": {
        "Alias"         : "N8X0",
        "VideoWidth"    : 400,
        "VideoHeight"   : 240,
        "MaxWidth"      : 800,
        "MaxHeight"     : 480,
        "VideoCodec"    : "xvid",
        "AudioCodec"    : "lame",
        "VideoOptions"  : {
            "opts1"    : "-xvidencopts max_bframes=0",
            "opts2"    : "-xvidencopts max_bframes=0"
        },
        "Extension"     : "avi"
    },

    "Nokia N8x0 (MPlayer engine - best)": {
        "Alias"         : "N8X0MP",
        "VideoWidth"    : 512,
        "VideoHeight"   : 304,
        "MaxWidth"      : 800,
        "MaxHeight"     : 480,
        "VideoCodec"    : "xvid",
        "AudioCodec"    : "lame",
        "Extension"     : "avi"
    },

    "iPOD (untested)": {
        "Alias"         : "IPOD",
        "VideoWidth"    : 320,
        "VideoHeight"   : 240,
        "MaxWidth"      : 320,
        "MaxHeight"     : 240,
        "VideoCodec"    : "xvid",
        "AudioCodec"    : "lavc-aac",
        "Extension"     : "avi"
    },

    "Sony PSP (MPEG4) (untested)": {
        "Alias"         : "PSP-MP4",
        "VideoWidth"    : 480,
        "VideoHeight"   : 272,
        "MaxWidth"      : 480,
        "MaxHeight"     : 272,
        "VideoCodec"    : "lavc-mpeg4",
        "VideoFilter"   : [ "harddup" ],
        "AudioCodec"    : "lavc-aac",
        "AudioFilter"   : [ "lavcresample=24000" ],
        "VideoOptions"  : {
            "opts1"    : "-lavfopts format=psp",
            "opts2"    : "-lavfopts format=psp"
        },
        "Extension"     : "mp4"
    },

    "Sony PSP (H264) (untested)": {
        "Alias"         : "PSP-264",
        "VideoWidth"    : 480,
        "VideoHeight"   : 272,
        "MaxWidth"      : 480,
        "MaxHeight"     : 272,
        "VideoCodec"    : "x264",
        "AudioCodec"    : "lavc-aac",
        "AudioFilter"   : [ "lavcresample=48000" ],
        "VideoOptions"  : {
            "opts1"    : "-lavfopts format=psp",
            "opts2"    : "-lavfopts format=psp"
        },
        "Extension"     : "avi"
    }
}
