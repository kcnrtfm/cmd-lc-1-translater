"""Four-bar psycore / psytrance rolling bass generator synchronized to MIDI Clock."""

from __future__ import annotations

import random

import mido


class PsycoreBassLineGenerator:
    BARS = 4
    STEPS_PER_BAR = 16
    TOTAL_STEPS = BARS * STEPS_PER_BAR
    CLOCKS_PER_STEP = 6
    NOTE_OFF_CLOCK = 4

    def __init__(self, send_message) -> None:
        self.send_message = send_message
        self.enabled = False
        self.waiting_seed = False
        self.seed_note: int | None = None
        self.pattern_offsets: list[int | None] = []
        self.pattern: list[int | None] = []
        self.channel = 8

        self.transport_running = False
        self.step_index = 0
        self.clock_in_step = 0
        self.active_note: int | None = None

    @property
    def steps_per_bar(self) -> int:
        return self.STEPS_PER_BAR

    def set_steps_per_bar(self, steps: int) -> None:
        # Psycore mode intentionally stays at 16 sixteenth-note steps per bar.
        return

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

        if not self.transport_running:
            self.transport_running = True
            self.step_index = 0
            self.clock_in_step = 0

        if self.clock_in_step == 0:
            self._play_current_step()

        self.clock_in_step += 1

        if self.clock_in_step == self.NOTE_OFF_CLOCK:
            self._note_off()

        if self.clock_in_step >= self.CLOCKS_PER_STEP:
            self.clock_in_step = 0
            self.step_index = (self.step_index + 1) % self.TOTAL_STEPS

    def _generate_pattern_offsets(self) -> list[int | None]:
        pattern: list[int | None] = []

        # First three bars: strict rolling bass.
        for step in range(self.TOTAL_STEPS):
            position_in_beat = step % 4
            if position_in_beat == 0:
                pattern.append(None)
            else:
                pattern.append(0)

        # Fourth bar: keep the K-B-B-B pulse but add one restrained variation.
        last_bar_start = 3 * self.STEPS_PER_BAR
        bass_positions = [
            step
            for step in range(last_bar_start, self.TOTAL_STEPS)
            if step % 4 != 0
        ]

        variation_step = random.choice(bass_positions)
        pattern[variation_step] = random.choice((7, 12))

        # Optional single dropout in the final beat to create a turnaround.
        if random.random() < 0.5:
            final_beat_positions = [61, 62, 63]
            dropout = random.choice(final_beat_positions)
            if dropout != variation_step:
                pattern[dropout] = None

        return pattern

    def _transpose_pattern(self, root: int) -> list[int | None]:
        result: list[int | None] = []
        for offset in self.pattern_offsets:
            if offset is None:
                result.append(None)
            else:
                result.append(max(0, min(127, root + offset)))
        return result

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
