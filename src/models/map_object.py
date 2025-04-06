





# --- MapObject Class ---
class MapObject:
    """Representeert een enkel object op een ObjectGroupLayer."""
    _next_id = 1 # Simpele manier om unieke IDs te genereren per sessie

    def __init__(self, obj_type, x, y, width=32, height=32, name="", properties=None, gid=None):
        self.id = MapObject._next_id
        MapObject._next_id += 1
        self.name = name
        self.type = obj_type # bv. "tree", "house", "npc_spawn"
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.properties = properties if properties is not None else {}
        self.gid = gid # Optioneel GID voor Tiled compatibiliteit (placeholder tile)
        self.rotation = 0 # Standaard voor Tiled
        self.visible = True # Standaard voor Tiled

    def to_dict(self):
        """Converteert object naar dictionary voor JSON, Tiled compatibel."""
        # Maakt een kopie om te voorkomen dat we het origineel wijzigen
        props_copy = copy.deepcopy(self.properties)
        data = {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "properties": props_copy,
            "rotation": self.rotation,
            "visible": self.visible,
        }
        if self.gid is not None: # Voeg gid alleen toe als het gezet is
            data["gid"] = self.gid
        return data

    @classmethod
    def from_dict(cls, data):
        """Maakt een MapObject van een dictionary."""
        # Zorg dat volgende ID hoger is dan geladen IDs
        MapObject._next_id = max(MapObject._next_id, data.get("id", 0) + 1)

        # Maak een diepe kopie van properties om onverwachte gedeelde referenties te voorkomen
        properties_copy = copy.deepcopy(data.get("properties", {}))

        obj = cls(
            obj_type=data.get("type", ""),
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 32), # Standaard breedte/hoogte
            height=data.get("height", 32),
            name=data.get("name", ""),
            properties=properties_copy,
            gid=data.get("gid") # Laad GID indien aanwezig
        )
        # Overschrijf gegenereerde ID met geladen ID, indien aanwezig
        obj.id = data.get("id", obj.id)
        obj.rotation = data.get("rotation", 0)
        obj.visible = data.get("visible", True)
        return obj
