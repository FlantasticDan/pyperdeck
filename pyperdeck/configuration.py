'''Configuration Constants'''

class VideoInput:
    SDI = 'SDI'
    HDMI = 'HDMI'
    COMPONENT = 'component'

class AudioInput:
    EMBEDDED = 'embedded'
    XLR = 'XLR'
    RCA = 'RCA'

class AudioCodec:
    PCM = 'PCM'
    AAC = 'AAC'

class FileFormat:
    class H264:
        HIGH_SDI = 'H.264High_SDI'
        HIGH = 'H.264High'
        MEDIUM = 'H.264Medium'
        LOW = 'H.264Low'
    class H265:
        HIGH_SDI = 'H.265High_SDI'
        HIGH = 'H.265High'
        MEDIUM = 'H.265Medium'
        LOW = 'H.265Low'
    class QuickTime:
        PRORES_HQ = 'QuickTimeProResHQ'
        PRORES = 'QuickTimeProRes'
        PRORES_LT = 'QuickTimeProResLT'
        PRORES_PROXY = 'QuickTimeProResProxy'
        DNXHD220X = 'QuickTimeDNxHD220x'
        DNXHD145 = 'QuickTimeDNxHD145'
        DNXHD45 = 'QuickTimeDNxHD45'
        DNXHR_HQX = 'QuickTimeDNxHR_HQX'
        DNXHR_SQ = 'QuickTimeDNxHR_SQ'
        DNXHR_LB= 'QuickTimeDNxHR_LB'
    class DNxH:
        D220X = 'DNxHD220x'
        D145 = 'DNxHD145'
        D45 = 'DNxHD45'
        R_HQX = 'DNxHR_HQX 4Kp60'
        R_SQ = 'DNxHR_SQ'
        R_LB = 'DNxHR_LB'
