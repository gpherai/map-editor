# src/ui/terrain_panel.py
# Paneel voor terreintype selectie in Map Editor

import customtkinter as ctk
import tkinter as tk
from src.utils.tooltip import CTkToolTip


class TerrainButton(ctk.CTkButton):
    """Aangepaste knop voor terreintypen met juiste kleuren en labels."""

    def __init__(self, parent, terrain_id, description, color, on_click=None, **kwargs):
        """
        Creëert een terreinknop.

        Args:
            parent: Het ouderwidget
            terrain_id (str): ID/code van het terreintype
            description (str): Omschrijving van het terreintype
            color (str): Kleur (hex) voor het terreintype
            on_click: Callback functie bij klikken
            **kwargs: Extra argumenten voor CTkButton
        """
        self.terrain_id = terrain_id
        self.description = description
        self.terrain_color = color

        # Bereken contrasterende tekstkleur op basis van achtergrondkleur
        text_color = self._get_contrasting_color(color)

        # Maak button label
        if len(terrain_id) <= 2:
            # Voor korte codes, toon code en beschrijving
            button_text = f"{terrain_id} - {description}"
        else:
            # Voor langere codes, alleen de code
            button_text = terrain_id

        # Creëer de knop
        super().__init__(
            parent,
            text=button_text,
            fg_color=color,
            text_color=text_color,
            command=lambda: on_click(terrain_id) if on_click else None,
            **kwargs,
        )

        # Tooltips voor langere terreintypen
        if len(terrain_id) > 2:
            CTkToolTip(self, f"{terrain_id}: {description}")

    def _get_contrasting_color(self, hex_color):
        """
        Bepaal of witte of zwarte tekst beter leesbaar is op de gegeven achtergrondkleur.

        Args:
            hex_color (str): Hex kleur code zoals "#RRGGBB"

        Returns:
            str: "#FFFFFF" voor wit of "#000000" voor zwart
        """
        # Verwijder # indien aanwezig
        hex_color = hex_color.lstrip("#")

        # Converteer naar RGB
        r, g, b = (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )

        # Bereken luminantie
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255

        # Als licht, gebruik donkere tekst, anders lichte tekst
        return "#000000" if luminance > 0.5 else "#FFFFFF"


