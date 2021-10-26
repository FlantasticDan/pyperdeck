from typing import List

from .timecode import Timecode, parse_framerate

class Slot:
    """Low Level Hyperdeck Media Slot Interface
    """    
    def __init__(self, id: int) -> None:
        """Initialize a Media Slot Interface

        Parameters
        ----------
        id : int
            Hyperdeck Hardware Slot ID
        """        
        self.id = id

        self.status = None
        self.volume_name = None
        self.recording_time = 0
        self.video_format = None
        self.framerate = 0
        self.blocked = False

        self.clips = []
    
    def _slot_info(self, body: List[str]) -> None:
        for field in body:
            prop, value = field.split(': ')
            if prop == 'status':
                self.status = value
            elif prop == 'volume name':
                self.volume_name = value
            elif prop == 'recording time':
                self.recording_time = int(value)
            elif prop == 'video format':
                self.video_format = value
                self.framerate = parse_framerate(self.video_format)
            elif prop == 'blocked':
                self.blocked = value == 'true'

    def _disk_list(self, body: List[str]) -> None:
        self.clips = []
        for field in body:
            prop, value = field.split(': ')
            if prop == 'slot id':
                continue
            self.clips.append(DiskClip(int(prop), value, self.framerate))

class DiskClip:
    def __init__(self, clip_id: int, entry: str, framerate: int) -> None:
        self.original = entry
        
        self.clip_id = clip_id
        self.name = ''
        self.file_format = ''
        self.video_format = ''
        self.duration = ''
        self.duration_frames = 0

        soup, duration = entry.rsplit(' ', 1)
        self.duration = duration
        self.duration_frames = Timecode(self.duration, framerate).frame_count
        soup, video_format = soup.rsplit(' ', 1)
        self.video_format = video_format
        name, file_format = soup.rsplit(' ', 1)
        self.file_format = file_format
        self.name = name
    
    def __repr__(self) -> str:
        return self.original

class Timeline:
    def __init__(self) -> None:
        self.clips = []
        self.framerate = 0
        self.duration = 0
    
    def _clip_info(self, body: List[str], framerate: int) -> None:
        self.clips = []
        self.framerate = framerate
        for field in body:
            prop, value = field.split(': ')
            if prop == 'clip count':
                continue
            clip = TimelineClip(int(prop), value, framerate)
            self.duration += clip.duration_frames
            self.clips.append(clip)

class TimelineClip:
    def __init__(self, clip_id: int, entry: str, framerate: int) -> None:
        self.original = entry
        
        self.clip_id = clip_id
        self.name = ''
        self.start_timecode = ''
        self.duration = ''
        self.duration_frames = 0

        self.duration = entry[-11:]
        self.start_timecode = entry[-23:-12]
        self.name = entry[:-24]

        self.duration_frames = Timecode(self.duration, framerate).frame_count
    
    def __repr__(self) -> str:
        return self.original