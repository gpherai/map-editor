from .layer_base import BaseLayer

# --- Layer Classes ---
class BaseLayer:
    """Basisklasse voor alle kaartlagen."""
    def __init__(self, name, type, width, height, id, visible=True, locked=False, opacity=1.0, x=0, y=0):
        self.name = name
        self.type = type # "tilelayer" of "objectgroup"
        self.width = width # Breedte van de map voor context
        self.height = height # Hoogte van de map voor context
        self.id = id # Tiled Layer ID
        self.visible = visible
        self.locked = locked # Onze custom property
        self.opacity = opacity # Tussen 0.0 en 1.0
        self.x = x # Offset X (voor Tiled compatibiliteit)
        self.y = y # Offset Y (voor Tiled compatibiliteit)

    def to_dict(self):
        """Basis serialisatie, voegt Tiled-standaard velden toe."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "visible": self.visible,
            "locked": self.locked, # Eigen property, kan optioneel weggelaten worden voor strict Tiled
            "opacity": self.opacity,
            "x": self.x,
            "y": self.y,
        }

    def set_visibility(self, visible):
        old_visible = self.visible
        self.visible = bool(visible)
        return old_visible

    def set_lock(self, locked):
        old_locked = self.locked
        self.locked = bool(locked)
        return old_locked