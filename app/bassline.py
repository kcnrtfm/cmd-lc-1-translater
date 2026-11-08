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

        self.seed_note = message.note
        self.channel = message.channel
        self.pattern = self._generate_pattern(message.note)
        self.waiting_seed = False
        self.start_loop()
        return True

    def _generate_pattern(self, root: int) -> list[int | None]:
        pool = [root + interval for interval in self.SCALE_INTERVALS if root + interval <= 127]
        pattern: list[int | None] = []

        for step in range(self.STEPS):
            if step == 0:
                pattern.append(root)
                continue

            if random.random() < 0.42:
                pattern.append(None)
                continue

            if random.random() < 0.50:
                pattern.append(root)
            else:
                pattern.append(random.choice(pool))

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
