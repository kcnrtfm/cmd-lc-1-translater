"""MIDI ports and passthrough; independent from the terminal UI."""

from collections.abc import Callable
from threading import RLock

import mido

MessageHandler = Callable[[mido.Message], None]
MessageProcessor = Callable[[mido.Message], mido.Message]


class MidiRouter:
    def __init__(self, on_input: MessageHandler, on_output: MessageHandler, processor: MessageProcessor | None = None) -> None:
        self.on_input = on_input
        self.on_output = on_output
        self.processor = processor
        self._input = None
        self._output = None
        self._lock = RLock()

    @staticmethod
    def input_ports() -> list[str]:
        return mido.get_input_names()

    @staticmethod
    def output_ports() -> list[str]:
        return mido.get_output_names()

    def connect(self, input_name: str, output_name: str) -> None:
        self.disconnect()
        output_port = mido.open_output(output_name)
        try:
            input_port = mido.open_input(input_name, callback=self._handle_message)
        except Exception:
            output_port.close()
            raise
        with self._lock:
            self._output = output_port
            self._input = input_port

    def _handle_message(self, message: mido.Message) -> None:
        with self._lock:
            if self._output is None:
                return
            self.on_input(message.copy())
            output_message = self.processor(message.copy()) if self.processor else message.copy()
            self._output.send(output_message)
            self.on_output(output_message.copy())

    def disconnect(self) -> None:
        with self._lock:
            input_port, output_port = self._input, self._output
            self._input = None
            self._output = None
        if input_port is not None:
            input_port.close()
        if output_port is not None:
            output_port.close()

    @property
    def connected(self) -> bool:
        with self._lock:
            return self._input is not None and self._output is not None
