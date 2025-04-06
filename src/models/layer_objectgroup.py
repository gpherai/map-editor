from .layer_base import BaseLayer
from .map_object import MapObject

class ObjectGroupLayer(BaseLayer):
    """Een laag die een lijst van MapObject instanties bevat."""
    def __init__(self, name, width, height, id, draworder="topdown", **kwargs):
        # Width/Height hier vooral voor context in editor, niet strict voor data
        super().__init__(name=name, type="objectgroup", width=width, height=height, id=id, **kwargs)
        self.objects = [] # Lijst van MapObject instanties
        self.draworder = draworder # Tiled property

    def add_object(self, map_object):
        """Voegt een MapObject toe aan de laag."""
        if isinstance(map_object, MapObject):
            self.objects.append(map_object)
            return True
        return False

    def remove_object(self, obj_id):
        """Verwijdert een MapObject op basis van ID."""
        obj_to_remove = self.get_object_by_id(obj_id)
        if obj_to_remove:
            try:
                self.objects.remove(obj_to_remove)
                return obj_to_remove # Geef verwijderd object terug voor undo
            except ValueError:
                 pass # Object was al verwijderd?
        return None

    def get_object_by_id(self, obj_id):
        """Zoekt een MapObject op basis van ID."""
        for obj in self.objects:
            if obj.id == obj_id:
                return obj
        return None

    def to_dict(self):
        """Converteert object group layer naar dictionary voor JSON."""
        base_dict = super().to_dict()
        base_dict.update({
            "draworder": self.draworder,
            "objects": [obj.to_dict() for obj in self.objects]
        })
        # Width/Height zijn niet standaard voor Tiled objectgroup layers
        # Verwijder ze uit de basis dict voor compatibiliteit
        if "width" in base_dict: del base_dict["width"]
        if "height" in base_dict: del base_dict["height"]
        return base_dict

    @classmethod
    def from_dict(cls, data_dict, map_width=0, map_height=0): # Geef map dims mee voor context
        """Maakt een ObjectGroupLayer van een dictionary."""
        layer_id = data_dict.get("id", 0)
        layer = cls(
            name=data_dict.get("name", "Object Group"),
            id=layer_id,
            width=map_width, # Zet contextuele breedte
            height=map_height, # Zet contextuele hoogte
            draworder=data_dict.get("draworder", "topdown"),
            visible=data_dict.get("visible", True),
            locked=data_dict.get("locked", False), # Lees onze custom property
            opacity=data_dict.get("opacity", 1.0),
            x=data_dict.get("x", 0),
            y=data_dict.get("y", 0),
        )
        # Laad objecten
        layer.objects = [MapObject.from_dict(obj_data) for obj_data in data_dict.get("objects", [])]
        return layer
