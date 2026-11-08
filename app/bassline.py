"""Bass line generation synchronized exclusively to MIDI Clock."""

from __future__ import annotations

import random

import mido


class BassLineGenerator:
    STEPS = 16
    CLOCKS_PER_STEP = 6  # MIDI Clock is 24 PPQN; six clocks = one sixteenth note.
    NOTE_OFF_CLOCK = 4

    SCALE_INTERVALS = (0, 3, 5, 7, 10)

    def __init__(self, send_message) -> None:
        self.send_message = send_message
        self.enabled = False
        self.waiting_seed = False
        self.seed_note: int | None = None
        self.pattern: list[int | None] = []
        self.pattern_offsets: list[int | None] = []
        self.channel = 0

        self.transport_running = False
        self.step_index = 0
        self.clock_in_step = 0
        self.active_note: int | None = None

    def arm(self) -> None:
        self.enabled = True
        self.waiting_seed = self.seed_note is None

    def disarm(self) -> None:
        self.enabled = False
        self.waiting_seed = False
        self._note_off()

    def accept_seed(self, message: mido.Message) -> bool:
        if (
            not self.enabled
            or message.type != "note_on"
            or message.velocity == 0
        ):
            return False

        self.channel = message.channel

        if self.seed_note is None or not self.pattern_offsets:
            self.pattern_offsets = self._generate_pattern_offsets()

        self.seed_note = message.note
        self.pattern = self._transpose_pattern(self.seed_note)
        self.waiting_seed = False
        return True

    def process_transport(self, message: mido.Message) -> None:
        if message.type == "start":
            self.transport_running = True
            self.step_index = 0
            self.clock_in_step = 0
            self._note_off()
            return

        if message.type == "continue":
            self.transport_running = True
            return

        if message.type == "stop":
            self.transport_running = False
            self._note_off()
            return

        if message.type != "clock" or not self.transport_running:
            return

        if not self.enabled or not self.pattern:
            return

        if self.clock_in_step == 0:
            self._play_current_step()

        self.clock_in_step += 1

        if self.clock_in_step == self.NOTE_OFF_CLOCK:
            self._note_off()

        if self.clock_in_step >= self.CLOCKS_PER_STEP:
            self.clock_in_step = 0
            self.step_index = (self.step_index + 1) % self.STEPS

    def _generate_pattern_offsets(self) -> list[int | None]:
        pattern: list[int | None] = []

        for step in range(self.STEPS):
            if step == 0:
                pattern.append(0)
                continue

            if random.random() < 0.42:
                pattern.append(None)
                continue

            if random.random() < 0.50:
                pattern.append(0)
            else:
                pattern.append(random.choice(self.SCALE_INTERVALS))

        return pattern

    def _transpose_pattern(self, root: int) -> list[int | None]:
        pattern: list[int | None] = []
        for offset in self.pattern_offsets:
            if offset is None:
                pattern.append(None)
            else:
                pattern.append(max(0, min(127, root + offset)))
        return pattern

    def _play_current_step(self) -> None:
        self._note_off()
        note = self.pattern[self.step_index]
        if note is None:
            return

        self.active_note = note
        self.send_message(
            mido.Message(
                "note_on",
                channel=self.channel,
                note=note,
                velocity=100,
            )
        )

    def _note_off(self) -> None:
        if self.active_note is None:
            return

        self.send_message(
            mido.Message(
                "note_off",
                channel=self.channel,
                note=self.active_note,
                velocity=0,
            )
        )
        self.active_note = None
