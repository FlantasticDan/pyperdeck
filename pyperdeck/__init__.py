import time
import logging
from os import linesep
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
    def __init__(self, ip: str, in_cmd_timeout: int = 5) -> None:     
        self.ip = ip
        self.cmd_timeout = in_cmd_timeout
        self.connection = Telnet(ip, 9993, self.cmd_timeout)
        self.logger = logging.getLogger(__name__)

        self._reader_thread = Thread(target=self._reader)
        self._reader_thread.start()

        # Device Info
        self.model = None # type: str
        """Model of Hyperdeck (ex. 'HyperDeck Studio HD Plus' )
        """        
        self.protocol_version = None # type: str
        """Hyperdeck Ethernet Protocol Version (ex. '1.12' )
        """
        self.software_version = None # type: str
        """Hyperdeck Software Version (ex. '8.0.2' )
        """        
        self.unique_id = None # type: str
        """Generated unique identifier for each Hyperdeck, persists across boots and network changes. (ex. '7c2e0d1443d2' )
        """        
        self.slot_count = 0 # type: int
        """Total number of media slots on the Hyperdeck, not necessarily the number of slots available for use.
        """        
        
        # Slot Info
        self.slots = {} # type: Dict[str, Slot]
        """Dictionary of Slot objects for each media slot, keyed by each slot's ID.
        """        
        self.remaining_time = 0
        """Recording time (in seconds) remaining on the active media slot with the current configuration settings.
        """        

        # Transport Info
        self.status = None # type: str
        """Status of the Hyperdeck, one of 'preview', 'stopped', 'play', 'forward', 'rewind', 'jog', 'shuttle', 'record'.
        """        
        self.speed = 0 # type: int
        """Playback speed as a percentage, between -5000 and 5000
        """        
        self.slot_id = 0 # type: int
        """Current active media slot, or `0` if no slot is active.
        """        
        self.active_slot = 0 # type: int
        self.clip_id = 0 # type: int
        """Clip ID of the clip the timeline playhead is currently within.
        """        
        self.single_clip = None # type: bool
        """Timeline playback mode, `True` indicates playback will only play within the current clip.
        """        
        self.display_timecode = None # type: str
        """Timecode shown on the front of the Hyperdeck
        """        
        self.timecode = None # type: str
        """Timecode within the current timeline for playback or the clip for record (from Blackmagic's documentation, meaning unclear)
        """        
        self.video_format = None # type: str
        """Video format of the output stream, one of 'NTSC', 'PAL', 'NTSCp', 'PALp', '720p50', '720p5994', '720p60', '1080p23976', '1080p24', '1080p25', '1080p2997', '1080p30', '1080i50', '1080i5994', '1080i60', '4Kp23976', '4Kp24', '4Kp25', '4Kp2997', '4Kp30', '4Kp50', '4Kp5994', '4Kp60'
        """        
        self.framerate = 0 # type: int
        """Frames per seconds of the output stream, commonly `24`, `25`, `30`, `50`, or `60`.
        """        
        self.loop = None # type: bool
        """Playback loop state, if `True`, playback loops back to the beginning when it reaches the end.
        """        
        self.timeline_playhead = 0 # type: int
        """Current frame number of the playhead on the timeline, the first frame of the timeline is frame `1`.
        """        
        self.input_video_format = None # type: str
        """Video format of the input stream, one of 'NTSC', 'PAL', 'NTSCp', 'PALp', '720p50', '720p5994', '720p60', '1080p23976', '1080p24', '1080p25', '1080p2997', '1080p30', '1080i50', '1080i5994', '1080i60', '4Kp23976', '4Kp24', '4Kp25', '4Kp2997', '4Kp30', '4Kp50', '4Kp5994', '4Kp60'
        """ 
        self.dynamic_range = None # type: str
        """Dynamic range setting of the Hyperdeck, one of 'off', 'Rec709', 'Rec2020_SDR', 'HLG', 'ST2084_300', 'ST2084_500', 'ST2084_800', 'ST2084_1000', 'ST2084_2000', 'ST2084_4000', 'ST2048' or 'none'.
        """        
        self.stop_mode = None # type: str
        """Behavior of the output stream when the playhead is stopped, one of `lastframe`, `nextframe`, or `black`.
        """        

        # Playrange Info
        self.timeline_in = 0 # type: int
        """Frame number of the timeline in point, or `0` if there is no active range
        """        
        self.timeline_out = 0 # type: int
        """Frame number of the timeline out point, or `0` if there is no active range
        """        

        # Configuration
        self.audio_input = None # type: str
        self.audio_mapping = 0 # type: int
        self.video_input = None # type: str
        self.file_format = None # type: str
        self.audio_codec = None # type: str
        self.timecode_input = None # type: str
        self.timecode_output = None # type: str
        self.timecode_preference = None # type: str
        self.timecode_preset = None # type: str
        self.audio_input_channels = 0 # type: int
        self.record_trigger = None # type: str
        self.record_prefix = None # type: str
        self.append_timestamp = False # type: bool
        self.genlock_input_resync = False # type: bool

        # Timeline
        self.timeline = Timeline() # type: Timeline
        """Currently active timeline object.
        """        

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
                self.connection = Telnet(self.ip, 9993, self.cmd_timeout)
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
        self._send('disk list')
        self._send('clips get')

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

    def add_clip(self, name: str, *, clip_id: int = 0, in_timecode: str = '', out_timecode: str = '') -> None:
        """Add a clip to the timeline.  Note that in/out timecodes are based on the clip's embedded timecode, and doesn't always begin at 00:00:00:00.

        Parameters
        ----------
        name : str
            Name of the clip to add, inclusive of the file extension
        clip_id : int, optional
            Clip ID of the clip in the timeline this clip should be added before, by default 0 (end of the timeline)
        in_timecode : str, optional
            If adding only a portion of the clip, the beginning timecode of the portion, by default '' (start of clip)
        out_timecode : str, optional
            If adding only a portion of the clip, the ending timecode of the portion, by default '' (end of clip)
        """
        command = 'clips add: '
        if clip_id > 0:
            command += f'clip id: {clip_id} '
        if in_timecode != '' and out_timecode != '':
            command += f'in: {in_timecode} out: {out_timecode} '
        command += f'name: {name}'
        self._send(command)
        self._send('clips get')

    def remove_clip(self, clip_id: int) -> None:
        """Remove a clip from the timeline.

        Parameters
        ----------
        clip_id : int
            Clip ID of the clip to remove, the first clip on the timeline is ID 1.
        """
        self._send(f'clips remove: clip id: {clip_id}')
        self._send('clips get')
    
    def clear_clips(self) -> None:
        """Clear all clips from the timeline
        """
        self._send('clips clear')

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

    def go_to_clip(self, clip_id: int) -> None:
        """Place timeline playhead at the start of a clip in timeline based on clip id.

        Parameters
        ----------
        clip_id : int
            Clip ID in the timeline, the first clip is 1, the last clip is a special value, -1.
        """
        if clip_id == -1:
            self._send('goto: clip id: end')
        elif clip_id == 0:
            self._send('goto: clip id: start')
        else:
            self._send(f'goto: clip id: {clip_id}')

    def move_between_clips(self, count: int) -> None:
        """Place timeline playhead at the start of a clip a relative number of clips away from the current clip.

        Parameters
        ----------
        count : int
            Number of clips to move, positive is forward in time, negative is backwards in time.
        """
        if count > 0:
            self._send(f'goto: clip id: +{count}')
        else:
            count *= -1
            self._send(f'goto: clip id: -{count}')

    def go_within_clip(self, frame: int) -> None:
        """Place the timeline playhead at a specific frame within the current clip.

        Parameters
        ----------
        frame : int
            The frame number to place the playhead at, the first frame of the clip is frame 1, the last frame is a special value, -1.
        """
        if frame < 0:
            self._send('goto: clip: end')
        elif frame == 0:
            self._send('goto: clip: start')
        else:
            self._send(f'goto: clip: {frame}')

    def move_within_clip(self, frames: int) -> None:
        """Place the timeline playhead a number of frames offset from it's current position within the current clip.

        Parameters
        ----------
        frames : int
            Number of frames to move the playhead, positive is forward in time, negative is backward in time.
        """
        if frames > 0:
            self._send(f'goto: clip: +{frames}')
        else:
            frames *= -1
            self._send(f'goto: clip: -{frames}')
    
    def go_within_timeline(self, frame: int) -> None:
        """Place the timeline playhead at a specific frame on the timeline.

        Parameters
        ----------
        frame : int
            The frame number to place the playhead at, the first frame of the timeline is frame 1, the last frame is a special value, -1.
        """
        if frame < 0:
            self._send('goto: timeline: end')
        elif frame == 0:
            self._send('goto: timeline: start')
        else:
            self._send(f'goto: timeline: {frame}')
    
    def move_within_timeline(self, frames: int) -> None:
        """Place the timeline playhead a number of frames offset from it's current position .

        Parameters
        ----------
        frames : int
            Number of frames to move the playhead, positive is forward in time, negative is backward in time.
        """
        if frames > 0:
            self._send(f'goto: timeline: +{frames}')
        else:
            frames *= -1
            self._send(f'goto: timeline: -{frames}')

    def go_to_timecode(self, timecode: str) -> None:
        """Place the timeline playhead at a specific timecode.

        Parameters
        ----------
        timecode : str
            Timecode to place the playhead at, the timeline starts at 00:00:00:00.
        """
        self._send(f'goto: timecode: {timecode}')
    
    def move_timecode(self, timecode: str, reverse: bool = False) -> None:
        """Move the timeline playhead a duration from it's current position

        Parameters
        ----------
        timecode : str
            Timecode duration to move playhead, 00:00:00:00 would indicate no movement.
        reverse : bool, optional
            If true, move the playhead backward in time, by default False (forward in time)
        """
        if reverse:
            self._send(f'goto: timecode: -{timecode}')
        else:
            self._send(f'goto: timecode: +{timecode}')
    
    def shuttle(self, speed: int) -> None:
        """Shuttle the playhead along the timeline.

        Parameters
        ----------
        speed : int
            Speed (as a percentage of time) at which the playhead will move, most Hyperdeck models support values between -5000 and 5000.
        """
        self._send(f'shuttle: speed: {speed}')

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

    def select_slot(self, slot_id: int) -> None:
        """Change the active media slot.

        Parameters
        ----------
        slot_id : int
            ID of the slot to be selected as active
        """
        self._send(f'slot select: slot id: {slot_id}')

    def format(self) -> None:
        """Format the active slot to exFAT, this will delete all data on the media in that slot.
        """        
        self._send('format: prepare: exFAT')

    def reboot(self) -> None:
        """Reboot the Hyperdeck, reconnection happens automatically.
        """
        self._send('reboot')
    