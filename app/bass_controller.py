"""Routing and internal controls for the Bass Liner CMD LC-1 zone."""

from __future__ import annotations

import mido

from app.bassline import BassLineGenerator


class BassController:
    INPUT_CHANNEL = 7          # MIDI channel 8 as shown to the user.
    BASS_CHANNEL = 8           # MIDI channel 9 as shown to the user.

    RESERVED_ENCODERS = {16, 20}
    STEP_ENCODER_CC = 16
    STEP_VALUES = (1, 2, 4, 8, 16)
    ENCODER_TICKS_PER_CHANGE = 5
    TOGGLE_GENERATOR_NOTE = 16
    REGENERATE_NOTE = 20
    NOTE_BUTTONS = (32, 36, 40, 44, 48, 52, 56, 60)
    OCTAVE_DOWN_NOTE = 64
    OCTAVE_UP_NOTE = 68
    RESERVED_NOTE = 72

    # Eight physical buttons mapped as C D E F G A B C.
    NOTE_OFFSETS = (0, 2, 4, 5, 7, 9, 11, 12)

    def __init__(self, generator: BassLineGenerator, send_bass, on_state_change=None) -> None:
        self.generator = generator
        self.send_bass = send_bass
        self.on_state_change = on_state_change
        self.octave = 2
        self.active_notes: dict[int, int] = {}
        self.step_index = self.STEP_VALUES.index(16)
        self.step_encoder_accumulator = 0

    def process(self, message: mido.Message) -> bool:
        """Return True when the message belongs to the reserved Bass Liner zone."""
        if not hasattr(message, "channel") or message.channel != self.INPUT_CHANNEL:
            return False

        if message.type == "control_change" and message.control in self.RESERVED_ENCODERS:
            if message.control == self.STEP_ENCODER_CC:
                self._handle_step_encoder(message.value)
            return True

        if message.type not in ("note_on", "note_off"):
            return False

        note = message.note
        pressed = message.type == "note_on" and message.velocity > 0

        if note == self.TOGGLE_GENERATOR_NOTE:
            if pressed:
                if self.generator.enabled:
                    self.generator.disarm()
                else:
                    self.generator.arm()
                self._notify()
            return True

        if note == self.REGENERATE_NOTE:
            if pressed:
                self.generator.regenerate()
                self._notify()
            return True

        if note == self.OCTAVE_DOWN_NOTE:
            if pressed:
                self.octave = max(0, self.octave - 1)
                self._retune_generator()
                self._notify()
            return True

        if note == self.OCTAVE_UP_NOTE:
            if pressed:
                self.octave = min(8, self.octave + 1)
                self._retune_generator()
                self._notify()
            return True

        if note == self.RESERVED_NOTE:
            return True

        if note in self.NOTE_BUTTONS:
            self._handle_note_button(message, pressed)
            return True

        return False

    def _handle_step_encoder(self, value: int) -> None:
        if value == 65:
            self.step_encoder_accumulator += 1
        elif value == 63:
            self.step_encoder_accumulator -= 1
        else:
            return

        if self.step_encoder_accumulator >= self.ENCODER_TICKS_PER_CHANGE:
            if self.step_index < len(self.STEP_VALUES) - 1:
                self.step_index += 1
                self.generator.set_steps_per_bar(self.STEP_VALUES[self.step_index])
                self._notify()
            self.step_encoder_accumulator = 0

        elif self.step_encoder_accumulator <= -self.ENCODER_TICKS_PER_CHANGE:
            if self.step_index > 0:
                self.step_index -= 1
                self.generator.set_steps_per_bar(self.STEP_VALUES[self.step_index])
                self._notify()
            self.step_encoder_accumulator = 0

    def _handle_note_button(self, message: mido.Message, pressed: bool) -> None:
        index = self.NOTE_BUTTONS.index(message.note)

        if pressed:
            midi_note = self._mapped_note(index)
            self.active_notes[message.note] = midi_note

            self.send_bass(
                mido.Message(
                    "note_on",
                    channel=self.BASS_CHANNEL,
                    note=midi_note,
                    velocity=message.velocity,
                )
            )

            self.generator.set_root(midi_note, channel=self.BASS_CHANNEL)
            self._notify()
            return

        midi_note = self.active_notes.pop(message.note, self._mapped_note(index))
        self.send_bass(
            mido.Message(
                "note_off",
                channel=self.BASS_CHANNEL,
                note=midi_note,
                velocity=0,
            )
        )

    def _mapped_note(self, index: int) -> int:
        # MIDI C-1 = 0, therefore C2 = 36.
        base_c = (self.octave + 1) * 12
        return max(0, min(127, base_c + self.NOTE_OFFSETS[index]))

    def _retune_generator(self) -> None:
        if self.generator.seed_note is None:
            return

        # Keep the currently selected pitch class and move it to the new octave.
        pitch_class = self.generator.seed_note % 12
        base_c = (self.octave + 1) * 12
        self.generator.set_root(base_c + pitch_class, channel=self.BASS_CHANNEL)

    def _notify(self) -> None:
        if self.on_state_change is not None:
            self.on_state_change(self.state)

    @property
    def state(self) -> dict[str, object]:
        return {
            "generator_enabled": self.generator.enabled,
            "octave": self.octave,
            "root": self.generator.seed_note,
            "steps": self.generator.steps_per_bar,
        }
