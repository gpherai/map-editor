# src/models/map_model.py
# Model voor de Map Editor - beheert de kaartdata en operaties
# Versie aangepast voor JSON formaat met metadata en typed layers.

import os
import json
from collections import deque
import time
import copy # Nodig voor deep copies in undo/redo

# Importeer de gesplitste klassen
from .map_object import MapObject
from .layer_tile import TileLayer  # Impliciet BaseLayer via overerving
from .layer_objectgroup import ObjectGroupLayer # Impliciet BaseLayer via overerving
from .map_action import MapAction
from .layer_base import BaseLayer

# --- MapModel Class ---
class MapModel:
    """Model voor de kaartdata, ondersteunt meerdere lagen en undo/redo."""

    def __init__(self, config):
        """
        Initialiseert het kaartmodel.
        Args:
            config: Dict-like object met configuratie-instellingen.
        """
        self.config = config
        self.new_map() # Start met een lege kaart volgens config

    def new_map(self, width=None, height=None):
        """Maakt een nieuwe, lege kaart aan."""
        old_state_dict = self.to_dict() if hasattr(self, 'metadata') and self.metadata else None # Voor undo

        map_w = width if width is not None else self.config.get("default_map_width", 40)
        map_h = height if height is not None else self.config.get("default_map_height", 30)
        tile_w = self.config.get("tile_width", 32)
        tile_h = self.config.get("tile_height", 32)

        # Reset object ID counter
        MapObject._next_id = 1

        self.metadata = {
            "mapName": "Nieuwe Kaart", # Zal overschreven worden bij save/load
            "mapWidth": map_w,
            "mapHeight": map_h,
            "tileWidth": tile_w,
            "tileHeight": tile_h,
            "bgMusic": "",
            "infinite": False,
            "nextlayerid": 1, # Start laag ID's vanaf 1
            "nextobjectid": 1, # Start object ID's vanaf 1 (wordt beheerd door MapObject class)
            "orientation": "orthogonal",
            "renderorder": "right-down",
            "tiledversion": "1.10.0", # Indicatie van recent Tiled formaat
            "tilesets": [], # Leeg voor nu
            "type": "map",
            "version": "1.10" # Tiled JSON formaat versie
        }
        self.width = map_w
        self.height = map_h
        self.current_file = None
        self.unsaved_changes = False
        self.active_layer_index = 0
        self.layers = [] # Lijst van Layer objecten

        # Maak standaard lagen aan
        default_layers_config = self.config.get("default_layers", [
            {"name": "Terrain", "type": "tilelayer", "visible": True, "locked": False},
            {"name": "Objects", "type": "objectgroup", "visible": True, "locked": False},
            {"name": "NPCs",    "type": "objectgroup", "visible": True, "locked": False}
        ])
        layer_id_counter = 1
        for layer_config in default_layers_config:
            layer_type = layer_config.get("type", "tilelayer")
            layer_name = layer_config.get("name", f"Laag {layer_id_counter}")
            layer_visible = layer_config.get("visible", True)
            layer_locked = layer_config.get("locked", False)
            layer = None

            if layer_type == "tilelayer":
                layer = TileLayer(name=layer_name, width=self.width, height=self.height, id=layer_id_counter,
                                  default_value=0, visible=layer_visible, locked=layer_locked)
            elif layer_type == "objectgroup":
                layer = ObjectGroupLayer(name=layer_name, width=self.width, height=self.height, id=layer_id_counter,
                                       visible=layer_visible, locked=layer_locked)

            if layer:
                 self.layers.append(layer)
                 layer_id_counter += 1

        self.metadata["nextlayerid"] = layer_id_counter

        # Reset undo/redo stacks
        self.undo_stack = deque(maxlen=self.config.get("max_undo_steps", 50))
        self.redo_stack = deque(maxlen=self.config.get("max_undo_steps", 50))

        # Voeg undo actie toe als er een vorige staat was
        if old_state_dict:
            self._add_action("new_map", {"old_state": old_state_dict, "new_state": self.to_dict()}) # Sla ook nieuwe staat op

        self.unsaved_changes = False # Een nieuwe kaart heeft geen wijzigingen
        return True

    @property
    def active_layer(self):
        """Geeft de actieve laag (TileLayer of ObjectGroupLayer object)."""
        if 0 <= self.active_layer_index < len(self.layers):
            return self.layers[self.active_layer_index]
        return None

    def set_active_layer(self, index):
        """Stelt de actieve laag in op basis van index."""
        if 0 <= index < len(self.layers):
            if self.active_layer_index != index:
                 # Geen undo nodig voor enkel wisselen van actieve laag
                self.active_layer_index = index
                return True # Geeft aan dat de index gewijzigd is
        return False

    def add_layer(self, name, layer_type="tilelayer", visible=True, locked=False):
        """Voegt een nieuwe laag van een specifiek type toe."""
        new_layer = None
        layer_id = self.metadata.get("nextlayerid", len(self.layers) + 1)

        if layer_type == "tilelayer":
            new_layer = TileLayer(
                name=name, width=self.width, height=self.height, id=layer_id, default_value=0,
                visible=visible, locked=locked
            )
        elif layer_type == "objectgroup":
             new_layer = ObjectGroupLayer(
                name=name, width=self.width, height=self.height, id=layer_id,
                visible=visible, locked=locked
            )
        else:
            print(f"Fout: Onbekend laag type '{layer_type}' kan niet worden toegevoegd.")
            return -1

        self.layers.append(new_layer)
        self.metadata["nextlayerid"] = layer_id + 1 # Update next layer ID in metadata
        new_index = len(self.layers) - 1

        self._add_action("add_layer", {
            "layer_index": new_index,
            "layer_data": new_layer.to_dict() # Sla volledige data op voor herstel
        })
        # self.unsaved_changes = True # Wordt gedaan door _add_action
        return new_index

    def remove_layer(self, index):
        """Verwijdert een laag op basis van index."""
        if 0 <= index < len(self.layers) and len(self.layers) > 1: # Moet minimaal 1 laag overblijven
            layer_to_remove = self.layers[index]
            self._add_action("remove_layer", {
                "layer_index": index,
                "layer_data": layer_to_remove.to_dict() # Sla data van verwijderde laag op
            })
            self.layers.pop(index)

            # Pas actieve index aan indien nodig
            if self.active_layer_index >= len(self.layers):
                self.active_layer_index = len(self.layers) - 1
            elif self.active_layer_index > index:
                 self.active_layer_index -= 1

            # self.unsaved_changes = True # Wordt gedaan door _add_action
            return layer_to_remove
        return None

    def move_layer(self, index, delta):
        """Verplaatst de laag op 'index' omhoog (delta=-1) of omlaag (delta=1)."""
        if not (0 <= index < len(self.layers)): return False
        new_index = index + delta
        if not (0 <= new_index < len(self.layers)): return False

        self._add_action("move_layer", {"old_index": index, "new_index": new_index})
        layer = self.layers.pop(index)
        self.layers.insert(new_index, layer)

        # Update actieve index als deze beïnvloed is
        if self.active_layer_index == index: self.active_layer_index = new_index
        elif min(index, new_index) <= self.active_layer_index <= max(index, new_index):
             self.active_layer_index += delta * -1 # Tegenovergestelde richting van laagbeweging

        # self.unsaved_changes = True # Wordt gedaan door _add_action
        return True

    def set_cell(self, row, col, value, layer_index=None):
        """Stelt de waarde van een cel in op een TileLayer."""
        layer_idx = layer_index if layer_index is not None else self.active_layer_index
        if 0 <= layer_idx < len(self.layers):
            layer = self.layers[layer_idx]
            if isinstance(layer, TileLayer) and not layer.locked:
                 try:
                     int_value = int(value)
                     old_value = layer.get_cell(row, col)
                     if old_value is not None and old_value != int_value:
                         if layer.set_cell(row, col, int_value) is not None: # Check return van set_cell
                             self._add_action("set_cell", {
                                 "layer_index": layer_idx, "row": row, "col": col,
                                 "old_value": old_value, "new_value": int_value
                             })
                             return True
                 except (ValueError, TypeError):
                     print(f"Waarschuwing: Ongeldige waarde '{value}' voor set_cell.")
        return False

    def get_cell(self, row, col, layer_index=None):
        """Haalt de waarde van een cel op van een TileLayer."""
        layer_idx = layer_index if layer_index is not None else self.active_layer_index
        if 0 <= layer_idx < len(self.layers):
            layer = self.layers[layer_idx]
            if isinstance(layer, TileLayer):
                return layer.get_cell(row, col)
        return None

    def get_cell_at_all_layers(self, row, col):
        """Haalt waarden op van een cel in alle zichtbare TileLayers."""
        result = []
        for i, layer in enumerate(self.layers):
            if layer.visible and isinstance(layer, TileLayer):
                value = layer.get_cell(row, col)
                if value is not None and value != layer.default_value:
                    result.append((i, value))
        return result

    def get_top_cell(self, row, col):
        """Haalt de bovenste niet-default waarde op van alle zichtbare TileLayers."""
        for i in range(len(self.layers) - 1, -1, -1):
            layer = self.layers[i]
            if layer.visible and isinstance(layer, TileLayer):
                value = layer.get_cell(row, col)
                if value is not None and value != layer.default_value:
                    return (i, value)
        return (None, None)

    def resize(self, new_width, new_height):
        """Past de grootte van de map en alle lagen aan."""
        if new_width <= 0 or new_height <= 0:
             print("Fout: Kaartafmetingen moeten positief zijn.")
             return False

        old_metadata = copy.deepcopy(self.metadata)
        old_layers_struct = [{"index": i, "data": layer.to_dict()} for i, layer in enumerate(self.layers)] # Sla structuur en data op

        self.metadata["mapWidth"] = new_width
        self.metadata["mapHeight"] = new_height
        self.width = new_width
        self.height = new_height

        resized_layers_data = [] # Om nieuwe staat voor redo op te slaan
        for i, layer in enumerate(self.layers):
             if isinstance(layer, TileLayer):
                 # TileLayer.resize past self.width/height en data aan
                 layer.resize(new_width, new_height, default_value=layer.default_value)
             # Object layers hoeven intern niet geresized te worden, alleen contextuele w/h
             layer.width = new_width
             layer.height = new_height
             resized_layers_data.append(layer.to_dict()) # Sla nieuwe staat op

        self._add_action("resize", {
            "old_metadata": old_metadata,
            "new_metadata": copy.deepcopy(self.metadata),
            "old_layers_data": old_layers_struct, # Oude data en index
            "new_layers_data": resized_layers_data  # Nieuwe data
        })
        return True

    def fill(self, value, layer_index=None, start_row=None, start_col=None, end_row=None, end_col=None):
         """Vult een gebied van een TileLayer."""
         layer_idx = layer_index if layer_index is not None else self.active_layer_index
         if 0 <= layer_idx < len(self.layers):
             layer = self.layers[layer_idx]
             if isinstance(layer, TileLayer) and not layer.locked:
                 try:
                     int_value = int(value)
                     changed_cells = layer.fill(int_value, start_row, start_col, end_row, end_col)
                     if changed_cells:
                         self._add_action("fill", {
                             "layer_index": layer_idx,
                             "changed_cells": changed_cells, # list of (row, col, old_value)
                             "filled_value": int_value
                         })
                         return True
                 except (ValueError, TypeError):
                      print(f"Waarschuwing: Ongeldige waarde '{value}' voor fill.")
         return False

    def toggle_layer_visibility(self, index):
        """Schakelt de zichtbaarheid van een laag."""
        if 0 <= index < len(self.layers):
            layer = self.layers[index]
            old_visible = layer.set_visibility(not layer.visible) # Gebruik setter
            self._add_action("toggle_visibility", {"layer_index": index, "old_value": old_visible})
            # self.unsaved_changes = True # Wordt gedaan door _add_action
            return layer.visible
        return False # Geef huidige status terug bij falen?

    def toggle_layer_lock(self, index):
        """Schakelt de vergrendeling van een laag."""
        if 0 <= index < len(self.layers):
            layer = self.layers[index]
            old_locked = layer.set_lock(not layer.locked) # Gebruik setter
            self._add_action("toggle_lock", {"layer_index": index, "old_value": old_locked})
            # self.unsaved_changes = True # Wordt gedaan door _add_action
            return layer.locked
        return False # Geef huidige status terug bij falen?

    # --- Object Manipulatie ---
    def add_object_to_active_layer(self, obj_type, x, y, width=32, height=32, name="", properties=None, gid=None):
        """Voegt een object toe aan de actieve laag, indien het een ObjectGroupLayer is."""
        layer = self.active_layer
        if isinstance(layer, ObjectGroupLayer) and not layer.locked:
            new_obj = MapObject(obj_type, x, y, width, height, name, properties, gid)
            # Update nextobjectid in metadata (Tiled doet dit ook)
            self.metadata["nextobjectid"] = max(self.metadata.get("nextobjectid", 1), new_obj.id + 1)
            if layer.add_object(new_obj):
                self._add_action("add_object", {
                    "layer_index": self.active_layer_index,
                    "object_data": new_obj.to_dict() # Sla data op voor undo
                })
                return new_obj
        return None

    def remove_object_from_active_layer(self, obj_id):
        """Verwijdert een object van de actieve laag op basis van ID."""
        layer = self.active_layer
        if isinstance(layer, ObjectGroupLayer) and not layer.locked:
            removed_obj = layer.remove_object(obj_id)
            if removed_obj:
                self._add_action("remove_object", {
                    "layer_index": self.active_layer_index,
                    "object_data": removed_obj.to_dict() # Sla data van verwijderd object op
                })
                return True
        return False

    def update_object_properties(self, obj_id, new_properties, layer_index=None):
         """Werkt de properties bij van een object op de opgegeven of actieve laag."""
         target_layer_index = layer_index if layer_index is not None else self.active_layer_index
         if not (0 <= target_layer_index < len(self.layers)): return False

         layer = self.layers[target_layer_index]
         if isinstance(layer, ObjectGroupLayer) and not layer.locked:
             obj_to_update = layer.get_object_by_id(obj_id)
             if obj_to_update:
                 old_properties = copy.deepcopy(obj_to_update.properties)
                 # Update, overschrijf bestaande, voeg nieuwe toe
                 obj_to_update.properties.update(new_properties)
                 # Controleer of er daadwerkelijk iets veranderd is
                 if old_properties != obj_to_update.properties:
                     self._add_action("update_object_properties", {
                         "layer_index": target_layer_index, "object_id": obj_id,
                         "old_properties": old_properties,
                         "new_properties": copy.deepcopy(obj_to_update.properties)
                     })
                     return True
                 else:
                      return True # Geen wijziging, maar actie 'geslaagd'
         return False

    def update_object_basic_info(self, obj_id, name=None, type=None, x=None, y=None, width=None, height=None, gid=None, layer_index=None):
        """Werkt basis attributen bij van een object (naam, type, pos, size, gid)."""
        target_layer_index = layer_index if layer_index is not None else self.active_layer_index
        if not (0 <= target_layer_index < len(self.layers)): return False

        layer = self.layers[target_layer_index]
        if isinstance(layer, ObjectGroupLayer) and not layer.locked:
            obj_to_update = layer.get_object_by_id(obj_id)
            if obj_to_update:
                old_basic_info = {
                    "name": obj_to_update.name, "type": obj_to_update.type,
                    "x": obj_to_update.x, "y": obj_to_update.y,
                    "width": obj_to_update.width, "height": obj_to_update.height,
                    "gid": obj_to_update.gid
                }
                changed = False
                if name is not None and obj_to_update.name != name: obj_to_update.name = name; changed = True
                if type is not None and obj_to_update.type != type: obj_to_update.type = type; changed = True
                if x is not None and obj_to_update.x != x: obj_to_update.x = x; changed = True
                if y is not None and obj_to_update.y != y: obj_to_update.y = y; changed = True
                if width is not None and obj_to_update.width != width: obj_to_update.width = width; changed = True
                if height is not None and obj_to_update.height != height: obj_to_update.height = height; changed = True
                if gid is not None and obj_to_update.gid != gid: obj_to_update.gid = gid; changed = True # GID kan None zijn

                if changed:
                    new_basic_info = {
                         "name": obj_to_update.name, "type": obj_to_update.type,
                         "x": obj_to_update.x, "y": obj_to_update.y,
                         "width": obj_to_update.width, "height": obj_to_update.height,
                         "gid": obj_to_update.gid
                    }
                    self._add_action("update_object_basic", {
                        "layer_index": target_layer_index, "object_id": obj_id,
                        "old_info": old_basic_info, "new_info": new_basic_info
                    })
                    return True
                else:
                    return True # Geen wijziging, maar 'geslaagd'
        return False

    # --- Laden en Opslaan ---
    def load_map(self, filepath):
        """Laadt een kaart uit een JSON-bestand."""
        if not filepath or not os.path.exists(filepath) or not filepath.lower().endswith(".json"):
            print(f"Fout: Ongeldig pad of geen JSON-bestand: {filepath}")
            return False
        try:
            # Reset het model voordat we laden (belangrijk voor state)
            # self.new_map() # Misschien beter om direct te overschrijven?

            # Sla huidige staat op VOORDAT we laden, voor undo
            old_state_dict = self.to_dict()

            # Laad de nieuwe structuur
            success = self._load_from_json(filepath)

            if success:
                 # Reset undo/redo na succesvol laden
                 self.undo_stack.clear()
                 self.redo_stack.clear()
                 # Voeg de laad-actie toe aan undo (met oude staat)
                 self._add_action("load_map", {"old_state": old_state_dict, "new_state": self.to_dict()})
                 self.unsaved_changes = False # Net geladen = geen wijzigingen
            return success
        except Exception as e:
            print(f"Algemene fout bij laden kaart '{filepath}': {e}")
            # Herstel mogelijk de oude staat? Lastig.
            return False

    def _load_from_json(self, filepath):
        """Laadt kaart data uit JSON bestand en update het model."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Fout: Ongeldig JSON-formaat in '{filepath}': {e}")
            return False
        except IOError as e:
             print(f"Fout: Kan bestand niet lezen '{filepath}': {e}")
             return False

        # --- Laad Metadata (Tiled-stijl) ---
        # Start met defaults, overschrijf met geladen data
        map_w = data.get("width", self.config.get("default_map_width", 40))
        map_h = data.get("height", self.config.get("default_map_height", 30))
        tile_w = data.get("tilewidth", self.config.get("tile_width", 32))
        tile_h = data.get("tileheight", self.config.get("tile_height", 32))

        self.metadata = {
            "mapName": os.path.splitext(os.path.basename(filepath))[0], # Gebruik bestandsnaam als default
            "mapWidth": map_w, "mapHeight": map_h,
            "tileWidth": tile_w, "tileHeight": tile_h,
            "bgMusic": data.get("properties", [{}])[0].get("bgMusic", ""), # Tiled stopt custom props vaak hier
            "infinite": data.get("infinite", False),
            "nextlayerid": data.get("nextlayerid", 1),
            "nextobjectid": data.get("nextobjectid", 1),
            "orientation": data.get("orientation", "orthogonal"),
            "renderorder": data.get("renderorder", "right-down"),
            "tiledversion": data.get("tiledversion", "1.10.0"),
            "tilesets": data.get("tilesets", []), # Laad tilesets mee, ook al gebruiken we ze niet direct
            "type": data.get("type", "map"),
            "version": data.get("version", "1.10")
        }
        # Laad eventuele top-level custom properties (minder gangbaar in Tiled)
        if "properties" in data:
             self.metadata["custom_properties"] = data["properties"]


        self.width = map_w
        self.height = map_h

        # Reset object ID counter voor deze map load
        MapObject._next_id = 1

        # --- Laad Lagen ---
        self.layers = []
        next_layer_id_calc = 1
        max_obj_id_calc = 0
        loaded_layers_data = data.get("layers", [])
        for layer_data in loaded_layers_data:
            layer_type = layer_data.get("type")
            layer = None
            try:
                if layer_type == "tilelayer":
                    layer = TileLayer.from_dict(layer_data)
                    # Check & Corrigeer dimensies indien nodig
                    if layer.width != self.width or layer.height != self.height:
                        print(f"Waarschuwing: Dimensies van tile layer '{layer.name}' (ID {layer.id}) gecorrigeerd naar kaartformaat.")
                        layer.resize(self.width, self.height, layer.default_value)
                elif layer_type == "objectgroup":
                    layer = ObjectGroupLayer.from_dict(layer_data, self.width, self.height)
                    # Update max object ID
                    for obj in layer.objects:
                        max_obj_id_calc = max(max_obj_id_calc, obj.id)
                else:
                    print(f"Onbekend laagtype '{layer_type}' overgeslagen bij laden.")

                if layer:
                    # Neem ID over uit data, of gebruik counter
                    layer.id = layer_data.get("id", next_layer_id_calc)
                    self.layers.append(layer)
                    next_layer_id_calc = max(next_layer_id_calc, layer.id + 1)
            except Exception as e:
                 print(f"Fout bij laden laag '{layer_data.get('name', 'Onbekend')}': {e}")

        # Update metadata met berekende next IDs
        self.metadata["nextlayerid"] = max(next_layer_id_calc, self.metadata.get("nextlayerid", next_layer_id_calc))
        # Zorg dat MapObject counter en metadata syncen
        MapObject._next_id = max(max_obj_id_calc + 1, MapObject._next_id)
        self.metadata["nextobjectid"] = max(MapObject._next_id, self.metadata.get("nextobjectid", MapObject._next_id))


        # Fallback als geen lagen geladen zijn
        if not self.layers:
             print("Waarschuwing: Geen lagen gevonden in JSON, standaard 'Terrain' laag aangemaakt.")
             default_layer = TileLayer(name="Terrain", width=self.width, height=self.height, id=1)
             self.layers.append(default_layer)
             self.metadata["nextlayerid"] = 2

        self.active_layer_index = 0 # Start altijd op de eerste laag na laden
        self.current_file = filepath
        # self.unsaved_changes = False # Wordt gezet door aanroepende load_map
        # self.config.add_recent_file(filepath) # Wordt gezet door aanroepende save/load_map
        return True # Succesvol geparsed (binnen de try-except van load_map)

    def save_map(self, filepath=None):
        """Slaat de kaart op naar een JSON-bestand."""
        save_path = filepath if filepath else self.current_file
        if not save_path:
            print("Fout: Geen bestandspad opgegeven om op te slaan.")
            return False

        # Zorg dat het pad eindigt op .json
        if not save_path.lower().endswith(".json"):
            save_path += ".json"

        try:
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
            success = self._save_to_json(save_path)
            if success:
                self.current_file = save_path
                self.unsaved_changes = False
                # self.config.add_recent_file(save_path) # Config moet buiten model beheerd worden
            return success
        except Exception as e:
            print(f"Fout bij opslaan kaart naar '{save_path}': {e}")
            return False

    def _save_to_json(self, filepath):
        """Slaat de kaart op in Tiled-compatibel JSON formaat."""
        try:
            map_data = self.to_dict() # Haal de volledige datastructuur op

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(map_data, f, indent=2) # indent=2 voor leesbaarheid

            return True
        except Exception as e:
            print(f"Fout tijdens schrijven JSON naar '{filepath}': {e}")
            return False

    def to_dict(self):
        """Converteert het volledige model naar een Tiled-compatibele dictionary."""
        # Update next IDs in metadata voordat we opslaan
        self.metadata["nextlayerid"] = max(layer.id for layer in self.layers if hasattr(layer, 'id')) + 1 if self.layers else 1
        self.metadata["nextobjectid"] = MapObject._next_id

        map_data = {
            # Metadata velden die direct overeenkomen met Tiled formaat
            "width": self.width,
            "height": self.height,
            "tilewidth": self.metadata.get("tileWidth", 32),
            "tileheight": self.metadata.get("tileHeight", 32),
            "infinite": self.metadata.get("infinite", False),
            "nextlayerid": self.metadata["nextlayerid"],
            "nextobjectid": self.metadata["nextobjectid"],
            "orientation": self.metadata.get("orientation", "orthogonal"),
            "renderorder": self.metadata.get("renderorder", "right-down"),
            "tiledversion": self.metadata.get("tiledversion", "1.10.0"),
            "tilesets": self.metadata.get("tilesets", []), # Behoud tilesets indien geladen
            "type": "map",
            "version": self.metadata.get("version", "1.10"),
            # Lagen data
            "layers": [layer.to_dict() for layer in self.layers if layer is not None],
            # Custom properties (optioneel, Tiled stopt ze vaak hier)
            "properties": [
                 {"name": "bgMusic", "type": "string", "value": self.metadata.get("bgMusic", "")}
                 # Voeg hier eventuele andere custom map properties toe
            ]
            # mapName zit niet standaard in Tiled JSON, maar in onze metadata
        }
        # Voeg onze custom metadata toe die niet standaard Tiled is (optioneel)
        # map_data["custom_metadata"] = {k: v for k, v in self.metadata.items() if k not in map_data}
        return map_data

    # --- Undo/Redo ---
    def _add_action(self, action_type, data):
        """Voegt een actie toe aan de undo-stack. Gebruikt deep copies."""
        try:
            # Maak diepe kopieën om te voorkomen dat latere wijzigingen de undo-data beïnvloeden
            action_data_copy = copy.deepcopy(data)
            self.undo_stack.append(MapAction(action_type, action_data_copy))
            self.redo_stack.clear() # Nieuwe actie maakt redo-historie ongeldig
            self.unsaved_changes = True # Elke actie wordt als wijziging gezien
        except Exception as e:
            print(f"Fout bij maken deepcopy voor undo actie '{action_type}': {e}")
            # Wat te doen? Undo niet toevoegen? Geeft risico op inconsistente staat.
            # Misschien beter om hier te crashen of een duidelijke error te geven.

    def has_unsaved_changes(self):
        """Controleert of er onopgeslagen wijzigingen zijn."""
        return self.unsaved_changes

    def can_undo(self):
        """Controleert of er acties zijn om ongedaan te maken."""
        return len(self.undo_stack) > 0

    def can_redo(self):
        """Controleert of er acties zijn om opnieuw te doen."""
        return len(self.redo_stack) > 0

    def undo(self):
        """Maakt de laatste actie ongedaan."""
        if not self.can_undo(): return False
        action = self.undo_stack.pop()
        success = False

        try:
            if action.type == "set_cell":
                layer = self.layers[action.data["layer_index"]]
                if isinstance(layer, TileLayer):
                    layer.set_cell(action.data["row"], action.data["col"], action.data["old_value"])
                    success = True
            elif action.type == "fill":
                layer = self.layers[action.data["layer_index"]]
                if isinstance(layer, TileLayer):
                    for row, col, old_value in action.data["changed_cells"]:
                        layer.set_cell(row, col, old_value)
                    success = True
            elif action.type == "resize":
                 self._restore_from_dict(action.data["old_state"]) # Herstel volledige oude staat
                 success = True
            elif action.type == "add_layer":
                 layer_idx = action.data["layer_index"]
                 if 0 <= layer_idx < len(self.layers):
                     # Verifieer of de laag op die index overeenkomt (simpele check)
                     if self.layers[layer_idx].id == action.data["layer_data"]["id"]:
                         self.layers.pop(layer_idx)
                         # Pas actieve index aan
                         if self.active_layer_index >= len(self.layers): self.active_layer_index = max(0, len(self.layers) - 1)
                         elif self.active_layer_index > layer_idx: self.active_layer_index -= 1
                         success = True
            elif action.type == "remove_layer":
                 layer_idx = action.data["layer_index"]
                 layer_data = action.data["layer_data"]
                 layer_type = layer_data.get("type")
                 layer = None
                 # Maak laag opnieuw aan van opgeslagen data
                 if layer_type == "tilelayer": layer = TileLayer.from_dict(layer_data)
                 elif layer_type == "objectgroup": layer = ObjectGroupLayer.from_dict(layer_data, self.width, self.height)
                 if layer and 0 <= layer_idx <= len(self.layers):
                     self.layers.insert(layer_idx, layer)
                     # Pas actieve index aan
                     if layer_idx <= self.active_layer_index: self.active_layer_index += 1
                     success = True
            elif action.type == "move_layer":
                 old_idx = action.data["old_index"]
                 new_idx = action.data["new_index"]
                 # Verplaats terug
                 layer = self.layers.pop(new_idx)
                 self.layers.insert(old_idx, layer)
                 # Herstel actieve index
                 if self.active_layer_index == new_idx: self.active_layer_index = old_idx
                 elif min(old_idx, new_idx) <= self.active_layer_index <= max(old_idx, new_idx):
                     self.active_layer_index += 1 if new_idx < old_idx else -1
                 success = True
            elif action.type == "toggle_visibility":
                 layer = self.layers[action.data["layer_index"]]
                 layer.set_visibility(action.data["old_value"])
                 success = True
            elif action.type == "toggle_lock":
                 layer = self.layers[action.data["layer_index"]]
                 layer.set_lock(action.data["old_value"])
                 success = True
            elif action.type == "add_object":
                 layer = self.layers[action.data["layer_index"]]
                 if isinstance(layer, ObjectGroupLayer):
                     obj_data = action.data["object_data"]
                     # Verwijder object met dezelfde ID
                     layer.objects = [obj for obj in layer.objects if obj.id != obj_data.get("id")]
                     success = True
            elif action.type == "remove_object":
                 layer = self.layers[action.data["layer_index"]]
                 if isinstance(layer, ObjectGroupLayer):
                     obj_data = action.data["object_data"]
                     # Voeg object terug toe
                     layer.add_object(MapObject.from_dict(obj_data))
                     success = True
            elif action.type == "update_object_properties":
                 layer = self.layers[action.data["layer_index"]]
                 if isinstance(layer, ObjectGroupLayer):
                     obj = layer.get_object_by_id(action.data["object_id"])
                     if obj:
                         obj.properties = copy.deepcopy(action.data["old_properties"])
                         success = True
            elif action.type == "update_object_basic":
                 layer = self.layers[action.data["layer_index"]]
                 if isinstance(layer, ObjectGroupLayer):
                     obj = layer.get_object_by_id(action.data["object_id"])
                     if obj:
                         old_info = action.data["old_info"]
                         obj.name = old_info["name"]
                         obj.type = old_info["type"]
                         obj.x = old_info["x"]
                         obj.y = old_info["y"]
                         obj.width = old_info["width"]
                         obj.height = old_info["height"]
                         obj.gid = old_info["gid"]
                         success = True
            elif action.type == "new_map" or action.type == "load_map":
                 self._restore_from_dict(action.data["old_state"])
                 success = True
            else:
                 print(f"Undo niet geïmplementeerd voor actie: {action.type}")

            if success:
                self.redo_stack.append(action)
                # De staat is nu *mogelijk* weer zoals voor de laatste actie.
                # unsaved_changes moet idealiter bijgehouden worden of de staat
                # gelijk is aan de laatst opgeslagen staat. Voor nu:
                # self.unsaved_changes = self.can_undo()
                return True # Geef aan dat undo geslaagd is
        except Exception as e:
            print(f"Fout tijdens undo van {action.type}: {e}")
            # Probeer de actie terug te zetten op de undo stack? Riskant.
        return False


    def redo(self):
        """Doet de laatst ongedaan gemaakte actie opnieuw."""
        if not self.can_redo(): return False
        action = self.redo_stack.pop()
        success = False

        try:
            if action.type == "set_cell":
                layer = self.layers[action.data["layer_index"]]
                if isinstance(layer, TileLayer):
                    layer.set_cell(action.data["row"], action.data["col"], action.data["new_value"])
                    success = True
            elif action.type == "fill":
                layer = self.layers[action.data["layer_index"]]
                if isinstance(layer, TileLayer):
                    # We hebben de filled_value opgeslagen
                    for row, col, _ in action.data["changed_cells"]:
                         layer.set_cell(row, col, action.data["filled_value"])
                    success = True
            elif action.type == "resize":
                 self._restore_from_dict(action.data["new_state"]) # Herstel naar nieuwe staat
                 success = True
            elif action.type == "add_layer":
                 # Voeg laag opnieuw toe
                 layer_idx = action.data["layer_index"]
                 layer_data = action.data["layer_data"]
                 layer_type = layer_data.get("type")
                 layer = None
                 if layer_type == "tilelayer": layer = TileLayer.from_dict(layer_data)
                 elif layer_type == "objectgroup": layer = ObjectGroupLayer.from_dict(layer_data, self.width, self.height)
                 if layer and 0 <= layer_idx <= len(self.layers):
                     self.layers.insert(layer_idx, layer)
                     # Pas actieve index aan
                     if layer_idx <= self.active_layer_index: self.active_layer_index += 1
                     success = True
            elif action.type == "remove_layer":
                 # Verwijder laag opnieuw
                 layer_idx = action.data["layer_index"]
                 if 0 <= layer_idx < len(self.layers):
                     # Verifieer of het de juiste laag is
                     if self.layers[layer_idx].id == action.data["layer_data"]["id"]:
                         self.layers.pop(layer_idx)
                         # Pas actieve index aan
                         if self.active_layer_index >= len(self.layers): self.active_layer_index = max(0, len(self.layers) - 1)
                         elif self.active_layer_index > layer_idx: self.active_layer_index -= 1
                         success = True
            elif action.type == "move_layer":
                 old_idx = action.data["old_index"]
                 new_idx = action.data["new_index"]
                 # Verplaats opnieuw
                 layer = self.layers.pop(old_idx)
                 self.layers.insert(new_idx, layer)
                 # Update actieve index
                 if self.active_layer_index == old_idx: self.active_layer_index = new_idx
                 elif min(old_idx, new_idx) <= self.active_layer_index <= max(old_idx, new_idx):
                     self.active_layer_index += 1 if old_idx < new_idx else -1
                 success = True
            elif action.type == "toggle_visibility":
                 layer = self.layers[action.data["layer_index"]]
                 # Toggle naar !old_value
                 layer.set_visibility(not action.data["old_value"])
                 success = True
            elif action.type == "toggle_lock":
                 layer = self.layers[action.data["layer_index"]]
                 layer.set_lock(not action.data["old_value"])
                 success = True
            elif action.type == "add_object":
                 layer = self.layers[action.data["layer_index"]]
                 if isinstance(layer, ObjectGroupLayer):
                     obj_data = action.data["object_data"]
                     # Voeg object terug toe
                     layer.add_object(MapObject.from_dict(obj_data))
                     success = True
            elif action.type == "remove_object":
                 layer = self.layers[action.data["layer_index"]]
                 if isinstance(layer, ObjectGroupLayer):
                     obj_data = action.data["object_data"]
                     # Verwijder object opnieuw
                     layer.objects = [obj for obj in layer.objects if obj.id != obj_data.get("id")]
                     success = True
            elif action.type == "update_object_properties":
                 layer = self.layers[action.data["layer_index"]]
                 if isinstance(layer, ObjectGroupLayer):
                     obj = layer.get_object_by_id(action.data["object_id"])
                     if obj:
                         obj.properties = copy.deepcopy(action.data["new_properties"])
                         success = True
            elif action.type == "update_object_basic":
                  layer = self.layers[action.data["layer_index"]]
                  if isinstance(layer, ObjectGroupLayer):
                      obj = layer.get_object_by_id(action.data["object_id"])
                      if obj:
                          new_info = action.data["new_info"]
                          obj.name = new_info["name"]
                          obj.type = new_info["type"]
                          obj.x = new_info["x"]
                          obj.y = new_info["y"]
                          obj.width = new_info["width"]
                          obj.height = new_info["height"]
                          obj.gid = new_info["gid"]
                          success = True
            elif action.type == "new_map" or action.type == "load_map":
                 # Herstel de *gehele* nieuwe staat die bij de actie was opgeslagen
                 new_state = action.data["new_state"]
                 self._restore_from_dict(new_state)
                 success = True
            else:
                 print(f"Redo niet geïmplementeerd voor actie: {action.type}")

            if success:
                self.undo_stack.append(action)
                self.unsaved_changes = True
                return True
        except Exception as e:
            print(f"Fout tijdens redo van {action.type}: {e}")
            # Actie terugzetten op redo stack?
            self.redo_stack.append(action) # Probeer terug te zetten
        return False

    def _restore_from_dict(self, state_dict):
        """Herstelt de volledige model staat van een dictionary (voor undo load/new)."""
        # Zorg ervoor dat state_dict niet None is
        if not state_dict:
             print("Fout: Kan staat niet herstellen vanuit lege dictionary.")
             # Mogelijk terugvallen op new_map() ?
             self.new_map()
             return

        try:
            # --- Herstel Metadata ---
            self.metadata = copy.deepcopy(state_dict.get("metadata", {}))
            # Zet basis defaults als ze missen in de oude staat
            self.width = self.metadata.setdefault("mapWidth", self.config.get("default_map_width", 40))
            self.height = self.metadata.setdefault("mapHeight", self.config.get("default_map_height", 30))
            self.metadata.setdefault("tileWidth", self.config.get("tile_width", 32))
            self.metadata.setdefault("tileHeight", self.config.get("tile_height", 32))
            # Herstel andere belangrijke metadata
            self.metadata.setdefault("infinite", False)
            self.metadata.setdefault("orientation", "orthogonal")
            self.metadata.setdefault("renderorder", "right-down")
            self.metadata.setdefault("version", "1.9") # Ouder formaat misschien?
            self.metadata.setdefault("tiledversion", "1.9.0")
            self.metadata.setdefault("type", "map")
            self.metadata.setdefault("tilesets", [])


            # --- Herstel Lagen ---
            self.layers = []
            next_layer_id_calc = 1
            max_obj_id_calc = 0
            loaded_layers_data = state_dict.get("layers", [])
            for layer_data in loaded_layers_data:
                layer_type = layer_data.get("type")
                layer = None
                if layer_type == "tilelayer":
                    layer = TileLayer.from_dict(layer_data)
                    # Corrigeer eventuele dimensie mismatches
                    if layer.width != self.width or layer.height != self.height:
                        layer.resize(self.width, self.height)
                elif layer_type == "objectgroup":
                    layer = ObjectGroupLayer.from_dict(layer_data, self.width, self.height)
                    for obj in layer.objects:
                        max_obj_id_calc = max(max_obj_id_calc, obj.id)
                else: # Oude formaat had geen type, neem aan tilelayer
                    print("Info: Laag zonder type gevonden, aanname: tilelayer.")
                    # Probeer als TileLayer te laden (vereist aanpassing from_dict of aparte logica)
                    # Voor nu, maken we een lege TileLayer
                    layer = TileLayer(name=layer_data.get("name", f"Laag {next_layer_id_calc}"),
                                      width=self.width, height=self.height,
                                      id=layer_data.get("id", next_layer_id_calc))
                    # Probeer data te laden als 2D array
                    old_data = layer_data.get("data", [])
                    if isinstance(old_data, list) and len(old_data) == self.height:
                        layer.data = [[int(c) if str(c).isdigit() else 0 for c in r] for r in old_data]


                if layer:
                    layer.id = layer_data.get("id", next_layer_id_calc)
                    self.layers.append(layer)
                    next_layer_id_calc = max(next_layer_id_calc, layer.id + 1)

            # Herstel next IDs
            self.metadata["nextlayerid"] = max(next_layer_id_calc, state_dict.get("nextlayerid", next_layer_id_calc))
            MapObject._next_id = max(max_obj_id_calc + 1, 1)
            self.metadata["nextobjectid"] = max(MapObject._next_id, state_dict.get("nextobjectid", MapObject._next_id))


            # Herstel actieve laag index uit oude formaat indien aanwezig
            self.active_layer_index = state_dict.get("active_layer_index", 0)
            if self.active_layer_index >= len(self.layers):
                 self.active_layer_index = max(0, len(self.layers) - 1)

            # current_file en unsaved_changes worden niet direct hersteld door undo
            # De aanroepende undo methode moet dit mogelijk afhandelen

        except Exception as e:
            print(f"Fout tijdens herstellen van staat: {e}. Model kan inconsistent zijn.")
            # Terugvallen op een nieuwe, lege kaart?
            # self.new_map() # Riskant

# --- Einde van map_model.py ---