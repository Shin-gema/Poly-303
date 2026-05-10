from abc import ABC, abstractmethod
from dataclasses import dataclass
import math
import threading
import time
from typing import Any

import numpy as np
import sounddevice


@dataclass
class NoteEvent:
    midi_note: int
    velocity: int
    duration: float
    channel: int = 0
    volume: float = 1.0
    timestamp: float = 0.0

@dataclass
class Voice:
    midi_note: int = 0
    frequency: float = 0.0
    velocity: int = 0
    volume: float = 0.0
    channel: int = 0
    duration: float = 0.0
    start_time: float = 0.0
    active: bool = False
    phase: float = 0.0

class Instrument(ABC):
    def __init__(self, polyphony: int = 8, sample_rate: int = 44100):
        self.polyphony = max(1, int(polyphony))
        self.sample_rate = max(8000, int(sample_rate))
        self._voices = [Voice() for _ in range(self.polyphony)]
        self._voices_lock = threading.Lock()
        self._stream_lock = threading.Lock()
        self._stream: Any = None
        self._stop_event = threading.Event()
        self._stream_started = False

    @abstractmethod
    def synthesize(self, voice: Voice, phases: np.ndarray) -> np.ndarray:
        pass

    @staticmethod
    def midi_to_frequency(midi_note: int) -> float:
        note = int(max(0, min(127, midi_note)))
        return 440.0 * (2.0 ** ((note - 69) / 12.0))

    def _ensure_stream(self) -> None:

        with self._stream_lock:
            if self._stream_started:
                return

            self._stop_event.clear()
            self._stream = sounddevice.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
                finished_callback=self._stream_finished,
            )
            self._stream.start()
            self._stream_started = True

    def _stream_finished(self) -> None:
        with self._stream_lock:
            self._stream_started = False
            self._stream = None

    def _allocate_voice(self) -> Voice:
        for voice in self._voices:
            if not voice.active:
                return voice

        return min(self._voices, key=lambda voice: voice.start_time)

    def _audio_callback(self, outdata, frames, time_info, status) -> None:
        if status:
            pass

        buffer = np.zeros(frames, dtype=np.float32)
        now = time.time()

        with self._voices_lock:
            for voice in self._voices:
                if not voice.active:
                    continue

                if self._stop_event.is_set() or (now - voice.start_time) >= voice.duration:
                    voice.active = False
                    continue

                velocity_norm = max(0.0, min(1.0, voice.velocity / 127.0))
                amplitude = max(0.0, min(0.95, velocity_norm * voice.volume))
                if amplitude <= 0.0:
                    voice.active = False
                    continue

                phase_increment = 2.0 * math.pi * voice.frequency / self.sample_rate
                phases = voice.phase + phase_increment * np.arange(frames, dtype=np.float32)
                voice_buffer = self.synthesize(voice, phases)
                buffer += amplitude * voice_buffer.astype(np.float32)
                voice.phase = float((voice.phase + phase_increment * frames) % (2.0 * math.pi))

            buffer = np.clip(buffer, -1.0, 1.0)
            outdata[:] = buffer.reshape(-1, 1)

    def play_note(
        self,
        midi_note: int,
        velocity: int,
        duration: float,
        channel: int = 0,
        volume: float = 1.0,
    ) -> None:
        event = NoteEvent(
            midi_note=int(midi_note),
            velocity=int(max(0, min(127, velocity))),
            duration=max(0.0, float(duration)),
            channel=int(max(0, channel)),
            volume=max(0.0, min(1.0, float(volume))),
            timestamp=time.time(),
        )

        if event.velocity <= 0 or event.volume <= 0.0:
            return

        self._ensure_stream()

        with self._voices_lock:
            voice = self._allocate_voice()
            voice.midi_note = event.midi_note
            voice.frequency = self.midi_to_frequency(event.midi_note)
            voice.velocity = event.velocity
            voice.volume = event.volume
            voice.channel = event.channel
            voice.duration = event.duration
            voice.start_time = event.timestamp
            voice.active = True
            voice.phase = 0.0
        print (f"Playing note: MIDI {event.midi_note}, Freq {voice.frequency:.2f} Hz, Vel {event.velocity}, Dur {event.duration:.2f}s, Vol {event.volume:.2f}")

    def stop_all(self) -> None:
        self._stop_event.set()

        with self._voices_lock:
            for voice in self._voices:
                voice.active = False

        stream = None
        with self._stream_lock:
            stream = self._stream
            self._stream = None
            self._stream_started = False

        if stream is not None:
            try:
                stream.abort()
                stream.close()
            except Exception as error:
                print(f"[Instrument] stop error: {error}")
