
class SceneController:
    """Classe de base — enregistre ses scènes et expose une méthode refresh."""

    def __init__(self, sm: "ScreenManager"):
        self.sm = sm
        self._register_scenes()

    def _register_scenes(self):
        raise NotImplementedError

    def set_scene(self, name: str):
        self.sm.set_scene(name)

    def refresh(self):
        self.sm.render()