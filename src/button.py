from gpiozero import Button

class button:
    def __init__(self, pin):
        self.button = Button(pin)

    def on_click(self, callback):
        self.button.when_pressed = callback

    def on_release(self, callback):
        self.button.when_released = callback

if __name__ == "__main__":
    btn = button(13)

    def click_callback():
        print("Button clicked!")

    def release_callback():
        print("Button released!")

    btn.on_click(click_callback)
    btn.on_release(release_callback)

    print("Press the button (Ctrl+C to exit)")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Exiting...")