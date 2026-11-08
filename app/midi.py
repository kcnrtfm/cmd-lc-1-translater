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

    def send(self, message: mido.Message) -> None:
        with self._lock:
            if self._output is None:
                return
            self._output.send(message)
            self.on_output(message.copy())

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


class MidiInputListener:
    def __init__(self, on_message: MessageHandler) -> None:
        self.on_message = on_message
        self._input = None
        self._lock = RLock()

    def connect(self, input_name: str) -> None:
        self.disconnect()
        input_port = mido.open_input(input_name, callback=self._handle_message)
        with self._lock:
            self._input = input_port

    def _handle_message(self, message: mido.Message) -> None:
        self.on_message(message.copy())

    def disconnect(self) -> None:
        with self._lock:
            input_port = self._input
            self._input = None
        if input_port is not None:
            input_port.close()

    @property
    def connected(self) -> bool:
        with self._lock:
            return self._input is not None


class DualOutputMidiRouter:
    def __init__(self, on_input: MessageHandler, on_translated_output: MessageHandler, on_bass_output: MessageHandler, processor: MessageProcessor | None = None) -> None:
        self.on_input = on_input
        self.on_translated_output = on_translated_output
        self.on_bass_output = on_bass_output
        self.processor = processor
        self._input = None
        self._translated_output = None
        self._bass_output = None
        self._lock = RLock()
        self.input_handler = None

    @staticmethod
    def input_ports() -> list[str]:
        return mido.get_input_names()

    @staticmethod
    def output_ports() -> list[str]:
        return mido.get_output_names()

    def connect(self, input_name: str, translated_output_name: str, bass_output_name: str) -> None:
        self.disconnect()
        translated = mido.open_output(translated_output_name)
        try:
            bass = mido.open_output(bass_output_name)
        except Exception:
            translated.close()
            raise
        try:
            input_port = mido.open_input(input_name, callback=self._handle_message)
        except Exception:
            translated.close()
            bass.close()
            raise

        with self._lock:
            self._translated_output = translated
            self._bass_output = bass
            self._input = input_port

    def _handle_message(self, message: mido.Message) -> None:
        self.on_input(message.copy())

        consumed = False
        if self.input_handler is not None:
            consumed = bool(self.input_handler(message.copy()))

        if not consumed:
            output_message = self.processor(message.copy()) if self.processor else message.copy()
            self.send_translated(output_message)

    def send_translated(self, message: mido.Message) -> None:
        with self._lock:
            if self._translated_output is None:
                return
            self._translated_output.send(message)
        self.on_translated_output(message.copy())

    def send_bass(self, message: mido.Message) -> None:
        with self._lock:
            if self._bass_output is None:
                return
            self._bass_output.send(message)
        self.on_bass_output(message.copy())

    def disconnect(self) -> None:
        with self._lock:
            input_port = self._input
            translated = self._translated_output
            bass = self._bass_output
            self._input = None
            self._translated_output = None
            self._bass_output = None

        if input_port is not None:
            input_port.close()
        if translated is not None:
            translated.close()
        if bass is not None:
            bass.close()

    @property
    def connected(self) -> bool:
        with self._lock:
            return (
                self._input is not None
                and self._translated_output is not None
                and self._bass_output is not None
            )
