from board import SCL, SDA
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont


class _SafeFormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


class Scene:
    def __init__(self, name, template=None, variables=None, render_callback=None, on_enter=None, on_exit=None):
        self.name = name
        self.template = template or []
        self.variables = variables or {}
        self.render_callback = render_callback
        self.on_enter = on_enter
        self.on_exit = on_exit

class ScreenManager:
    def __init__(self, width=128, height=32, i2c_address=0x3C):
        self.width = width
        self.height = height
        
        # I2C setup
        i2c = busio.I2C(SCL, SDA)
        self.display = adafruit_ssd1306.SSD1306_I2C(width, height, i2c, addr=i2c_address)
        
        # Image et draw
        self.image = Image.new("1", (width, height))
        self.draw = ImageDraw.Draw(self.image)
        
        # Charger police
        try:
            self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            self.font = ImageFont.load_default()
        
        # Callbacks list
        self.callbacks = {}
        
        self.scenes = {}
        self.current_scene = None
        self.template = None
        self.variables = {}
    
    def register_callback(self, callback):
        self.callbacks[callback.__name__] = callback

    def clear(self):
        self.image = Image.new("1", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
    
    def draw_text(self, x, y, text, fill=1):
        self.draw.text((x, y), text, fill=fill, font=self.font)
    
    def update_display(self):
        self.display.image(self.image)
        self.display.show()
    
    def render(self):
        self.clear()
        
        for key, callback in self.callbacks.items():
            callback(self)
        
        self.update_display()

    def draw_line(self, x1, y1, x2, y2, fill=1):
        self.draw.line((x1, y1, x2, y2), fill=fill)
    
    def draw_rectangle(self, x1, y1, x2, y2, fill=1):
        self.draw.rectangle((x1, y1, x2, y2), outline=fill)
    
    def set_template(self, template_elements):
        self.add_scene("default", template_elements)
        self.set_scene("default")

    def add_scene(self, name, template_elements=None, variables=None, render_callback=None, on_enter=None, on_exit=None):
        self.scenes[name] = Scene(
            name=name,
            template=template_elements,
            variables=variables,
            render_callback=render_callback,
            on_enter=on_enter,
            on_exit=on_exit,
        )
        if self.current_scene is None:
            self.set_scene(name)

    def set_scene(self, name):
        if name not in self.scenes:
            raise KeyError(f"Scene unknown: {name}")

        previous = self.current_scene
        if previous is not None:
            previous_scene = self.scenes[previous]
            if previous_scene.on_exit:
                previous_scene.on_exit(self)

        self.current_scene = name
        scene = self.scenes[name]
        self.template = scene.template

        if scene.on_enter:
            scene.on_enter(self)
    
    def set_variable(self, key, value, scene_name=None):
        target_scene = scene_name or self.current_scene
        if target_scene is None:
            self.variables[key] = value
            return

        if target_scene not in self.scenes:
            raise KeyError(f"Scene unknown: {target_scene}")

        self.scenes[target_scene].variables[key] = value

    def get_variable(self, key, default=None, scene_name=None):
        target_scene = scene_name or self.current_scene
        if target_scene is None:
            return self.variables.get(key, default)

        if target_scene not in self.scenes:
            raise KeyError(f"Scene unknown: {target_scene}")

        return self.scenes[target_scene].variables.get(key, default)

    def get_scene_names(self):
        return list(self.scenes.keys())
    
    def render_template(self):
        if self.template is None:
            raise ValueError("No template defined. Use set_template() first.")
        
        self.clear()

        scene = self.scenes[self.current_scene] if self.current_scene else None

        if scene and scene.render_callback:
            scene.render_callback(self)
        
        # Itère sur les éléments du template
        for element in self.template:
            element_type = element.get("type")
            
            if element_type == "text":
                # Remplace les variables dans le texte
                merged_variables = dict(self.variables)
                if scene:
                    merged_variables.update(scene.variables)
                text = element["text"].format_map(_SafeFormatDict(merged_variables))
                x = element.get("x", 0)
                y = element.get("y", 0)
                fill = element.get("fill", 1)
                self.draw_text(x, y, text, fill=fill)
            
            elif element_type == "line":
                x1 = element["x1"]
                y1 = element["y1"]
                x2 = element["x2"]
                y2 = element["y2"]
                fill = element.get("fill", 1)
                self.draw_line(x1, y1, x2, y2, fill=fill)
            
            elif element_type == "rectangle":
                x1 = element["x1"]
                y1 = element["y1"]
                x2 = element["x2"]
                y2 = element["y2"]
                fill = element.get("fill", 1)
                self.draw_rectangle(x1, y1, x2, y2, fill=fill)
            
            else:
                print(f"Unknown element type: {element_type}")
        
        self.update_display()


if __name__ == "__main__":
    screen = ScreenManager(width=128, height=64)
    
    screen.set_template([
        {"type": "text", "x": 0, "y": 0, "text": "Division: {division}"},
        {"type": "line", "x1": 0, "y1": 12, "x2": 127, "y2": 12},
        {"type": "text", "x": 0, "y": 15, "text": "Value: {value}"},
        {"type": "rectangle", "x1": 0, "y1": 28, "x2": 127, "y2": 45},
        {"type": "text", "x": 5, "y": 32, "text": "Status: {status}"}
    ])
    
    screen.set_variable("division", 4)
    screen.set_variable("value", 100)
    screen.set_variable("status", "OK")
    screen.render_template()
    
    try:
        while True:
            screen.render_template()
    except KeyboardInterrupt:
        pass