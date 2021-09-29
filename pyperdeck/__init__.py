from telnetlib import Telnet
from threading import Thread
from typing import Tuple

class Hyperdeck:
    def __init__(self, ip: str) -> None:
        self.connection = Telnet(ip, 9993)

        self._reader_thread = Thread(target=self._reader)
        self._reader_thread.start()

        self.timecode = 'HH:MM:SS:FF'
    
    def _reader(self) -> None:
        while True:
            message = self.connection.read_until(bytes('\r\n\r\n', 'utf-8'))
            self._decode_message(message)
    
    def _send(self, command: str) -> None:
        self.connection.write(bytes(command + '\r\n', 'utf-8'))
    
    def _decode_message(self, message: bytes) -> None:
        msg = message.decode('utf-8').rstrip('\r\n\r\n')
        lines = msg.split('\r\n')
        status = self._get_status_of_message(lines[0])
        body = lines[1:]
        print(status)
        print(body)
        
    def _get_status_of_message(self, status_line: str) -> Tuple[int, str]:
        blocks = status_line.rstrip(':').split(' ', maxsplit=1)
        status = int(blocks[0])
        response = blocks[1]
        return status, response
