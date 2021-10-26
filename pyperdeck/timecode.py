"""Timecode Utlity Functions
"""

from typing import Type

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

def format_timecode(hours: int, minutes: int, seconds: int, frames: int, dropcode: bool) -> str:
    """Create a timecode string from timecode field values

    Parameters
    ----------
    hours : int
        Hours
    minutes : int
        Minutes
    seconds : int
        Seconds
    frames : int
        Frames
    dropcode : bool
        Dropcode refers to whether the final field in delinated with a colon or a semicolon.  `True` indicates semicolon.

    Returns
    -------
    str
        Timecode String
    """    
    frame_seperator = ':'
    if dropcode:
        frame_seperator = ';'
    return f'{hours:02}:{minutes:02}:{seconds:02}{frame_seperator}{frames:02}'

class Timecode (object):
    """
    Timecode Object for Simple Manipulation of Timecodes

    Allows additon and subtraction of Timecode Objects, Frame Integers, and Timecode Strings

    Parameters
    ----------
    timecode : str
        Timecode String (ex. `00:00:00:00`)
    framerate : int
        Framerate (commonly `24`, `25`, `30`, `50`, or `60`)
    """
    def __init__(self, timecode: str, framerate: int) -> None:
        assert len(timecode) == 11, 'Timecode Strings are always 11 characters'

        self.timecode = timecode
        self.framerate = framerate
        self.dropcode = ';' in timecode

        self.hours = int(self.timecode[:2])
        self.minutes = int(self.timecode[3:5])
        self.seconds = int(self.timecode[6:8])
        self.frames = int(self.timecode[9:])
        self.frame_count = 0

        self._calc_frame_count()
    
    def _calc_frame_count(self) -> None:
        self.frame_count += (self.hours * 60 * 60 * self.framerate)
        self.frame_count += (self.minutes  * 60 * self.framerate)
        self.frame_count += (self.seconds * self.framerate)
        self.frame_count += self.frames

    def __repr__(self) -> str:
        return(format_timecode(self.hours, self.minutes, self.seconds, self.frames, self.dropcode))
    
    def __add__(self, other):
        if type(other) == Timecode:
            hours = self.hours + other.hours
            minutes = self.minutes + other.minutes
            seconds = self.seconds + other.seconds
            frames = self.frames + other.frames

            seconds += frames // self.framerate
            frames = frames % self.framerate

            minutes += seconds // 60
            seconds = seconds % 60

            hours += minutes // 60
            minutes = minutes % 60

            return Timecode(format_timecode(hours, minutes, seconds, frames, self.dropcode), self.framerate)
        elif type(other) == int:
            hours = self.hours
            minutes = self.minutes
            seconds = self.seconds
            frames = self.frames + other

            seconds += frames // self.framerate
            frames = frames % self.framerate

            minutes += seconds // 60
            seconds = seconds % 60

            hours += minutes // 60
            minutes = minutes % 60

            return Timecode(format_timecode(hours, minutes, seconds, frames, self.dropcode), self.framerate)
        elif type(other) == str:
            return self + Timecode(other, self.framerate)
    
    def __sub__(self, other):
        if type(other) == Timecode:
            hours = self.hours - other.hours
            minutes = self.minutes - other.minutes
            seconds = self.seconds - other.seconds
            frames = self.frames - other.frames

            while frames < 0:
                seconds -= 1
                frames += self.framerate
            
            while seconds < 0:
                minutes -= 1
                seconds += 60
            
            while minutes < 0:
                hours -= 1
                minutes += 60
            
            if hours < 0:
                hours = 0
                minutes = 0
                seconds = 0
                frames = 0

            seconds += frames // self.framerate
            frames = frames % self.framerate

            minutes += seconds // 60
            seconds = seconds % 60

            hours += minutes // 60
            minutes = minutes % 60

            return Timecode(format_timecode(hours, minutes, seconds, frames, self.dropcode), self.framerate)
        elif type(other) == int:
            hours = self.hours
            minutes = self.minutes
            seconds = self.seconds
            frames = self.frames - other

            while frames < 0:
                seconds -= 1
                frames += self.framerate
            
            while seconds < 0:
                minutes -= 1
                seconds += 60
            
            while minutes < 0:
                hours -= 1
                minutes += 60
            
            if hours < 0:
                hours = 0
                minutes = 0
                seconds = 0
                frames = 0

            seconds += frames // self.framerate
            frames = frames % self.framerate

            minutes += seconds // 60
            seconds = seconds % 60

            hours += minutes // 60
            minutes = minutes % 60

            return Timecode(format_timecode(hours, minutes, seconds, frames, self.dropcode), self.framerate)
        elif type(other) == str:
            return self - Timecode(other, self.framerate)