class TerrainPanel(ctk.CTkScrollableFrame):
    """Paneel voor het selecteren van terreintypen met categorieën."""

    def __init__(self, parent, config, on_terrain_selected=None, **kwargs):
        """
        Initialiseert het terreinpaneel.

        Args:
            parent: Het ouderwidget
            config: Configuratie object
            on_terrain_selected: Callback voor terrein selectie
            **kwargs: Extra argumenten voor CTkScrollableFrame
        """
        super().__init__(parent, **kwargs)

        self.config = config
        self.on_terrain_selected = on_terrain_selected
        self.current_terrain_id = config.get("default_tile", "G")
        self.terrain_buttons = {}

        # Maakt UI elementen
        self._create_ui()

        # Voeg tooltips toe
        self._setup_tooltips()

    def _create_ui(self):
        """Bouwt de UI van het terreinpaneel op."""
        # Titel
        self.title_label = ctk.CTkLabel(
            self, text="Terreintypen", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.title_label.pack(pady=(0, 10), anchor="w")

        # Zoekbalk
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.pack(fill="x", pady=(0, 10))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filter_terrain_types)

        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="Zoeken...",
            textvariable=self.search_var,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.clear_button = ctk.CTkButton(
            self.search_frame, text="×", width=30, command=self._clear_search
        )
        self.clear_button.pack(side="right")

        # Terrein indicator
        self.indicator_frame = ctk.CTkFrame(self)
        self.indicator_frame.pack(fill="x", pady=(0, 10))

        self.indicator_label = ctk.CTkLabel(
            self.indicator_frame, text="Geselecteerd:", anchor="w"
        )
        self.indicator_label.pack(side="left", padx=5, pady=5)

        self.selected_terrain_label = ctk.CTkLabel(
            self.indicator_frame,
            text=self.current_terrain_id,
            anchor="w",
            font=ctk.CTkFont(weight="bold"),
        )
        self.selected_terrain_label.pack(side="left", padx=(0, 5), pady=5)

        # Categorieën en terreintypen
        self._populate_terrain_types()

    def _setup_tooltips(self):
        """Voegt tooltips toe aan de elementen in het terrein paneel."""
        # Tooltip voor het titellabel
        CTkToolTip(
            self.title_label, "Beschikbare terreintypen voor plaatsing op de kaart"
        )

        # Tooltip voor de zoekbalk
        CTkToolTip(self.search_entry, "Zoek naar specifieke terreintypen")
        CTkToolTip(self.clear_button, "Wis zoekopdracht")

        # Tooltip voor de terrein indicator
        CTkToolTip(self.indicator_frame, "Huidig geselecteerd terreintype")

    def _populate_terrain_types(self):
        """Vult het paneel met terreintypen uit de configuratie."""
        # Terrein categorieën en types uit config
        terrain_categories = self.config.get("terrain_categories", {})
        terrain_colors = self.config.get("terrain_colors", {})

        # Verwijder bestaande widgets, behalve bovenste elementen
        for widget in self.winfo_children():
            if widget not in [
                self.title_label,
                self.search_frame,
                self.indicator_frame,
            ]:
                widget.destroy()

        self.terrain_buttons = {}

        # Voor gefilterde weergave
        search_text = self.search_var.get().lower()

        # Maak frames voor elke categorie
        for category_name, types in terrain_categories.items():
            # Filter voor huidige zoekopdracht
            filtered_types = {
                code: desc
                for code, desc in types.items()
                if search_text in code.lower() or search_text in desc.lower()
            }

            # Skip lege categorieën bij filteren
            if search_text and not filtered_types:
                continue

            # Categorie header
            category_frame = ctk.CTkFrame(self)
            category_frame.pack(fill="x", pady=(0, 5))

            category_label = ctk.CTkLabel(
                category_frame,
                text=category_name,
                anchor="w",
                font=ctk.CTkFont(weight="bold"),
            )
            category_label.pack(fill="x", padx=5, pady=5)

            # Voeg tooltip toe aan categorie label
            CTkToolTip(
                category_label, f"Terreintypen in de categorie '{category_name}'"
            )

            # Terreintypen in deze categorie
            types_frame = ctk.CTkFrame(self)
            types_frame.pack(fill="x", pady=(0, 10))
            types_frame.grid_columnconfigure(0, weight=1)

            # Maak knoppen voor elk terreintype
            row = 0
            for terrain_code, terrain_desc in sorted(filtered_types.items()):
                # Haal terreinkleur op, of standaardkleur
                color = terrain_colors.get(terrain_code, "#CCCCCC")

                # Maak terreinknop
                button = TerrainButton(
                    types_frame,
                    terrain_id=terrain_code,
                    description=terrain_desc,
                    color=color,
                    on_click=self._on_terrain_button_click,
                    height=32,
                )
                button.grid(row=row, column=0, sticky="ew", padx=5, pady=2)

                # Sla de knop op voor later gebruik
                self.terrain_buttons[terrain_code] = button

                row += 1

    def _filter_terrain_types(self, *args):
        """Filtert terreintypen op basis van zoekopdracht."""
        self._populate_terrain_types()

    def _clear_search(self):
        """Maakt het zoekveld leeg."""
        self.search_var.set("")

    def _on_terrain_button_click(self, terrain_id):
        """Verwerkt klikken op een terreinknop."""
        # Highlight de geselecteerde knop
        self._highlight_selected_terrain(terrain_id)

        # Update de huidige terrein indicator
        self.current_terrain_id = terrain_id
        terrain_types = self.config.get_terrain_types()
        desc = terrain_types.get(terrain_id, "")
        self.selected_terrain_label.configure(text=f"{terrain_id} - {desc}")

        # Roep de callback aan indien ingesteld
        if self.on_terrain_selected:
            self.on_terrain_selected(terrain_id)

    def _highlight_selected_terrain(self, terrain_id):
        """
        Markeert het geselecteerde terreintype visueel.

        Args:
            terrain_id (str): ID van het geselecteerde terrein
        """
        # Herstel alle knoppen naar normale staat
        for code, button in self.terrain_buttons.items():
            if code != terrain_id:
                # Herstel normale kleur
                button.configure(border_width=0)
            else:
                # Markeer geselecteerde knop
                button.configure(border_width=2, border_color="#FF5500")

    def set_current_terrain(self, terrain_id):
        """
        Stelt het huidige terreintype in.

        Args:
            terrain_id (str): ID van het terreintype
        """
        if terrain_id in self.terrain_buttons:
            self._on_terrain_button_click(terrain_id)
