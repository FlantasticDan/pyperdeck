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