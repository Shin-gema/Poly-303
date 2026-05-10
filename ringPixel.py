# Simple test for NeoPixels on Raspberry Pi
import time
import board
import neopixel

ORDER = neopixel.GRB

class PixelRing:
    def __init__(self, pixel_pin, num_pixels, brightness=0.2, auto_write=False, pixel_order=ORDER):
        self.pixels = neopixel.NeoPixel(
            pixel_pin, num_pixels, brightness=brightness, auto_write=auto_write, pixel_order=pixel_order
        )
        self.num_pixels = num_pixels
        self.pixel_state = [(0, 0, 0) for _ in range(num_pixels)]
        self._blink_state = {}

    def fill(self, color):
        self.pixel_state = [color for _ in range(self.num_pixels)]
        self.pixels.fill(color)
        self.pixels.show()

    def set_pixel(self, index, color):
        if index < 0 or index >= self.num_pixels:
            return
        
        if self.pixel_state[index] != color:
            self.pixel_state[index] = color
            self.pixels[index] = color
            self.pixels.show()

    def set_blink(self, color, index, frequency):
        if index < 0 or index >= self.num_pixels:
            return

        if frequency <= 0:
            self._blink_state.pop(index, None)
            self.set_pixel(index, (0, 0, 0))
            return

        now = time.monotonic()
        half_period = 1.0 / (2.0 * frequency)

        state = self._blink_state.get(index)
        if (
            state is None
            or state["color"] != color
            or state["frequency"] != frequency
        ):
            state = {
                "color": color,
                "frequency": frequency,
                "last_toggle": now,
                "is_on": True,
            }
            self._blink_state[index] = state
            self.set_pixel(index, color)
            return

        if now - state["last_toggle"] >= half_period:
            state["is_on"] = not state["is_on"]
            state["last_toggle"] = now

        self.set_pixel(index, state["color"] if state["is_on"] else (0, 0, 0))

    def clear(self):
        self.fill((0, 0, 0))

if __name__ == "__main__":

    pixel_pin = board.D21
    num_pixels = 16

    ring = PixelRing(pixel_pin, num_pixels)
    try:
        while True:
            for i in range(num_pixels):
                ring.set_pixel(i, (255, 0, 0))  # Red
                time.sleep(0.1)
                ring.set_pixel(i, (0, 255, 0))  # Green
                time.sleep(0.1)
                ring.set_pixel(i, (0, 0, 255))  # Blue
                time.sleep(0.1)
                ring.set_pixel(i, (0, 0, 0))  # Off
    except KeyboardInterrupt:
        ring.clear()  # Turn off all pixels on exit
