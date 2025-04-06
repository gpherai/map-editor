class TileLayer(BaseLayer):
    """Een laag die een grid van tiles bevat."""
    def __init__(self, name, width, height, id, default_value=0, **kwargs): # default_value is tile ID 0
        super().__init__(name=name, type="tilelayer", width=width, height=height, id=id, **kwargs)
        self.default_value = default_value
        # Gebruik 2D array: data[row][col]
        self.data = [[self.default_value for _ in range(width)] for _ in range(height)]

    def set_cell(self, row, col, value):
        """Stelt de waarde (tile ID) van een cel in."""
        if 0 <= row < self.height and 0 <= col < self.width:
            try:
                int_value = int(value)
                old_value = self.data[row][col]
                self.data[row][col] = int_value
                return old_value
            except (ValueError, TypeError):
                 print(f"Waarschuwing: Ongeldige waarde '{value}' voor set_cell, moet integer zijn.")
                 return None
        return None

    def get_cell(self, row, col):
        """Haalt de waarde (tile ID) van een cel op."""
        if 0 <= row < self.height and 0 <= col < self.width:
            return self.data[row][col]
        return None

    def resize(self, new_width, new_height, default_value=0):
        """Past de grootte van de tile data array aan."""
        old_data = copy.deepcopy(self.data) # Kopie voor undo
        old_width, old_height = self.width, self.height

        new_data_array = [[default_value for _ in range(new_width)] for _ in range(new_height)]

        # Kopieer bestaande data
        copy_height = min(old_height, new_height)
        copy_width = min(old_width, new_width)
        for row in range(copy_height):
            for col in range(copy_width):
                new_data_array[row][col] = self.data[row][col]

        # Update laag properties
        self.width = new_width
        self.height = new_height
        self.data = new_data_array

        return (old_width, old_height, old_data) # Geef oude staat terug voor undo

    def fill(self, value, start_row=0, start_col=0, end_row=None, end_col=None):
        """Vult een gebied met een tile ID."""
        if end_row is None: end_row = self.height - 1
        if end_col is None: end_col = self.width - 1

        # Begrenzing en validatie
        start_row = max(0, min(start_row, self.height - 1))
        start_col = max(0, min(start_col, self.width - 1))
        end_row = max(0, min(end_row, self.height - 1))
        end_col = max(0, min(end_col, self.width - 1))

        changed_cells = []
        try:
            int_value = int(value) # Zorg dat het een integer is
        except (ValueError, TypeError):
            print(f"Waarschuwing: Ongeldige waarde '{value}' voor fill, moet integer zijn.")
            return [] # Geen wijzigingen

        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                old_value = self.data[row][col]
                if old_value != int_value:
                    self.data[row][col] = int_value
                    changed_cells.append((row, col, old_value)) # Sla oude waarde op

        return changed_cells

    def to_dict(self):
        """Converteert tile layer naar dictionary voor JSON."""
        base_dict = super().to_dict()
        # Converteer 2D array naar 1D array voor Tiled compatibiliteit/efficiëntie
        flat_data = [tile for row in self.data for tile in row]
        base_dict.update({
            "data": flat_data, # 1D array
            "width": self.width, # Specifiek voor tilelayer in Tiled JSON
            "height": self.height, # Specifiek voor tilelayer in Tiled JSON
            "encoding": "csv", # Standaard voor Tiled als array plat is
            "compression": ""  # Geen compressie nu
        })
        return base_dict

    @classmethod
    def from_dict(cls, data_dict):
        """Maakt een TileLayer van een dictionary."""
        width = data_dict.get("width", 0)
        height = data_dict.get("height", 0)
        layer_id = data_dict.get("id", 0) # Lees Tiled ID
        layer = cls(
            name=data_dict.get("name", "Tile Layer"),
            width=width,
            height=height,
            id=layer_id,
            visible=data_dict.get("visible", True),
            locked=data_dict.get("locked", False), # Lees onze custom property
            opacity=data_dict.get("opacity", 1.0),
            x=data_dict.get("x", 0),
            y=data_dict.get("y", 0),
        )

        # Laad de data - Tiled slaat vaak op als 1D array
        loaded_data = data_dict.get("data", [])
        expected_length = width * height

        if isinstance(loaded_data, list) and len(loaded_data) == expected_length:
             # Converteer 1D naar 2D
             layer.data = []
             for i in range(height):
                 start = i * width
                 end = start + width
                 layer.data.append([int(c) if str(c).isdigit() else 0 for c in loaded_data[start:end]])
        elif isinstance(loaded_data, list) and height > 0 and len(loaded_data) == height and isinstance(loaded_data[0], list):
             # Het is al 2D (ons formaat)
              print(f"Info: Laag '{layer.name}' data was al in 2D formaat.")
              layer.data = [[int(c) if str(c).isdigit() else 0 for c in r] for r in loaded_data]
              # Check breedte
              if len(layer.data[0]) != width:
                   print(f"Waarschuwing: Breedte in 2D data laag '{layer.name}' klopt niet.")
                   # Corrigeer breedte (kan dataverlies geven)
                   new_data_2d = [[0 for _ in range(width)] for _ in range(height)]
                   for r in range(height):
                       for c in range(min(len(layer.data[r]), width)):
                           new_data_2d[r][c] = layer.data[r][c]
                   layer.data = new_data_2d
        else:
             print(f"Waarschuwing: Data formaat in laag '{layer.name}' onverwacht of incorrecte lengte. Laag wordt leeg gemaakt.")
             layer.data = [[layer.default_value for _ in range(width)] for _ in range(height)]

        return layer