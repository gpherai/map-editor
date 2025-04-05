# src/models/map_model.py
# Model voor de Map Editor - beheert de kaartdata en operaties

import os
import json
from collections import deque
import time


class MapAction:
    """Klasse voor het bijhouden van acties voor undo/redo-functionaliteit."""

    def __init__(self, action_type, data):
        """
        Initialiseert een nieuwe actie.

        Args:
            action_type (str): Type actie ('set_cell', 'resize', 'fill', etc.)
            data (dict): Data specifiek voor het actietype
        """
        self.type = action_type
        self.data = data
        self.timestamp = time.time()


class Layer:
    """Een enkele laag in de kaart, bevat data voor één type element (terrein, objecten, etc.)."""

    def __init__(
        self, name, width, height, default_value=" ", visible=True, locked=False
    ):
        """
        Initialiseert een nieuwe laag.

        Args:
            name (str): Naam van de laag
            width (int): Breedte van de laag in cellen
            height (int): Hoogte van de laag in cellen
            default_value (str): Standaardwaarde voor nieuwe cellen
            visible (bool): Of de laag zichtbaar is
            locked (bool): Of de laag vergrendeld is (niet bewerkbaar)
        """
        self.name = name
        self.width = width
        self.height = height
        self.visible = visible
        self.locked = locked
        self.data = [[default_value for _ in range(width)] for _ in range(height)]

    def set_cell(self, row, col, value):
        """
        Stelt de waarde van een cel in.

        Args:
            row (int): Rij-index
            col (int): Kolom-index
            value (str): Nieuwe waarde

        Returns:
            str: Oude waarde van de cel
        """
        if 0 <= row < self.height and 0 <= col < self.width:
            old_value = self.data[row][col]
            self.data[row][col] = value
            return old_value
        return None

    def get_cell(self, row, col):
        """
        Haalt de waarde van een cel op.

        Args:
            row (int): Rij-index
            col (int): Kolom-index

        Returns:
            str: Waarde van de cel of None als buiten bereik
        """
        if 0 <= row < self.height and 0 <= col < self.width:
            return self.data[row][col]
        return None

    def resize(self, new_width, new_height, default_value=" "):
        """
        Past de grootte van de laag aan.

        Args:
            new_width (int): Nieuwe breedte
            new_height (int): Nieuwe hoogte
            default_value (str): Waarde voor nieuwe cellen

        Returns:
            tuple: Oude afmetingen (width, height)
        """
        old_width, old_height = self.width, self.height

        # Maak nieuwe data array
        new_data = [
            [default_value for _ in range(new_width)] for _ in range(new_height)
        ]

        # Kopieer bestaande data waar mogelijk
        for row in range(min(self.height, new_height)):
            for col in range(min(self.width, new_width)):
                new_data[row][col] = self.data[row][col]

        # Update layer properties
        self.width = new_width
        self.height = new_height
        self.data = new_data

        return (old_width, old_height)

    def fill(self, value, start_row=None, start_col=None, end_row=None, end_col=None):
        """
        Vult een gebied van de laag met een waarde.

        Args:
            value (str): Waarde om in te vullen
            start_row (int, optional): Begin-rij, standaard hele laag
            start_col (int, optional): Begin-kolom, standaard hele laag
            end_row (int, optional): Eind-rij, standaard hele laag
            end_col (int, optional): Eind-kolom, standaard hele laag

        Returns:
            list: Lijst van (row, col, oude_waarde) tuples die gewijzigd zijn
        """
        # Standaard hele laag als gebied niet gespecificeerd is
        if start_row is None:
            start_row = 0
        if start_col is None:
            start_col = 0
        if end_row is None:
            end_row = self.height - 1
        if end_col is None:
            end_col = self.width - 1

        # Begrens binnen laagafmetingen
        start_row = max(0, min(start_row, self.height - 1))
        start_col = max(0, min(start_col, self.width - 1))
        end_row = max(0, min(end_row, self.height - 1))
        end_col = max(0, min(end_col, self.width - 1))

        # Houd gewijzigde cellen bij
        changed_cells = []

        # Vul het gebied
        for row in range(start_row, end_row + 1):
            for col in range(start_col, end_col + 1):
                old_value = self.data[row][col]
                if old_value != value:  # Alleen bijhouden als het echt verandert
                    self.data[row][col] = value
                    changed_cells.append((row, col, old_value))

        return changed_cells

    def to_dict(self):
        """Converteert laag naar een dictionary voor serialisatie."""
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "visible": self.visible,
            "locked": self.locked,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, data_dict):
        """
        Maakt een Layer-instantie van een dictionary.

        Args:
            data_dict (dict): Dictionary met laagdata

        Returns:
            Layer: Nieuwe Layer-instantie
        """
        layer = cls(
            name=data_dict["name"],
            width=data_dict["width"],
            height=data_dict["height"],
            visible=data_dict.get("visible", True),
            locked=data_dict.get("locked", False),
        )
        layer.data = data_dict["data"]
        return layer


