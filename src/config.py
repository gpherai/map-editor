# src/config.py
# Centrale configuratie voor de Map Editor

import os
import json
from pathlib import Path


class Config:
    """Centrale configuratieklasse voor de Map Editor."""

    # Default configuratie waarden
    _defaults = {
        # Algemene instellingen
        "app_name": "Tri-Sharira Map Editor",
        "version": "1.0.0",
        "theme_mode": "dark",  # dark, light of system
        "color_theme": "blue",  # blue, green, dark-blue
        # Map instellingen
        "default_map_width": 40,
        "default_map_height": 30,
        "default_tile": "G",
        "file_delimiter": "|",
        "grid_color": "#666666",
        "show_grid": True,
        # UI instellingen
        "window_width": 1280,
        "window_height": 800,
        "canvas_zoom_factor": 1.0,
        "show_minimap": True,
        "minimap_size": 200,
        "autosave_interval": 5,  # minuten, 0 = uit
        "max_undo_steps": 50,
        "show_tooltips": True,
        # Paden
        "default_save_dir": "./data",
        "export_dir": "./exports",
        "recent_files_max": 10,
        "recent_files": [],
        # Terrein categorieën en types
        "terrain_categories": {
            "Basis terrein": {
                "G": "Gras",
                "W": "Water",
                "P": "Pad",
                "Br": "Brug",
                "Be": "Berg",
            },
            "Gebouwen": {"H": "Huis", "Te": "Tempel/Ashram"},
            "Vegetatie": {"Tr": "Boom"},
            "NPC's": {
                "NE": "Dorpsoudste",
                "NH": "Handelaar",
                "NJ": "Jongere",
                "NS": "Spirituele meester",
                "V": "Handelaar (oude aanduiding)",
            },
            "Overig": {" ": "Leeg"},
        },
        # Terrein kleuren
        "terrain_colors": {
            "G": "#90EE90",  # Lichtgroen voor gras
            "W": "#ADD8E6",  # Lichtblauw voor water
            "P": "#DEB887",  # Beige voor pad
            "Tr": "#228B22",  # Donkergroen voor boom
            "H": "#CD853F",  # Zandkleur voor huis
            "Te": "#FFD700",  # Goud voor tempel/ashram
            "Br": "#8B4513",  # Donkerbruin voor brug
            "Be": "#A0522D",  # Bruin voor berg
            "NE": "#4169E1",  # Royal blue voor dorpsoudste
            "NH": "#FFD700",  # Goud voor handelaar
            "NJ": "#32CD32",  # Lime green voor jongere
            "NS": "#9932CC",  # Paars voor spirituele meester
            "V": "#FFD700",  # Goud voor handelaar (oude aanduiding)
            " ": "#FFFFFF",  # Wit voor leeg
        },
        # Laag instellingen (voor layer-based implementatie)
        "default_layers": [
            {"name": "Terrein", "visible": True, "locked": False},
            {"name": "Objecten", "visible": True, "locked": False},
            {"name": "NPC's", "visible": True, "locked": False},
        ],
        "active_layer": 0,
    }

    # Instantie attributen
    _instance = None
    _config_file = None
    _config_data = None

    def __new__(cls, config_file=None):
        """Singleton implementatie - zorgt dat er maar één configuratie-instantie is."""
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)

            # Bepaal config bestandspad
            if config_file is None:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                cls._config_file = os.path.join(base_dir, "config.json")
            else:
                cls._config_file = config_file

            # Initialize de configuratie
            cls._instance._initialize()

        return cls._instance

    def _initialize(self):
        """Laadt de configuratie uit bestand of initialiseert met defaults."""
        self._config_data = self._defaults.copy()

        # Probeer configuratie te laden uit bestand
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    # Update defaults met geladen waarden
                    self._update_config_recursive(self._config_data, loaded_config)
                print(f"Configuratie geladen uit: {self._config_file}")
            except Exception as e:
                print(f"Fout bij laden configuratie: {e}")
                # Ga verder met defaults
        else:
            print(
                f"Geen configuratiebestand gevonden op {
                    self._config_file}. Defaults worden gebruikt."
            )
            # Sla defaults op als nieuw config bestand
            self._save_config()

    def _update_config_recursive(self, target, source):
        """Update configuratie recursief, behoud structuur en onbekende keys."""
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                # Recursief updaten voor geneste dictionaries
                self._update_config_recursive(target[key], value)
            else:
                # Direct updaten voor niet-dict waarden of onbekende keys
                target[key] = value

    def _save_config(self):
        """Slaat de huidige configuratie op naar bestand."""
        try:
            # Zorg dat de directory bestaat
            os.makedirs(os.path.dirname(self._config_file), exist_ok=True)

            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._config_data, f, indent=4, ensure_ascii=False)
            print(f"Configuratie opgeslagen naar: {self._config_file}")
            return True
        except Exception as e:
            print(f"Fout bij opslaan configuratie: {e}")
            return False

    def get(self, key, default=None):
        """Haalt een configuratiewaarde op via een key."""
        # Support voor nested keys met dot notatie (bijv. "terrain_colors.G")
        if "." in key:
            parts = key.split(".")
            value = self._config_data
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value

        return self._config_data.get(key, default)

    def set(self, key, value, auto_save=True):
        """Stelt een configuratiewaarde in en slaat optioneel direct op."""
        # Support voor nested keys met dot notatie
        if "." in key:
            parts = key.split(".")
            target = self._config_data
            for part in parts[:-1]:  # Alle delen behalve de laatste
                if part not in target:
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = value
        else:
            self._config_data[key] = value

        # Automatisch opslaan indien gewenst
        if auto_save:
            return self._save_config()
        return True

    def get_all(self):
        """Geeft een kopie van alle configuratiedata."""
        return self._config_data.copy()

    def reset_to_defaults(self, save=True):
        """Reset alle configuratie naar standaardwaarden."""
        self._config_data = self._defaults.copy()
        if save:
            return self._save_config()
        return True

    def add_recent_file(self, filepath):
        """Voegt een bestand toe aan de lijst met recente bestanden."""
        filepath = str(Path(filepath).resolve())  # Normaliseer pad
        recent_files = self.get("recent_files", [])
        max_files = self.get("recent_files_max", 10)

        # Verwijder als het al bestaat (om het bovenaan te zetten)
        if filepath in recent_files:
            recent_files.remove(filepath)

        # Voeg toe aan het begin
        recent_files.insert(0, filepath)

        # Houd maximaal aantal bij
        if len(recent_files) > max_files:
            recent_files = recent_files[:max_files]

        self.set("recent_files", recent_files)

    def get_terrain_types(self):
        """Helper functie die een platte lijst van alle terrein types geeft."""
        result = {}
        for category in self.get("terrain_categories", {}).values():
            result.update(category)
        return result
