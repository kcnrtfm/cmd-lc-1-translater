"""MIDI message transformations."""

import mido


class RelativeEncoderToAbsolute:
    def __init__(
        self,
        channel: int = 7,
        controls: range = range(16, 24),
        initial_value: int = 64,
    ) -> None:
        self.enabled = False
        self.channel = channel
        self.controls = set(controls)
        self.values = {control: float(initial_value) for control in self.controls}
        self.steps_for_full_range = 18
        self.step_size = 127 / self.steps_for_full_range

    def process(self, message: mido.Message) -> mido.Message:
        if not self.enabled:
            return message

        if (
            message.type != "control_change"
            or message.channel != self.channel
            or message.control not in self.controls
        ):
            return message

        if message.value == 65:
            delta = 1
        elif message.value == 63:
            delta = -1
        else:
            return message

        current = self.values[message.control]
        current = max(0.0, min(127.0, current + (delta * self.step_size)))
        self.values[message.control] = current

        return message.copy(value=round(current))


class EncoderStepCounter:
    def __init__(self, channel: int = 7, controls: range = range(16, 24)) -> None:
        self.enabled = False
        self.channel = channel
        self.controls = set(controls)
        self.count = 0

    def process(self, message: mido.Message) -> int:
        if not self.enabled:
            return self.count
        if (
            message.type == "control_change"
            and message.channel == self.channel
            and message.control in self.controls
            and message.value in (63, 65)
        ):
            self.count += 1
        return self.count

    def reset(self) -> None:
        self.count = 0