class MapModel:
    """Model voor de kaartdata, ondersteunt meerdere lagen en undo/redo."""

    def __init__(self, config):
        """
        Initialiseert het kaartmodel.

        Args:
            config: Config-instantie met instellingen
        """
        self.config = config

        # Basisattributen
        self.width = config.get("default_map_width", 40)
        self.height = config.get("default_map_height", 30)
        self.current_file = None
        self.unsaved_changes = False
        self.active_layer_index = 0

        # Lagen initaliseren
        self.layers = []
        default_layers = config.get("default_layers", [])

        if default_layers:
            # Maak lagen uit configuratie
            for layer_config in default_layers:
                self.layers.append(
                    Layer(
                        name=layer_config["name"],
                        width=self.width,
                        height=self.height,
                        default_value=(
                            config.get("default_tile", "G")
                            if layer_config["name"] == "Terrein"
                            else " "
                        ),
                        visible=layer_config.get("visible", True),
                        locked=layer_config.get("locked", False),
                    )
                )
        else:
            # Standaard laag als er geen in de configuratie staan
            self.layers.append(
                Layer(
                    name="Terrein",
                    width=self.width,
                    height=self.height,
                    default_value=config.get("default_tile", "G"),
                )
            )

        # Undo/redo stacks
        self.undo_stack = deque(maxlen=config.get("max_undo_steps", 50))
        self.redo_stack = deque(maxlen=config.get("max_undo_steps", 50))

    @property
    def active_layer(self):
        """Geeft de actieve laag."""
        if 0 <= self.active_layer_index < len(self.layers):
            return self.layers[self.active_layer_index]
        return None

    def set_active_layer(self, index):
        """
        Stelt de actieve laag in.

        Args:
            index (int): Index van de laag

        Returns:
            bool: True als succesvol, False als index niet geldig is
        """
        if 0 <= index < len(self.layers):
            self.active_layer_index = index
            return True
        return False

    def add_layer(self, name, default_value=" ", visible=True, locked=False):
        """
        Voegt een nieuwe laag toe.

        Args:
            name (str): Naam van de laag
            default_value (str): Standaardwaarde voor cellen
            visible (bool): Of de laag zichtbaar is
            locked (bool): Of de laag vergrendeld is

        Returns:
            int: Index van de nieuwe laag
        """
        new_layer = Layer(
            name=name,
            width=self.width,
            height=self.height,
            default_value=default_value,
            visible=visible,
            locked=locked,
        )

        self.layers.append(new_layer)
        new_index = len(self.layers) - 1

        # Registreer actie voor undo
        self._add_action("add_layer", {"layer_index": new_index})

        self.unsaved_changes = True

        return new_index

    def remove_layer(self, index):
        """
        Verwijdert een laag.

        Args:
            index (int): Index van de laag om te verwijderen

        Returns:
            Layer: De verwijderde laag, of None als de index niet geldig was
        """
        if (
            0 <= index < len(self.layers) and len(self.layers) > 1
        ):  # Laat minimaal 1 laag over
            # Registreer actie voor undo
            self._add_action(
                "remove_layer",
                {"layer_index": index, "layer_data": self.layers[index].to_dict()},
            )

            removed_layer = self.layers.pop(index)

            # Update active_layer_index indien nodig
            if self.active_layer_index >= len(self.layers):
                self.active_layer_index = len(self.layers) - 1

            self.unsaved_changes = True
            return removed_layer

        return None

    def move_layer(self, delta):
        """
        Verplaatst de actieve laag omhoog of omlaag in de lagenstapel.

        Args:
            delta (int): Verplaatsingsrichting, -1 voor omhoog, 1 voor omlaag

        Returns:
            bool: True als de verplaatsing succesvol was, anders False
        """
        # Check of er een actieve laag is
        if self.active_layer_index is None:
            return False
            
        # Bereken nieuwe index
        new_index = self.active_layer_index + delta
        
        # Valideer nieuwe index
        if not (0 <= new_index < len(self.layers)):
            return False  # Buiten bereik, kan niet verplaatsen
        
        # Sla oude staat op voor undo
        self._add_action(
            "move_layer",
            {
                "old_index": self.active_layer_index,
                "new_index": new_index
            }
        )
        
        # Verplaats laag in de lijst
        layer = self.layers.pop(self.active_layer_index)
        self.layers.insert(new_index, layer)
        
        # Update actieve laag index
        self.active_layer_index = new_index
        
        # Geef wijziging aan
        self.unsaved_changes = True
        
        return True

    def set_cell(self, row, col, value, layer_index=None):
        """
        Stelt de waarde van een cel in.

        Args:
            row (int): Rij-index
            col (int): Kolom-index
            value (str): Nieuwe waarde
            layer_index (int, optional): Index van de laag, standaard actieve laag

        Returns:
            tuple: (succes, oude_waarde)
        """
        layer = (
            self.active_layer
            if layer_index is None
            else (
                self.layers[layer_index]
                if 0 <= layer_index < len(self.layers)
                else None
            )
        )

        if layer and not layer.locked:
            old_value = layer.get_cell(row, col)

            if old_value is not None and old_value != value:
                layer.set_cell(row, col, value)

                # Registreer actie voor undo
                self._add_action(
                    "set_cell",
                    {
                        "row": row,
                        "col": col,
                        "old_value": old_value,
                        "new_value": value,
                        "layer_index": (
                            layer_index
                            if layer_index is not None
                            else self.active_layer_index
                        ),
                    },
                )

                self.unsaved_changes = True
                return (True, old_value)

        return (False, None)

    def get_cell(self, row, col, layer_index=None):
        """
        Haalt de waarde van een cel op.

        Args:
            row (int): Rij-index
            col (int): Kolom-index
            layer_index (int, optional): Index van de laag, standaard actieve laag

        Returns:
            str: Waarde van de cel of None als buiten bereik
        """
        layer = (
            self.active_layer
            if layer_index is None
            else (
                self.layers[layer_index]
                if 0 <= layer_index < len(self.layers)
                else None
            )
        )

        if layer:
            return layer.get_cell(row, col)

        return None

    def get_cell_at_all_layers(self, row, col):
        """
        Haalt waarden op van een cel in alle zichtbare lagen.

        Args:
            row (int): Rij-index
            col (int): Kolom-index

        Returns:
            list: Lijst van (laag_index, waarde) tuples
        """
        result = []

        for i, layer in enumerate(self.layers):
            if layer.visible:
                value = layer.get_cell(row, col)
                if value and value != " ":  # Skip lege cellen
                    result.append((i, value))

        return result

    def get_top_cell(self, row, col):
        """
        Haalt de bovenste niet-lege waarde op van alle zichtbare lagen.

        Args:
            row (int): Rij-index
            col (int): Kolom-index

        Returns:
            tuple: (laag_index, waarde) of (None, None) als alles leeg is
        """
        # Loop van boven naar beneden door de lagen
        for i in range(len(self.layers) - 1, -1, -1):
            layer = self.layers[i]
            if layer.visible:
                value = layer.get_cell(row, col)
                if value and value != " ":  # Skip lege cellen
                    return (i, value)

        return (None, None)

    def resize(self, new_width, new_height):
        """
        Past de grootte van alle lagen aan.

        Args:
            new_width (int): Nieuwe breedte
            new_height (int): Nieuwe hoogte

        Returns:
            tuple: (oude_breedte, oude_hoogte)
        """
        old_width, old_height = self.width, self.height

        # Bewaar data voor undo
        old_layers_data = []
        for layer in self.layers:
            old_layers_data.append(
                {"index": self.layers.index(layer), "data": layer.to_dict()}
            )

        # Registreer actie voor undo
        self._add_action(
            "resize",
            {
                "old_width": old_width,
                "old_height": old_height,
                "new_width": new_width,
                "new_height": new_height,
                "old_layers_data": old_layers_data,
            },
        )

        # Update alle lagen
        for layer in self.layers:
            layer.resize(new_width, new_height, " ")

        self.width = new_width
        self.height = new_height
        self.unsaved_changes = True

        return (old_width, old_height)

    def fill(
        self,
        value,
        layer_index=None,
        start_row=None,
        start_col=None,
        end_row=None,
        end_col=None,
    ):
        """
        Vult een gebied van de kaart met een waarde.

        Args:
            value (str): Waarde om in te vullen
            layer_index (int, optional): Index van de laag, standaard actieve laag
            start_row (int, optional): Begin-rij, standaard hele laag
            start_col (int, optional): Begin-kolom, standaard hele laag
            end_row (int, optional): Eind-rij, standaard hele laag
            end_col (int, optional): Eind-kolom, standaard hele laag

        Returns:
            bool: True als succesvol
        """
        layer = (
            self.active_layer
            if layer_index is None
            else (
                self.layers[layer_index]
                if 0 <= layer_index < len(self.layers)
                else None
            )
        )

        if layer and not layer.locked:
            # Vul het gebied en ontvang gewijzigde cellen
            changed_cells = layer.fill(value, start_row, start_col, end_row, end_col)

            if changed_cells:
                # Registreer actie voor undo
                self._add_action(
                    "fill",
                    {
                        "layer_index": (
                            layer_index
                            if layer_index is not None
                            else self.active_layer_index
                        ),
                        "changed_cells": changed_cells,
                    },
                )

                self.unsaved_changes = True
                return True

        return False

    def toggle_layer_visibility(self, index):
        """
        Schakelt de zichtbaarheid van een laag.

        Args:
            index (int): Index van de laag

        Returns:
            bool: Nieuwe zichtbaarheidsstatus
        """
        if 0 <= index < len(self.layers):
            layer = self.layers[index]
            old_visible = layer.visible
            layer.visible = not layer.visible

            # Registreer actie voor undo
            self._add_action(
                "toggle_visibility",
                {
                    "layer_index": index,
                    "old_visible": old_visible,
                    "new_visible": layer.visible,
                },
            )

            return layer.visible

        return False

    def toggle_layer_lock(self, index):
        """
        Schakelt de vergrendeling van een laag.

        Args:
            index (int): Index van de laag

        Returns:
            bool: Nieuwe vergrendelingsstatus
        """
        if 0 <= index < len(self.layers):
            layer = self.layers[index]
            old_locked = layer.locked
            layer.locked = not layer.locked

            # Registreer actie voor undo
            self._add_action(
                "toggle_lock",
                {
                    "layer_index": index,
                    "old_locked": old_locked,
                    "new_locked": layer.locked,
                },
            )

            return layer.locked

        return False

    def new_map(self, width=None, height=None):
        """
        Maakt een nieuwe, lege kaart.

        Args:
            width (int, optional): Breedte, standaard uit config
            height (int, optional): Hoogte, standaard uit config

        Returns:
            bool: True als succecvol
        """
        if width is None:
            width = self.config.get("default_map_width", 40)
        if height is None:
            height = self.config.get("default_map_height", 30)

        # Registreer actie voor undo
        old_model_state = self.to_dict()
        self._add_action("new_map", {"old_state": old_model_state})

        # Reset attributen
        self.width = width
        self.height = height
        self.current_file = None

        # Maak nieuwe lagen
        self.layers = []
        default_layers = self.config.get("default_layers", [])

        if default_layers:
            for layer_config in default_layers:
                self.layers.append(
                    Layer(
                        name=layer_config["name"],
                        width=self.width,
                        height=self.height,
                        default_value=(
                            self.config.get("default_tile", "G")
                            if layer_config["name"] == "Terrein"
                            else " "
                        ),
                        visible=layer_config.get("visible", True),
                        locked=layer_config.get("locked", False),
                    )
                )
        else:
            self.layers.append(
                Layer(
                    name="Terrein",
                    width=self.width,
                    height=self.height,
                    default_value=self.config.get("default_tile", "G"),
                )
            )

        self.active_layer_index = 0

        # Reset undo/redo stacks
        self.undo_stack.clear()
        self.redo_stack.clear()

        self.unsaved_changes = False

        return True

    def load_map(self, filepath):
        """
        Laadt een kaart uit een bestand (alleen JSON-formaat).

        Args:
            filepath (str): Pad naar het bestand

        Returns:
            bool: True als succesvol
        """
        if not os.path.exists(filepath):
            return False

        try:
            # Bewaar oude status voor undo
            old_model_state = self.to_dict()

            # Controleer of het een JSON-bestand is
            if not filepath.lower().endswith(".json"):
                print(
                    f"Fout: Alleen JSON-bestanden worden ondersteund. Bestand moet eindigen op .json"
                )
                return False

            # JSON formaat laden
            return self._load_from_json(filepath)

        except Exception as e:
            print(f"Fout bij laden kaart: {e}")
            return False

    # De methoden _load_delimited en _load_ascii zijn verwijderd omdat we nu alleen JSON ondersteunen

    def _load_from_json(self, filepath):
        """Laadt een kaart in JSON formaat."""
        try:
            # Bewaar oude status voor undo
            old_model_state = self.to_dict()

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Basis kaartinfo laden
            self.width = data.get("width", 40)
            self.height = data.get("height", 30)

            # Lagen laden
            self.layers = []
            for layer_data in data.get("layers", []):
                self.layers.append(Layer.from_dict(layer_data))

            # Als er geen lagen zijn, maak een standaard laag
            if not self.layers:
                self.layers.append(
                    Layer(
                        name="Terrein",
                        width=self.width,
                        height=self.height,
                        default_value=self.config.get("default_tile", "G"),
                    )
                )

            self.active_layer_index = data.get("active_layer_index", 0)
            if self.active_layer_index >= len(self.layers):
                self.active_layer_index = 0

            # Registreer actie voor undo
            self._add_action(
                "load_map", {"old_state": old_model_state, "new_state": self.to_dict()}
            )

            self.current_file = filepath
            self.unsaved_changes = False

            # Voeg toe aan recente bestanden
            self.config.add_recent_file(filepath)

            return True

        except Exception as e:
            print(f"Fout bij laden JSON kaart: {e}")
            return False

    def save_map(self, filepath=None):
        """
        Slaat de kaart op naar een bestand (alleen JSON-formaat).

        Args:
            filepath (str, optional): Pad om naar op te slaan, standaard current_file

        Returns:
            bool: True als succesvol
        """
        if filepath is None:
            filepath = self.current_file

        if not filepath:
            return False

        try:
            # Maak de directory aan als deze niet bestaat
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

            # Zorg dat het bestand eindigt op .json
            if not filepath.lower().endswith(".json"):
                filepath += ".json"

            # Sla op als JSON
            success = self._save_to_json(filepath)

            if success:
                self.current_file = filepath
                self.unsaved_changes = False

                # Voeg toe aan recente bestanden
                self.config.add_recent_file(filepath)

            return success

        except Exception as e:
            print(f"Fout bij opslaan kaart: {e}")
            return False

    # De methoden _save_delimited en _save_as_ascii zijn verwijderd omdat we nu alleen JSON ondersteunen

    def _save_to_json(self, filepath):
        """Slaat de kaart op in JSON formaat (ondersteunt alle features)."""
        try:
            # Volledige model data als dictionary
            data = self.to_dict()

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return True

        except Exception as e:
            print(f"Fout bij opslaan JSON kaart: {e}")
            return False

    def export_to_string(self):
        """
        Exporteert de kaart als JSON string.

        Returns:
            str: De kaart als JSON string
        """
        # Export als JSON string
        data = self.to_dict()
        return json.dumps(data, indent=2)

    def to_dict(self):
        """Converteert het model naar een dictionary voor JSON-serialisatie."""
        return {
            "width": self.width,
            "height": self.height,
            "active_layer_index": self.active_layer_index,
            "layers": [layer.to_dict() for layer in self.layers],
            "version": "1.0",
        }

    def _add_action(self, action_type, data):
        """
        Voegt een actie toe aan de undo-stack.

        Args:
            action_type (str): Type actie
            data (dict): Data voor de actie
        """
        self.undo_stack.append(MapAction(action_type, data))
        self.redo_stack.clear()  # Wis redo-stack na nieuwe actie

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
        """
        Maakt de laatste actie ongedaan.

        Returns:
            tuple: (success, action_type)
        """
        if not self.undo_stack:
            return (False, None)

        action = self.undo_stack.pop()

        # Voer de juiste undo-operatie uit op basis van actie-type
        if action.type == "set_cell":
            row = action.data["row"]
            col = action.data["col"]
            old_value = action.data["old_value"]
            layer_index = action.data["layer_index"]

            if 0 <= layer_index < len(self.layers):
                layer = self.layers[layer_index]
                layer.set_cell(row, col, old_value)

        elif action.type == "fill":
            layer_index = action.data["layer_index"]
            changed_cells = action.data["changed_cells"]

            if 0 <= layer_index < len(self.layers):
                layer = self.layers[layer_index]
                for row, col, old_value in changed_cells:
                    layer.set_cell(row, col, old_value)

        elif action.type == "resize":
            old_width = action.data["old_width"]
            old_height = action.data["old_height"]
            old_layers_data = action.data["old_layers_data"]

            self.width = old_width
            self.height = old_height

            # Herstel lagen uit backup
            for layer_data in old_layers_data:
                index = layer_data["index"]
                data = layer_data["data"]

                if 0 <= index < len(self.layers):
                    self.layers[index] = Layer.from_dict(data)

        elif action.type == "add_layer":
            layer_index = action.data["layer_index"]

            if 0 <= layer_index < len(self.layers):
                self.layers.pop(layer_index)

                # Update active_layer_index indien nodig
                if self.active_layer_index >= len(self.layers):
                    self.active_layer_index = len(self.layers) - 1

        elif action.type == "remove_layer":
            layer_index = action.data["layer_index"]
            layer_data = action.data["layer_data"]

            # Voeg de laag weer toe op de juiste index
            if 0 <= layer_index <= len(self.layers):
                self.layers.insert(layer_index, Layer.from_dict(layer_data))

                # Herstel active_layer_index indien nodig
                if layer_index <= self.active_layer_index:
                    self.active_layer_index = min(
                        len(self.layers) - 1, self.active_layer_index + 1
                    )

        elif action.type == "toggle_visibility":
            layer_index = action.data["layer_index"]
            old_visible = action.data["old_visible"]

            if 0 <= layer_index < len(self.layers):
                self.layers[layer_index].visible = old_visible

        elif action.type == "toggle_lock":
            layer_index = action.data["layer_index"]
            old_locked = action.data["old_locked"]

            if 0 <= layer_index < len(self.layers):
                self.layers[layer_index].locked = old_locked

        elif action.type == "new_map" or action.type == "load_map":
            # Volledig herstel van oude status
            old_state = action.data["old_state"]

            self.width = old_state["width"]
            self.height = old_state["height"]
            self.active_layer_index = old_state["active_layer_index"]

            # Herstel lagen
            self.layers = []
            for layer_data in old_state["layers"]:
                self.layers.append(Layer.from_dict(layer_data))

        elif action.type == "move_layer":
            old_index = action.data["old_index"]
            new_index = action.data["new_index"]
            
            # Verplaats terug naar oude positie (undo)
            layer = self.layers.pop(new_index)
            self.layers.insert(old_index, layer)
            
            # Reset actieve laag index
            self.active_layer_index = old_index

        # Bewaar actie in redo-stack
        self.redo_stack.append(action)

        self.unsaved_changes = True

        return (True, action.type)

    def redo(self):
        """
        Doet de laatst ongedaan gemaakte actie opnieuw.

        Returns:
            tuple: (success, action_type)
        """
        if not self.redo_stack:
            return (False, None)

        action = self.redo_stack.pop()

        # Voer de juiste redo-operatie uit op basis van actie-type
        if action.type == "set_cell":
            row = action.data["row"]
            col = action.data["col"]
            new_value = action.data["new_value"]
            layer_index = action.data["layer_index"]

            if 0 <= layer_index < len(self.layers):
                layer = self.layers[layer_index]
                layer.set_cell(row, col, new_value)

        elif action.type == "fill":
            layer_index = action.data["layer_index"]
            changed_cells = action.data["changed_cells"]

            if 0 <= layer_index < len(self.layers):
                layer = self.layers[layer_index]
                # Als we de nieuwe waarde hebben, kunnen we die gebruiken, anders
                # moeten we een extra set_cell actie doen om het opnieuw te vullen
                for next_action in self.redo_stack:
                    if (
                        next_action.type == "set_cell"
                        and next_action.data["layer_index"] == layer_index
                    ):
                        new_value = next_action.data["new_value"]
                        for row, col, _ in changed_cells:
                            layer.set_cell(row, col, new_value)
                        break

        elif action.type == "resize":
            new_width = action.data["new_width"]
            new_height = action.data["new_height"]

            # Pas grootte van alle lagen aan
            for layer in self.layers:
                layer.resize(new_width, new_height, " ")

            self.width = new_width
            self.height = new_height

        elif action.type == "add_layer":
            layer_index = action.data["layer_index"]

            # Als we de laagdata niet hebben, voeg dan een nieuwe standaard laag toe
            # De juiste data zou moeten worden ingesteld door latere set_cell acties
            if 0 <= layer_index <= len(self.layers):
                self.layers.insert(
                    layer_index,
                    Layer(
                        name=f"Layer {layer_index}",
                        width=self.width,
                        height=self.height,
                        default_value=" ",
                    ),
                )

        elif action.type == "remove_layer":
            layer_index = action.data["layer_index"]

            if 0 <= layer_index < len(self.layers):
                self.layers.pop(layer_index)

                # Update active_layer_index indien nodig
                if self.active_layer_index >= len(self.layers):
                    self.active_layer_index = len(self.layers) - 1

        elif action.type == "toggle_visibility":
            layer_index = action.data["layer_index"]
            new_visible = action.data["new_visible"]

            if 0 <= layer_index < len(self.layers):
                self.layers[layer_index].visible = new_visible

        elif action.type == "toggle_lock":
            layer_index = action.data["layer_index"]
            new_locked = action.data["new_locked"]

            if 0 <= layer_index < len(self.layers):
                self.layers[layer_index].locked = new_locked

        elif action.type == "new_map" or action.type == "load_map":
            # Volledig herstel van nieuwe status
            new_state = action.data["new_state"]

            self.width = new_state["width"]
            self.height = new_state["height"]
            self.active_layer_index = new_state["active_layer_index"]

            # Herstel lagen
            self.layers = []
            for layer_data in new_state["layers"]:
                self.layers.append(Layer.from_dict(layer_data))

        elif action.type == "move_layer":
            old_index = action.data["old_index"]
            new_index = action.data["new_index"]
    
            # Verplaats opnieuw naar nieuwe positie (redo)
            layer = self.layers.pop(old_index)
            self.layers.insert(new_index, layer)
    
            # Update actieve laag index
            self.active_layer_index = new_index

        # Bewaar actie in undo-stack
        self.undo_stack.append(action)

        self.unsaved_changes = True

        return (True, action.type)