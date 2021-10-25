"""Timecode Utlity Functions
"""

def parse_framerate(video_format: str) -> int:
    """Parse framerate from a Hyperdeck Video Format

    Parameters
    ----------
    video_format : str
        Hyperdeck Video Format String

    Returns
    -------
    int
        Framerate
    """    
    if '50' in video_format:
        return 50
    elif '5994' in video_format:
        return 60
    elif '60' in video_format:
        return 60
    elif '23976' in video_format:
        return 24
    elif '24' in video_format:
        return 24
    elif '25' in video_format:
        return 25
    elif '2997' in video_format:
        return 30
    elif '30' in video_format:
        return 30