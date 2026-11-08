"""Bass line generation and looping."""

from __future__ import annotations

import random
import threading
import time

import mido


class BassLineGenerator:
    BPM = 120
    STEPS = 16
    STEP_SECONDS = 60.0 / BPM / 4.0  # sixteenth notes

    # Minor pentatonic intervals keep random output constrained and usable.
    SCALE_INTERVALS = (0, 3, 5, 7, 10)

    def __init__(self, send_message) -> None:
        self.send_message = send_message
        self.enabled = False
        self.waiting_seed = False
        self.seed_note: int | None = None
        self.pattern: list[int | None] = []
        self.pattern_offsets: list[int | None] = []
        self.channel = 0
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def arm(self) -> None:
        self.enabled = True
        self.waiting_seed = True
        self.stop_loop()

    def disarm(self) -> None:
        self.enabled = False
        self.waiting_seed = False
        self.stop_loop()

    def accept_seed(self, message: mido.Message) -> bool:
        if (
            not self.enabled
            or not self.waiting_seed
            or message.type != "note_on"
            or message.velocity == 0
        ):
            return False

        self.channel = message.channel

        if self.seed_note is None or not self.pattern_offsets:
            self.seed_note = message.note
            self.pattern_offsets = self._generate_pattern_offsets()
        else:
            self.seed_note = message.note

        self.pattern = self._transpose_pattern(self.seed_note)
        self.waiting_seed = False

        if self._thread is None or not self._thread.is_alive():
            self.start_loop()

        return True

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

    def start_loop(self) -> None:
        self.stop_loop()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop_loop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=0.5)

    def _run_loop(self) -> None:
        note_length = self.STEP_SECONDS * 0.72

        while not self._stop_event.is_set():
            for note in self.pattern:
                if self._stop_event.is_set():
                    return

                started = time.monotonic()

                if note is not None:
                    self.send_message(
                        mido.Message(
                            "note_on",
                            channel=self.channel,
                            note=note,
                            velocity=100,
                        )
                    )

                elapsed = time.monotonic() - started
                self._stop_event.wait(max(0.0, note_length - elapsed))

                if note is not None and not self._stop_event.is_set():
                    self.send_message(
                        mido.Message(
                            "note_off",
                            channel=self.channel,
                            note=note,
                            velocity=0,
                        )
                    )

                remaining = self.STEP_SECONDS - note_length
                self._stop_event.wait(max(0.0, remaining))
