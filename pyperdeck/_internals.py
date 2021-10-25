from typing import List

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
        self.blocked = False
    
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
            elif prop == 'blocked':
                self.blocked = value == 'true'

class Timeline:
    def __init__(self) -> None:
        self.clips = []
    
    def _clip_info(self, body: List[str]) -> None:
        self.clips = []
        for field in body:
            prop, value = field.split(': ')
            if prop == 'clip count':
                continue
            self.clips.append(TimelineClip(int(prop), value))

class TimelineClip:
    def __init__(self, clip_id: int, entry: str) -> None:
        self.clip_id = clip_id
        self.name = ''
        self.start_timecode = ''
        self.duration = ''

        self.duration = entry[-11:]
        self.start_timecode = entry[-23:-12]
        self.name = entry[:-24]
