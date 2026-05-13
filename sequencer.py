
from dataclasses import dataclass
import threading
import time
from enum import Enum

from instrument.instrument import Instrument

NOTE_NAMES = ["C", "C%", "D", "D%", "E", "F", "F%", "G", "G%", "A", "A%", "B"]

TRACK_COLORS = [
    (255, 0,   0),    # Rouge   — cercle 1
    (0,   200, 255),  # Cyan    — cercle 2
    (255, 180, 0),    # Jaune   — cercle 3
    (180, 0,   255),  # Violet  — cercle 4
]

NEEDLE_COLOR  = (0, 255, 0)   # Vert — aiguille

class mode (Enum):
    SEQUENCE = 0
    NOTE_SELECTION = 1
    NOTE_EDITING = 2
    INSTRUMENT_EDITING = 3

@dataclass
class track:
    division: int
    mute: bool
    pattern: list[int]
    velocity: int
    _counter: float = 0.0
    current_step: int = 0


class sequencer:
    def __init__(self):
        self.tracks = [track(division=4, mute=False, pattern=[36, 36, 43, 41], velocity=100), *[track(division=0, mute=False, pattern=[], velocity=100) for _ in range(3)]]
        self.current_track = 0
        self.current_step = 0
        self.bpm = 120
        self.volume = 100
        self.is_playing = False
        self._tick_thread = None
        self._stop_event = threading.Event()
        self.pixel = None                   # PixelRing à définir dans main.py
        self.sequence_length = 16           # Nombre de steps dans la séquence
        self.mode = mode.SEQUENCE
        self.instrument: Instrument | None = None

        self.selected_note = 0
        self.frequency_target = "bpm"
        self._last_step = None              # Garder en mémoire la dernière étape affichée
        self._last_division = None          # Garder en mémoire la dernière division affichée

        if self._tick_thread is None or not self._tick_thread.is_alive():
            self._stop_event.clear()
            self._tick_thread = threading.Thread(target=self._timing_loop, daemon=True)
            self._tick_thread.start()

    def midi_note_to_name(self, value):
        if value is None:
            return "-"
        midi_value = max(0, min(127, int(value)))
        note_name = NOTE_NAMES[midi_value % 12]
        octave = (midi_value // 12) - 1
        return f"{note_name}{octave}"

    def _update_division_pixels(self):
        division = self.tracks[self.current_track].division
        if division == 0:
            self.pixel.clear()
            return
        
        active_positions = set()
        
        color = TRACK_COLORS[self.current_track % len(TRACK_COLORS)]

        for i in range(division):
            position = (i * self.sequence_length) // division
            active_positions.add(position)
            intensity = self.mode != mode.SEQUENCE and 0.1 or 1.0
            if (self.mode != mode.SEQUENCE and self.selected_note == i):
                continue  
            self.pixel.set_pixel(position, tuple(int(c * intensity) for c in color))

        if self.mode == mode.SEQUENCE and self.is_playing:
            current_pixel = self.current_step % self.sequence_length
            active_positions.add(current_pixel)
            self.pixel.set_pixel(current_pixel, NEEDLE_COLOR)

        if self.mode == mode.NOTE_SELECTION and self.selected_note is not None:
            selected_pixel = (self.selected_note * self.sequence_length) // division
            self.pixel.set_blink(color, selected_pixel, 2.0)

        if self.mode == mode.NOTE_EDITING and self.selected_note is not None:
            selected_pixel = (self.selected_note * self.sequence_length) // division
            active_positions.add(selected_pixel)
            self.pixel.set_pixel(selected_pixel, color) 
        
        for i in range(self.sequence_length):
            if i not in active_positions:
                self.pixel.set_pixel(i, (0, 0, 0))

    def on_division_rotate(self, position):
        self.tracks[self.current_track].division = position
        if self.tracks[self.current_track].pattern is None:
            self.tracks[self.current_track].pattern = [60] * position
        elif len(self.tracks[self.current_track].pattern) < position:
            self.tracks[self.current_track].pattern.extend([60] * (position - len(self.tracks[self.current_track].pattern)))
        elif len(self.tracks[self.current_track].pattern) > position:
            self.tracks[self.current_track].pattern = self.tracks[self.current_track].pattern[:position]

        print(f"Division changed to: {position}")

    def on_selection_rotate(self, position):
        if self.tracks[self.current_track].division == 0:
            return
        
        self.selected_note = position % self.tracks[self.current_track].division
        print(f"selected note : {self.selected_note}")

    def on_edit_rotate(self, position):
        if self.selected_note is None or self.tracks[self.current_track].division == 0:
            return
        
        pattern = self.tracks[self.current_track].pattern
        if not pattern:
            pattern = [0] * self.tracks[self.current_track].division
            self.tracks[self.current_track].pattern = pattern

        pattern[self.selected_note % len(pattern)] = position % 128
        print(f"edited note : {self.selected_note} value : {pattern[self.selected_note % len(pattern)]}")
    
    def on_frequency_rotate(self, position):
        if self.frequency_target == "volume":
            self.volume = max(0, min(100, position))
            print(f"Volume changed to: {self.volume}")
            return

        self.bpm = max(30, min(300, position * 2 + 30))  # 30-300 BPM
        print(f"BPM changed to: {self.bpm}")

    def on_velocity_rotate(self, position):
        self.tracks[self.current_track].velocity = max(1, min(100, position))
        print(f"Velocity changed to: {self.tracks[self.current_track].velocity}")
    
    def on_division_click(self, position):
        if self.mode == mode.NOTE_SELECTION and self.selected_note is not None:
            self.mode = mode.NOTE_EDITING
            return
        
        if self.mode == mode.NOTE_EDITING:
            self.mode = mode.NOTE_SELECTION
    
    def on_frequency_click(self, position):
        self.frequency_target = "volume" if self.frequency_target == "bpm" else "bpm"

    def play(self):
        self.is_playing = True
        
    def pause(self):
        self.is_playing = False
        if self.instrument and hasattr(self.instrument, "stop_all"):
            self.instrument.stop_all()

    def stop(self):
        self.is_playing = False
        self._stop_event.set()

        if self.instrument and hasattr(self.instrument, "stop_all"):
            self.instrument.stop_all()

        if self._tick_thread:
            self._tick_thread.join(timeout=1)

    def _timing_loop(self):
        while not self._stop_event.is_set():
            t_start = time.perf_counter()

            if self.pixel:
                self._update_division_pixels()

            step_duration = (60.0 / self.bpm) * 4 / self.sequence_length
            if self.is_playing:
                self.tick(step_duration)

            elapsed = time.perf_counter() - t_start
            sleep_time = max(0.0, step_duration - elapsed)
            time.sleep(sleep_time)

    def tick(self, step_duration):
        if not self.is_playing:
            return

        playback_volume = self.volume / 100.0

        for track in self.tracks:
            if track.mute or track.division <= 0 or not track.pattern:
                continue

            interval = self.sequence_length / track.division

            if not hasattr(track, '_counter'):
                track._counter = 0.0

            track._counter += 1.0
            if track._counter >= interval:
                track._counter -= interval

                midi_note = track.pattern[track.current_step % len(track.pattern)]
                track.current_step += 1

                if midi_note <= 0:
                    continue

                note_duration = step_duration * interval * 0.9

                if self.instrument:
                    self.instrument.play_note(
                        midi_note=midi_note,
                        velocity=track.velocity,
                        duration=note_duration,
                        volume=playback_volume,
                    )

        self.current_step = (self.current_step + 1) % self.sequence_length

if __name__ == "__main__":
    seq = sequencer()
    seq.bpm = 120
    seq.play()
    
    try:
        time.sleep(4)
    except KeyboardInterrupt:
        pass
    finally:
        seq.stop()
