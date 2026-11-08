"""Bass line generation synchronized exclusively to MIDI Clock."""

from __future__ import annotations

import random

import mido


class BassLineGenerator:
    MAX_STEPS = 16
    CLOCKS_PER_BAR = 96  # 24 PPQN * 4 beats

    SCALE_INTERVALS = (0, 3, 5, 7, 10)

    def __init__(self, send_message) -> None:
        self.send_message = send_message
        self.enabled = False
        self.waiting_seed = False
        self.seed_note: int | None = None
        self.pattern: list[int | None] = []
        self.pattern_offsets: list[int | None] = []
        self.channel = 0
        self.steps_per_bar = 16

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

    def set_root(self, note: int, channel: int = 8) -> None:
        self.channel = channel

        if not self.pattern_offsets:
            self.pattern_offsets = self._generate_pattern_offsets()

        self.seed_note = max(0, min(127, note))
        self.pattern = self._transpose_pattern(self.seed_note)
        self.waiting_seed = False

    def regenerate(self) -> None:
        self.pattern_offsets = self._generate_pattern_offsets()
        if self.seed_note is not None:
            self.pattern = self._transpose_pattern(self.seed_note)

    def set_steps_per_bar(self, steps: int) -> None:
        if steps not in (1, 2, 4, 8, 16):
            raise ValueError("steps must be one of 1, 2, 4, 8, 16")

        self.steps_per_bar = steps
        self.step_index %= steps
        self.clock_in_step = 0

    @property
    def clocks_per_step(self) -> int:
        return self.CLOCKS_PER_BAR // self.steps_per_bar

    @property
    def note_off_clock(self) -> int:
        return max(1, round(self.clocks_per_step * 2 / 3))

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

        if message.type != "clock":
            return

        if not self.enabled or not self.pattern:
            return

        # If the program connects while Ableton is already playing, we may
        # receive clocks without having seen the initial START message.
        if not self.transport_running:
            self.transport_running = True
            self.step_index = 0
            self.clock_in_step = 0

        if self.clock_in_step == 0:
            self._play_current_step()

        self.clock_in_step += 1

        if self.clock_in_step == self.note_off_clock:
            self._note_off()

        if self.clock_in_step >= self.clocks_per_step:
            self.clock_in_step = 0
            self.step_index = (self.step_index + 1) % self.steps_per_bar

    def _generate_pattern_offsets(self) -> list[int | None]:
        pattern: list[int | None] = []

        for step in range(self.MAX_STEPS):
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
