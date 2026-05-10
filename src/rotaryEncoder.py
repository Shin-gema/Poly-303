from enum import Enum

from gpiozero import RotaryEncoder, Button
import signal

class enum (Enum):
    BLOCK = 1
    CONTINUOUS = 2

class Encoder:
    def __init__(self, clk_pin, dt_pin, sw_pin, min_position=0, max_position=100):
        self.encoder = RotaryEncoder(a=clk_pin, b=dt_pin, wrap=False, max_steps=1000)
        self.button = Button(sw_pin, pull_up=True, bounce_time=0.05)
        self.position = 0

        self.encoder.when_rotated = self.rotate
        self.button.when_pressed = self.clic
        self.button.when_released = self.release
        self._rotate_callback = None
        self._click_callback = None
        self._release_callback = None

        self.min_position = min_position
        self.max_position = max_position
        self.mode = enum.BLOCK

    def set_range(self, min_position: int, max_position: int, mode: enum = None, sync_position: int | None = None):
        self.min_position = int(min_position)
        self.max_position = int(max_position)

        if mode is not None:
            self.mode = mode

        target = self.position if sync_position is None else int(sync_position)

        if target < self.min_position:
            target = self.min_position

        if target > self.max_position:
            if self.mode == enum.CONTINUOUS:
                span = self.max_position - self.min_position + 1
                if span > 0:
                    target = ((target - self.min_position) % span) + self.min_position
                else:
                    target = self.min_position
            else:
                target = self.max_position
        self.position = target

        try:
            self.encoder.steps = target
        except Exception:
            pass

    def set_position(self, position: int):
        pos = int(position)
        if pos < self.min_position:
            pos = self.min_position
        if pos > self.max_position:
            if self.mode == enum.CONTINUOUS:
                span = self.max_position - self.min_position + 1
                if span > 0:
                    pos = ((pos - self.min_position) % span) + self.min_position
                else:
                    pos = self.min_position
            else:
                pos = self.max_position
        self.position = pos
        try:
            self.encoder.steps = pos
        except Exception:
            pass

    def rotate(self):
        self.position = self.encoder.steps
        if self.position < self.min_position:
            if self.mode == enum.CONTINUOUS:
                self.position = self.max_position
                self.encoder.steps = self.max_position
            else:
                self.position = self.min_position
                self.encoder.steps = self.min_position
        elif self.position > self.max_position:
            if self.mode == enum.CONTINUOUS:
                self.position = self.min_position
                self.encoder.steps = self.min_position
            else:
                self.position = self.max_position
                self.encoder.steps = self.max_position
        if self._rotate_callback:
            self._rotate_callback(self.position)

    def clic(self):
        if self._click_callback:
            self._click_callback(self.position)

    def release(self):
        if self._release_callback:
            self._release_callback(self.position)

    def on_rotate(self, callback):
        self._rotate_callback = callback

    def on_click(self, callback):
        self._click_callback = callback
    
    def on_release(self, callback):
        self._release_callback = callback



if __name__ == "__main__":
  
  # Pins
  clk = 17
  dt = 18
  sw = 27

  encoder = Encoder(clk, dt, sw)

  encoder.on_click(lambda pos: print(f"Clic ! callback pos : {pos}"))
  encoder.on_rotate(lambda pos: print(f"Rotation callback ! pos : {pos}"))

  print("Encoder ready. Rotate or click the encoder to see the callbacks in action.")
  signal.pause()  # wait indefinitely until a signal is received (like Ctrl+C)