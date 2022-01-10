import time
import logging
from os import linesep, stat
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
        self.logger = logging.getLogger(__name__)

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
        self.stop_mode = None

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
        self._send('play option')
        
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
            except Exception as e:
                self.logger.error(e)
                time.sleep(3)
                self.connection = Telnet(self.ip, 9993)
                self._send('ping')
    
    def _send(self, command: str) -> None:
        self.logger.debug(f'Sending Message: [{command.replace(linesep, "-")}]')
        self.connection.write(bytes(command + '\r\n', 'ascii'))
    
    def _decode_response(self, message: bytes) -> None:
        response = message.decode('ascii').rstrip('\r\n')
        status = self._get_status_of_message(response)
        if status[0] < 200:
            self.logger.warning(f'Failure Response Recieved: [{response.replace(linesep, "//")}]')
        else:
            self.logger.debug(f'Response Recieved: [{response.replace(linesep, "//")}]')

    def _decode_message(self, message: bytes) -> None:
        msg = message.decode('ascii').rstrip('\r\n\r\n')
        lines = msg.split('\r\n')
        status = self._get_status_of_message(lines[0])
        body = lines[1:]
        self.logger.debug(f'Recieved Message: [{msg.replace(linesep, "//")}]')
        if 500 <= status[0] <= 599:
            self._asynchronous_response_processor(status, body)
        elif 200 < status[0] <= 299:
            self._success_response_processor(status, body)
        
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
        if slot != 'none':
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
                if value != 'none':
                    self.active_slot = int(value)
                    self._send('clips get')
                else:
                    self.active_slot = None
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
        elif status[1] == 'format ready':
            self._format(body)
        elif status[1] == 'play option info':
            self._play_option(body)
    
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

        self.logger.info(f'Connected to {self.model} @ {self.ip}, software version {self.software_version}, protocol version {self.protocol_version}')

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

    def _format(self, body: List[str]) -> None:
        format_token = body[0]
        self._send(f'format: confirm: {format_token}')

    def _play_option(self, body: List[str]) -> None:
        for field in body:
            prop, value = field.split(': ')
            if prop == 'stop mode':
                self.stop_mode = value

    def preview(self) -> None:
        """Set the Hyperdeck to preview mode, which allows for clips to be recorded.
        """
        self._send('preview: enable: true')
    
    def output(self) -> None:
        """Set the Hyperdeck to output mode, which allows for the playback of clips on the timeline.
        """
        self._send('preview: enable: false')
    
    def record(self, name: str = None) -> None:
        """Record a clip to the active slot.

        Parameters
        ----------
        name : str, optional
            File name of the recorded clip, otherwise generated in sequence by the Hyperdeck, by default `None`
        """        
        _record = 'record'
        if name:
            _record = f'record: name: {name}'
        
        self._send(_record)

    def spill(self, slot: int = 0) -> None:
        """Spill recording from one slot to another.

        Parameters
        ----------
        slot : int, optional
            Slot to spill recording to, if not set, spills to the next available slot, by default 0
        """
        command = 'record spill'
        if slot > 0:
            command += f': slot id: {slot}'
        self._send(command)

    def stop(self) -> None:
        """Stop recording or pause playback
        """
        self._send('stop')

    def play(self, speed: int = 100, loop: bool = False, single_clip: bool = False) -> None:
        """Play the timeline from the current timecode.

        Parameters
        ----------
        speed : int, optional
            Speed of playback as a percentage (range `-5000` to  `5000`), by default `100`
        loop : bool, optional
            Loop playback at the end of playback range (`True`) or stop-at-end (`False`), by default `False`
        single_clip : bool, optional
            Playback only current clip (`True`) or all clips (`False`), by default `False`
        """
        _speed = f'speed: {speed}'
        _loop = f'loop: false'
        if loop:
            _loop = f'loop: true'
        _single_clip = f'single clip: false'
        if single_clip:
            _single_clip = f'single clip: true'

        self._send(f'play: {_speed} {_loop} {_single_clip}')

    def playrange_clip(self, clip_id: int, count: int = 1) -> None:
        """Set timeline playrange based based on clip IDs and move playhead to the start.

        Parameters
        ----------
        clip_id : int
            Starting clip ID
        count : int, optional
            Number of clips to include at range, starting at clip ID, by default 1
        """
        assert count > 0, 'Count must be a positive intager'
        self._send(f'playrange set: clip id: {clip_id} count: {count}')

    def playrange_timecode(self, in_timecode: str, out_timecode: str) -> None:
        """Set timeline playrange based based on in/out timecodes and move playhead to the in timecode.

        Parameters
        ----------
        in_timecode : str
            Starting Timecode
        out_timecode : str
            Ending Timecode
        """
        self._send(f'playrange set: in: {in_timecode} out: {out_timecode}')
    
    def playrange_frame(self, in_frame: int, out_frame: int) -> None:
        """Set timeline playrange based based on frame numbers and move playhead to the start.

        Parameters
        ----------
        in_frame : int
            Starting Frame
        out_frame : int
            Ending Frame
        """
        self._send(f'playrange set: timeline in: {in_frame} timeline out: {out_frame}')
    
    def clear_playrange(self) -> None:
        """Clear the timeline playrange.
        """
        self._send('playrange clear')

    def configure(
            self,
            *,
            video_input: str = None,
            audio_input: str = None,
            file_format: str = None,
            audio_codec: str = None,
            play_option: str = None,
        ) -> None:
        """Change the configuration of the Hyperdeck.  Timecode, audio channels, record triggers, file naming, and genlock settings are unimplemented.

        Parameters
        ----------
        video_input : str, optional
            Source of video signal (one of SDI, HDMI, or component), by default unchanged
        audio_input : str, optional
            Source of the audio signal (one of embedded, XLR, or RCA), by default unchanged
        file_format : str, optional
            Recording file format/codec configuration for future recordings, by default unchanged
        audio_codec : str, optional
            Recording codec of the audio signal for future recordings, by default unchanged
        play_option : str
            Sets the output frame when playback stops (one of lastframe, nextframe, or black), by default unchanged
        """
        command = 'configuration: '
        if video_input:
            command += f'video input: {video_input} '
        if audio_input:
            command += f'audio input: {audio_input} '
        if file_format:
            command += f'file format: {file_format} '
        if audio_codec:
            command += f'audio codec: {audio_codec} '
        if command != 'configuration: ':
            self._send(command[:-1])
        
        if play_option:
            self._send(f'play option: stop mode: {play_option}')
            self._send('play option')

    def format(self) -> None:
        """Format the active slot to exFAT, this will delete all data on the media in that slot.
        """        
        self._send('format: prepare: exFAT')

    def reboot(self) -> None:
        """Reboot the Hyperdeck, reconnection happens automatically.
        """
        self._send('reboot')
    