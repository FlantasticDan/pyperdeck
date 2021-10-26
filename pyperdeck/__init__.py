import time
from telnetlib import Telnet
from threading import Thread
from typing import List, Tuple, Dict

from ._internals import Slot, Timeline
from .timecode import parse_framerate

class Hyperdeck:
    """Blackmagic Design Hyperdeck Control Interface

    Parameters
    ----------
    ip : str
        Local IP Address of the Hyperdeck
    """    
    def __init__(self, ip: str) -> None:     
        self.ip = ip
        self.connection = Telnet(ip, 9993)

        self._reader_thread = Thread(target=self._reader)
        self._reader_thread.start()

        # Device Info
        self.protocol_version = None
        self.model = None
        self.unique_id = None
        self.slot_count = 0
        self.software_version = None

        # Slot Info
        self.slots = {} # type: Dict[str, Slot]
        self.remaining_time = 0 # recording time remaining in seconds

        # Transport Info
        self.status = None
        self.speed = 0
        self.slot_id = 0
        self.active_slot = 0
        self.clip_id = 0
        self.single_clip = False
        self.display_timecode = None
        self.timecode = None
        self.video_format = None
        self.framerate = 0
        self.loop = False
        self.timeline_playhead = 0
        self.input_video_format = None
        self.dynamic_range = None

        # Playrange Info
        self.timeline_in = 0
        self.timeline_out = 0

        # Configuration
        self.audio_input = None
        self.audio_mapping = 0
        self.video_input = None
        self.file_format = None
        self.audio_codec = None
        self.timecode_input = None
        self.timecode_output = None
        self.timecode_preference = None
        self.timecode_preset = None
        self.audio_input_channels = 0
        self.record_trigger = None
        self.record_prefix = None
        self.append_timestamp = False
        self.genlock_input_resync = False

        # Timeline
        self.timeline = Timeline()

    def _startup(self) -> None:
        self._send('device info')
        self._send('configuration')
        self._send('transport info')
        self._send('playrange')
        self._send('clips get')
        
        self._notify('transport')
        self._notify('display timecode')
        self._notify('timeline position')
        self._notify('playrange')
        self._notify('slot')
        self._notify('configuration')

    def _notify(self, prop: str, enable: bool = True) -> None:
        value = 'false'
        if enable:
            value = 'true'
        self._send(f'notify: {prop}: {value}')

    def _reader(self) -> None:
        while True:
            try:
                message = self.connection.read_until(bytes('\r\n', 'ascii'))
                if message.decode('ascii')[-3] == ':':
                    message += self.connection.read_until(bytes('\r\n\r\n', 'ascii'))
                    self._decode_message(message)
                else:
                    self._decode_response(message)
            except Exception:
                time.sleep(3)
                self.connection = Telnet(self.ip, 9993)
                self._send('ping')
    
    def _send(self, command: str) -> None:
        self.connection.write(bytes(command + '\r\n', 'ascii'))
    
    def _decode_response(self, message: bytes) -> None:
        response = message.decode('ascii').rstrip('\r\n')
        status = self._get_status_of_message(response)
        print(status)

    def _decode_message(self, message: bytes) -> None:
        msg = message.decode('ascii').rstrip('\r\n\r\n')
        lines = msg.split('\r\n')
        status = self._get_status_of_message(lines[0])
        body = lines[1:]
        if 500 <= status[0] <= 599:
            self._asynchronous_response_processor(status, body)
        elif 200 < status[0] <= 299:
            self._success_response_processor(status, body)
        print(status)
        print(body)
        
    def _get_status_of_message(self, status_line: str) -> Tuple[int, str]:
        blocks = status_line.rstrip(':').split(' ', maxsplit=1)
        status = int(blocks[0])
        response = blocks[1]
        return status, response
    
    def _asynchronous_response_processor(self, status: Tuple[int, str], body: List[str]) -> None:
        if status[1] == 'connection info':
            self._connection_info(body)
        elif status[1] == 'slot info':
            self._slot_info(body)
        elif status[1] == 'transport info':
            self._transport_info(body)
        elif status[1] == 'timeline position':
            self._timeline_position(body)
        elif status[1] == 'display timecode':
            self._display_timecode(body)
        elif status[1] == 'playrange info':
            self._playrange_info(body)
        elif status[1] == 'configuration':
            self._configuration(body)
    
    def _connection_info(self, body: List[str]) -> None:
        for field in body:
            prop, value = field.split(': ')
            if prop == 'protocol version':
                self.protocol_version = value
            elif prop == 'model':
                self.model = value
        self._startup()
    
    def _slot_info(self, body: List[str]) -> None:
        slot = None
        for field in body:
            prop, value = field.split(': ')
            if prop == 'slot id':
                slot = value
                break
        self.slots[slot]._slot_info(body)
        self._recording_time_remaining()
    
    def _recording_time_remaining(self) -> None:
        remaining_time = 0
        for slot in self.slots.values():
            remaining_time += slot.recording_time
        self.remaining_time = remaining_time
    
    def _transport_info(self, body: List[str]) -> None:
        for field in body:
            prop, value = field.split(': ')
            if prop == 'status':
                self.status = value
            elif prop == 'speed':
                self.speed = int(value)
            elif prop == 'slot id':
                self.slot_id = int(value)
            elif prop == 'active slot':
                self.active_slot = int(value)
                self._send('clips get')
            elif prop == 'clip id':
                self.clip_id = int(value)
            elif prop == 'single clip':
                self.single_clip = value == 'true'
            elif prop == 'display timecode':
                self.display_timecode = value
            elif prop == 'timecode':
                self.timecode = value
            elif prop == 'video format':
                self.video_format = value
                self.framerate = parse_framerate(self.video_format)
            elif prop == 'loop':
                self.loop = value == 'true'
            elif prop == 'timeline':
                self.timeline_playhead = int(value)
            elif prop == 'input video format':
                self.input_video_format = value
            elif prop == 'dynamic range':
                self.dynamic_range = value
    
    def _timeline_position(self, body: List[str]) -> None:
        for field in body:
            prop, value = field.split(': ')
            if prop == 'timeline':
                self.timeline_playhead = int(value)
    
    def _display_timecode(self, body: List[str]) -> None:
        for field in body:
            prop, value = field.split(': ')
            if prop == 'display timecode':
                self.display_timecode = value

    def _playrange_info(self, body: List[str]) -> None:
        for field in body:
            prop, value = field.split(': ')
            if prop == 'timeline in':
                try:
                    self.timeline_in = int(value)
                except ValueError:
                    self.timeline_in = 0
            elif prop == 'timeline out':
                try:
                    self.timeline_out = int(value)
                except ValueError:
                    self.timeline_out = 0
    
    def _configuration(self, body: List[str]) -> None:
        for field in body:
            prop, value = field.split(': ')
            if prop == 'audio input':
                self.audio_input = value
            elif prop == 'audio mapping':
                self.audio_mapping = int(value)
            elif prop == 'video input':
                self.video_input = value
            elif prop == 'file format':
                self.file_format = value
            elif prop == 'audio codec':
                self.audio_codec = value
            elif prop == 'timecode input':
                self.timecode_input = value
            elif prop == 'timecode output':
                self.timecode_output = value
            elif prop == 'timecode preference':
                self.timecode_preference = value
            elif prop == 'audio input channels':
                self.audio_input_channels = int(value)
            elif prop == 'record trigger':
                self.record_trigger = value
            elif prop == 'record prefix':
                self.record_prefix = value
            elif prop == 'append timestamp':
                self.append_timestamp = value == 'true'
            elif prop == 'genlock input resync':
                self.genlock_input_resync = value == 'true'

    def _success_response_processor(self, status: Tuple[int, str], body: List[str]) -> None:
        if status[1] == 'slot info':
            self._slot_info(body)
        elif status[1] == 'device info':
            self._device_info(body)
        elif status[1] == 'transport info':
            self._transport_info(body)
        elif status[1] == 'playrange info':
            self._playrange_info(body)
        elif status[1] == 'configuration':
            self._configuration(body)
        elif status[1] == 'clips info':
            self._clips_info(body)
        elif status[1] == 'disk list':
            self._disk_list(body)
    
    def _device_info(self, body: List[str]) -> None:
        for field in body:
            prop, value = field.split(': ')
            if prop == 'protocol version':
                self.protocol_version = value
            elif prop == 'model':
                self.model = value
            elif prop == 'unique id':
                self.unique_id = value
            elif prop == 'slot count':
                self.slot_count = int(value)
            elif prop == 'software version':
                self.software_version = value
        
        for slot in range(self.slot_count):
            self.slots[str(slot + 1)] = Slot(slot + 1)
            self._send(f'slot info: slot id: {slot + 1}')
            self._send(f'disk list: slot id: {slot + 1}')
    
    def _clips_info(self, body: List[str]) -> None:
        self.timeline._clip_info(body, self.framerate)

    def _disk_list(self, body: List[str]) -> None:
        slot = None
        for field in body:
            prop, value = field.split(': ')
            if prop == 'slot id':
                slot = value
                break
        self.slots[slot]._disk_list(body)

    def reboot(self) -> None:
        """Reboot the Hyperdeck, reconnection happens automatically.
        """
        self._send('reboot')
    