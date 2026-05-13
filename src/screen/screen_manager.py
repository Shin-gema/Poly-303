# screen_manager.py

from board import SCL, SDA
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont


class ScreenManager:
    def __init__(self, width=128, height=32, i2c_address=0x3C):
        self.width = width
        self.height = height

        i2c = busio.I2C(SCL, SDA)
        self.display = adafruit_ssd1306.SSD1306_I2C(width, height, i2c, addr=i2c_address)

        self.image = Image.new("1", (width, height))
        self.draw = ImageDraw.Draw(self.image)

        try:
            self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            self.font = ImageFont.load_default()

        self._scenes: dict[str, callable] = {}
        self._current_scene: str | None = None
        self._on_enter: dict[str, callable] = {}
        self._on_exit:  dict[str, callable] = {}

    # ── Scènes ────────────────────────────────────────────────────────────────

    def register_scene(self, name: str, draw_fn, on_enter=None, on_exit=None):
        """Enregistre une scène. draw_fn(sm) est appelée à chaque render."""
        self._scenes[name] = draw_fn
        if on_enter:
            self._on_enter[name] = on_enter
        if on_exit:
            self._on_exit[name] = on_exit

    def set_scene(self, name: str):
        if name not in self._scenes:
            raise KeyError(f"Scène inconnue : {name}")

        if self._current_scene and self._current_scene in self._on_exit:
            self._on_exit[self._current_scene](self)

        self._current_scene = name

        if name in self._on_enter:
            self._on_enter[name](self)

    def render(self):
        if self._current_scene is None:
            return
        self.clear()
        self._scenes[self._current_scene](self)
        self._flush()

    # ── Primitives ────────────────────────────────────────────────────────────

    def clear(self):
        self.image = Image.new("1", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)

    def text(self, x, y, content, fill=1):
        self.draw.text((x, y), str(content), fill=fill, font=self.font)

    def line(self, x1, y1, x2, y2, fill=1):
        self.draw.line((x1, y1, x2, y2), fill=fill)
    
    def vline(self, x, y1, y2, fill=1):
        self.draw.line((x, y1, x, y2), fill=fill)

    def rect(self, x1, y1, x2, y2, fill=1):
        self.draw.rectangle((x1, y1, x2, y2), outline=fill)

    def _flush(self):
        self.display.image(self.image)
        self.display.show()