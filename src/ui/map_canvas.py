# src/ui/map_canvas.py
# Canvas voor het weergeven en bewerken van kaarten in de Map Editor

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os
import math
from PIL import Image, ImageDraw, ImageTk
from src.utils.tooltip import CTkToolTip


class MapCanvas(ctk.CTkFrame):
    """Aangepaste canvas voor het weergeven en bewerken van kaartdata."""

    def __init__(
        self,
        parent,
        model,
        config,
        width=800,
        height=600,
        on_cell_change=None,
        on_mouse_position=None,
        **kwargs,
    ):
        """
        Initialiseert de map canvas.

        Args:
            parent: Het ouderwidget
            model: Het kaartmodel (MapModel)
            config: Configuratieobject
            width (int): Breedte van de canvas in pixels
            height (int): Hoogte van de canvas in pixels
            on_cell_change: Callback voor celwijzigingen
            on_mouse_position: Callback voor muispositie updates
            **kwargs: Extra argumenten voor CTkFrame
        """
        super().__init__(parent, width=width, height=height, **kwargs)

        # Maak een echte Canvas in de frame
        self.canvas = tk.Canvas(
            self, bg="#2B2B2B", highlightthickness=0, width=width, height=height
        )
        self.canvas.pack(fill="both", expand=True)

        # Slaat referenties op
        self.model = model
        self.config = config
        self.on_cell_change = on_cell_change
        self.on_mouse_position = on_mouse_position

        # Staat van de canvas
        self.zoom_factor = self.config.get("canvas_zoom_factor", 1.0)
        self.show_grid = self.config.get("show_grid", True)
        self.minimap_visible = self.config.get("show_minimap", True)
        self.current_terrain = self.config.get("default_tile", "G")

        # UI-gerelateerde variabelen
        self.cell_size = 32  # Basiscell size in pixels
        self.offset_x = 0  # Viewport offset X
        self.offset_y = 0  # Viewport offset Y
        self.drag_start_x = None  # Voor pannen
        self.drag_start_y = None
        self.last_cell = None  # Laatste gewijzigde cel (row, col, old_value)
        self.hovered_cell = None  # Huidige cel onder de muis (row, col)

        # Selectie variabelen
        self.selection_start = None  # (row, col) van selectie begin
        self.selection_end = None  # (row, col) van selectie eind
        self.selection_rect_id = None  # Canvas ID van selectierechthoek

        # Minimap
        self.minimap_size = self.config.get("minimap_size", 200)
        self.minimap_rect_id = None  # Canvas ID van minimap viewportrechthoek

        # Setup event bindings
        self._setup_bindings()

        # Voeg tooltips toe
        self._setup_tooltips()

        # Teken de kaart voor het eerst
        # Slight delay to ensure proper sizing
        self.after(100, self.redraw_map)

    def _setup_tooltips(self):
        """Voegt tooltips toe aan map canvas elementen."""
        # Canvas tooltip
        CTkToolTip(
            self.canvas,
            "Linkermuisknop: Plaats geselecteerd terrein\n"
            "Rechtermuisknop: Verwijder terrein\n"
            "Middelste muisknop/Wiel: Pannen over de kaart\n"
            "Shift+Sleep: Teken een lijn\n"
            "Ctrl+Sleep: Selecteer gebied\n"
            "Scrollwiel: Zoom in/uit",
            delay=1000,
        )  # Langere vertraging om niet in de weg te zitten

    def _setup_bindings(self):
        """Stelt muis en keyboard bindings in."""
        # Muis bindings
        self.canvas.bind("<Button-1>", self._on_left_click)
        self.canvas.bind("<B1-Motion>", self._on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_left_release)

        self.canvas.bind("<Button-2>", self._on_middle_click)  # Middelklik (wheel)
        self.canvas.bind("<B2-Motion>", self._on_middle_drag)

        self.canvas.bind("<Button-3>", self._on_right_click)  # Rechts-klik
        self.canvas.bind("<B3-Motion>", self._on_right_drag)
        self.canvas.bind("<ButtonRelease-3>", self._on_right_release)  # Rechts-release

        self.canvas.bind("<Motion>", self._on_mouse_move)  # Muis beweging

        # Toetsenbord bindings
        self.canvas.bind("<Delete>", self._on_delete_key)  # Delete toets

        # Modifier keys bindings
        self.canvas.bind("<Control-Button-1>", self._on_ctrl_left_click)  # Ctrl+LMB
        self.canvas.bind(
            "<Control-B1-Motion>", self._on_ctrl_left_drag
        )  # Ctrl+LMB drag
        self.canvas.bind(
            "<Control-ButtonRelease-1>", self._on_ctrl_left_release
        )  # Ctrl+LMB release

        # Shift bindings
        self.canvas.bind("<Shift-Button-1>", self._on_shift_left_click)  # Shift+LMB
        self.canvas.bind(
            "<Shift-B1-Motion>", self._on_shift_left_drag
        )  # Shift+LMB drag
        self.canvas.bind(
            "<Shift-ButtonRelease-1>", self._on_shift_left_release
        )  # Shift+LMB release

    def redraw_map(self):
        """Tekent de volledige kaart opnieuw."""
        self.canvas.delete("all")  # Wis alles op de canvas

        # Bereken effectieve celgrootte (met zoom)
        cell_size = self.cell_size * self.zoom_factor

        # Bereken zichtbare gebied (viewport)
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Voorkom delen door nul als canvas nog niet geïnitialiseerd is
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = self.canvas.winfo_reqwidth()
            canvas_height = self.canvas.winfo_reqheight()

        # Bereken bereik van zichtbare cellen
        start_col = max(0, int(self.offset_x / cell_size))
        start_row = max(0, int(self.offset_y / cell_size))
        end_col = min(
            self.model.width, int((canvas_width + self.offset_x) / cell_size) + 1
        )
        end_row = min(
            self.model.height, int((canvas_height + self.offset_y) / cell_size) + 1
        )

        # Tags voor verschillende elementen
        grid_tag = "grid"
        tile_tag = "tile"

        # Teken cellen
        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                x1 = col * cell_size - self.offset_x
                y1 = row * cell_size - self.offset_y
                x2 = x1 + cell_size
                y2 = y1 + cell_size

                # Verzamel alle zichtbare lagen op deze positie (in volgorde
                # van beneden naar boven)
                cells = self.model.get_cell_at_all_layers(row, col)

                # Teken elke laag, beginnend bij de onderste
                for layer_idx, terrain in cells:
                    if not self.model.layers[layer_idx].visible:
                        continue  # Skip onzichtbare lagen

                    # Haal kleur op basis van terreintype
                    color = self.config.get(f"terrain_colors.{terrain}", "#CCCCCC")

                    # Teken cell achtergrond
                    rect_id = self.canvas.create_rectangle(
                        x1,
                        y1,
                        x2,
                        y2,
                        fill=color,
                        outline=(
                            "" if len(cells) > 1 and layer_idx != cells[-1][0] else ""
                        ),
                        tags=(
                            tile_tag,
                            f"row_{row}",
                            f"col_{col}",
                            f"layer_{layer_idx}",
                        ),
                    )

                    # Teken terrein label
                    if len(terrain) > 1:  # Meerkarakter terrain codes
                        # Teken de eerste letter groter en rest kleiner eronder
                        self.canvas.create_text(
                            x1 + cell_size / 2,
                            y1 + cell_size / 3,
                            text=terrain[0],
                            font=("Arial", int(min(cell_size / 2.5, 16))),
                            tags=(
                                tile_tag,
                                f"row_{row}",
                                f"col_{col}",
                                f"layer_{layer_idx}",
                            ),
                        )
                        self.canvas.create_text(
                            x1 + cell_size / 2,
                            y1 + 2 * cell_size / 3,
                            text=terrain[1:],
                            font=("Arial", int(min(cell_size / 3, 12))),
                            tags=(
                                tile_tag,
                                f"row_{row}",
                                f"col_{col}",
                                f"layer_{layer_idx}",
                            ),
                        )
                    else:
                        # Alleen één karakter
                        self.canvas.create_text(
                            x1 + cell_size / 2,
                            y1 + cell_size / 2,
                            text=terrain,
                            font=("Arial", int(min(cell_size / 1.8, 24))),
                            tags=(
                                tile_tag,
                                f"row_{row}",
                                f"col_{col}",
                                f"layer_{layer_idx}",
                            ),
                        )

        # Teken raster indien ingeschakeld
        if self.show_grid:
            grid_color = self.config.get("grid_color", "#666666")

            # Verticale lijnen
            for col in range(start_col, end_col + 1):
                x = col * cell_size - self.offset_x
                self.canvas.create_line(
                    x, 0, x, canvas_height, fill=grid_color, width=1, tags=grid_tag
                )

            # Horizontale lijnen
            for row in range(start_row, end_row + 1):
                y = row * cell_size - self.offset_y
                self.canvas.create_line(
                    0, y, canvas_width, y, fill=grid_color, width=1, tags=grid_tag
                )

        # Teken minimap indien ingeschakeld
        if self.minimap_visible:
            self._draw_minimap()

        # Teken huidige selectie indien aanwezig
        if self.selection_start and self.selection_end:
            self._draw_selection()

    def _draw_minimap(self):
        """Tekent de minimap in de rechteronderhoek."""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # Bepaal minimap positie en grootte
        minimap_size = min(self.minimap_size, canvas_width // 3, canvas_height // 3)
        minimap_x = canvas_width - minimap_size - 10
        minimap_y = canvas_height - minimap_size - 10

        # Creëer minimap achtergrond
        self.canvas.create_rectangle(
            minimap_x,
            minimap_y,
            minimap_x + minimap_size,
            minimap_y + minimap_size,
            fill="#333333",
            outline="#999999",
            tags="minimap",
        )

        # Bereken schaalfactor en padding voor minimap
        map_width = self.model.width
        map_height = self.model.height
        
        # Bepaal de schaling en padding zodat de kaart altijd volledig in de minimap past
        # en de aspectratio behouden blijft
        map_aspect = map_width / map_height if map_height > 0 else 1
        
        # Bereken de effectieve minimap grootte (content gebied binnen padding)
        if map_aspect >= 1:  # Brede of vierkante kaart
            content_width = minimap_size
            content_height = minimap_size / map_aspect
            pad_x = 0
            pad_y = (minimap_size - content_height) / 2
        else:  # Hoge kaart
            content_width = minimap_size * map_aspect
            content_height = minimap_size
            pad_x = (minimap_size - content_width) / 2
            pad_y = 0
            
        # Bereken de schalingsfactoren
        scale_x = content_width / map_width
        scale_y = content_height / map_height

        # Teken tegelrepresentaties in minimap
        for row in range(map_height):
            for col in range(map_width):
                # Krijg de top-level terrein (hoogste zichtbare laag)
                layer_idx, terrain = self.model.get_top_cell(row, col)

                if terrain and layer_idx is not None:
                    # Bereken positie in minimap
                    mini_x = minimap_x + pad_x + col * scale_x
                    mini_y = minimap_y + pad_y + row * scale_y
                    mini_width = max(1, scale_x)
                    mini_height = max(1, scale_y)

                    # Haal kleur op basis van terreintype
                    color = self.config.get(f"terrain_colors.{terrain}", "#CCCCCC")

                    # Teken minimap pixel voor deze tegel
                    self.canvas.create_rectangle(
                        mini_x,
                        mini_y,
                        mini_x + mini_width,
                        mini_y + mini_height,
                        fill=color,
                        outline="",
                        tags="minimap",
                    )

        # Bereken viewport parameters
        cell_size = self.cell_size * self.zoom_factor
        
        # Bereken de relatieve posities in kaart coördinaten
        rel_view_x = self.offset_x / cell_size  # Linker viewport rand in kaart cellen
        rel_view_y = self.offset_y / cell_size   # Bovenste viewport rand in kaart cellen
        rel_view_width = canvas_width / cell_size  # Viewport breedte in kaart cellen
        rel_view_height = canvas_height / cell_size  # Viewport hoogte in kaart cellen
        
        # Converteer naar minimap coördinaten
        viewport_x = minimap_x + pad_x + rel_view_x * scale_x
        viewport_y = minimap_y + pad_y + rel_view_y * scale_y
        viewport_width = rel_view_width * scale_x
        viewport_height = rel_view_height * scale_y
        
        # Begrens het viewportrechthoek zodat het niet buiten de minimap uitsteekt
        viewport_right = min(minimap_x + minimap_size, viewport_x + viewport_width)
        viewport_bottom = min(minimap_y + minimap_size, viewport_y + viewport_height)
        viewport_x = max(minimap_x, viewport_x)
        viewport_y = max(minimap_y, viewport_y)
        
        # Bereken de uiteindelijke breedte en hoogte na begrenzing
        bounded_width = viewport_right - viewport_x
        bounded_height = viewport_bottom - viewport_y
        
        # Teken viewport rechthoek alleen als het zichtbaar is (positieve afmetingen)
        if bounded_width > 0 and bounded_height > 0:
            self.minimap_rect_id = self.canvas.create_rectangle(
                viewport_x,
                viewport_y,
                viewport_x + bounded_width,
                viewport_y + bounded_height,
                outline="#FF5500",
                width=2,
                tags="minimap",
            )

    def _draw_selection(self):
        """Tekent de huidige selectie."""
        if not self.selection_start or not self.selection_end:
            return

        # Sorteer coördinaten voor consistente rechthoek
        start_row = min(self.selection_start[0], self.selection_end[0])
        start_col = min(self.selection_start[1], self.selection_end[1])
        end_row = max(self.selection_start[0], self.selection_end[0])
        end_col = max(self.selection_start[1], self.selection_end[1])

        # Bereken pixelposities
        cell_size = self.cell_size * self.zoom_factor
        x1 = start_col * cell_size - self.offset_x
        y1 = start_row * cell_size - self.offset_y
        x2 = (end_col + 1) * cell_size - self.offset_x
        y2 = (end_row + 1) * cell_size - self.offset_y

        # Teken selectierechthoek
        if self.selection_rect_id:
            self.canvas.delete(self.selection_rect_id)

        self.selection_rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2, outline="#00FFFF", width=2, dash=(4, 4), tags="selection"
        )

    def _get_cell_at_position(self, x, y):
        """
        Bepaalt de cel-coördinaten op basis van pixelcoördinaten.

        Args:
            x (int): X-coördinaat in pixels
            y (int): Y-coördinaat in pixels

        Returns:
            tuple: (row, col) of None als buiten de kaart
        """
        cell_size = self.cell_size * self.zoom_factor

        # Bereken cel coördinaten
        col = int((x + self.offset_x) / cell_size)
        row = int((y + self.offset_y) / cell_size)

        # Controleer of binnen kaartgrenzen
        if 0 <= row < self.model.height and 0 <= col < self.model.width:
            return (row, col)

        return None

    def _modify_cell(self, row, col, value):
        """
        Wijzigt de waarde van een cel in het model.

        Args:
            row (int): Rij-index
            col (int): Kolom-index
            value (str): Nieuwe waarde voor de cel

        Returns:
            bool: True als de wijziging is gelukt
        """
        # Controleer of er een actieve laag is
        active_layer = self.model.active_layer
        if not active_layer or active_layer.locked:
            return False

        # Wijzig in het model
        success, old_value = self.model.set_cell(row, col, value)

        # Update UI en triggers callback indien succesvol
        if success:
            # Herlaad alleen deze specieke cel
            self._update_cell_visuals(row, col)

            # Remembers last modified cell for undo
            self.last_cell = (row, col, old_value)

            # Notify caller
            if self.on_cell_change:
                self.on_cell_change(row, col, value)

            return True

        return False

    def _update_cell_visuals(self, row, col):
        """
        Update alleen de visuele weergave van een specifieke cel.

        Args:
            row (int): Rij-index
            col (int): Kolom-index
        """
        # Bereken positie van de cel
        cell_size = self.cell_size * self.zoom_factor
        x1 = col * cell_size - self.offset_x
        y1 = row * cell_size - self.offset_y
        x2 = x1 + cell_size
        y2 = y1 + cell_size

        # Verwijder bestaande cell elementen
        self.canvas.delete(f"row_{row}", f"col_{col}")

        # Verzamel alle zichtbare lagen op deze positie (in volgorde van
        # beneden naar boven)
        cells = self.model.get_cell_at_all_layers(row, col)

        # Teken elke laag, beginnend bij de onderste
        for layer_idx, terrain in cells:
            if not self.model.layers[layer_idx].visible:
                continue  # Skip onzichtbare lagen

            # Haal kleur op basis van terreintype
            color = self.config.get(f"terrain_colors.{terrain}", "#CCCCCC")

            # Teken cell achtergrond
            rect_id = self.canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=color,
                outline="" if len(cells) > 1 and layer_idx != cells[-1][0] else "",
                tags=("tile", f"row_{row}", f"col_{col}", f"layer_{layer_idx}"),
            )

            # Teken terrein label
            if len(terrain) > 1:  # Meerkarakter terrain codes
                # Teken de eerste letter groter en rest kleiner eronder
                self.canvas.create_text(
                    x1 + cell_size / 2,
                    y1 + cell_size / 3,
                    text=terrain[0],
                    font=("Arial", int(min(cell_size / 2.5, 16))),
                    tags=("tile", f"row_{row}", f"col_{col}", f"layer_{layer_idx}"),
                )
                self.canvas.create_text(
                    x1 + cell_size / 2,
                    y1 + 2 * cell_size / 3,
                    text=terrain[1:],
                    font=("Arial", int(min(cell_size / 3, 12))),
                    tags=("tile", f"row_{row}", f"col_{col}", f"layer_{layer_idx}"),
                )
            else:
                # Alleen één karakter
                self.canvas.create_text(
                    x1 + cell_size / 2,
                    y1 + cell_size / 2,
                    text=terrain,
                    font=("Arial", int(min(cell_size / 1.8, 24))),
                    tags=("tile", f"row_{row}", f"col_{col}", f"layer_{layer_idx}"),
                )

    def set_current_terrain(self, terrain_id):
        """
        Stelt het huidige geselecteerde terreintype in.

        Args:
            terrain_id (str): ID van het terreintype
        """
        self.current_terrain = terrain_id

    def set_zoom(self, zoom_factor):
        """
        Stelt de zoom factor in en herlaadt de kaart.

        Args:
            zoom_factor (float): Nieuwe zoomfactor
        """
        # Bereken focuspunt (centrum van huidige viewport)
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        center_x = self.offset_x + canvas_width / 2
        center_y = self.offset_y + canvas_height / 2

        old_cell_size = self.cell_size * self.zoom_factor

        # Update zoom
        self.zoom_factor = zoom_factor

        # Nieuwe cell size met nieuwe zoom
        new_cell_size = self.cell_size * self.zoom_factor

        # Bereken nieuwe offset om op hetzelfde punt gecentreerd te blijven
        scale_factor = new_cell_size / old_cell_size
        new_center_x = center_x * scale_factor
        new_center_y = center_y * scale_factor

        self.offset_x = new_center_x - canvas_width / 2
        self.offset_y = new_center_y - canvas_height / 2

        # Herlaad kaart
        self.redraw_map()

    def set_grid_visible(self, visible):
        """
        Stelt in of het raster zichtbaar is.

        Args:
            visible (bool): Of het raster zichtbaar moet zijn
        """
        self.show_grid = visible
        self.redraw_map()

    def set_minimap_visible(self, visible):
        """
        Stelt in of de minimap zichtbaar is.

        Args:
            visible (bool): Of de minimap zichtbaar moet zijn
        """
        self.minimap_visible = visible
        self.redraw_map()

    def export_as_image(self, filepath):
        """
        Exporteert de huidige kaart als afbeelding.

        Args:
            filepath (str): Pad om naar te exporteren

        Returns:
            bool: True als succesvol
        """
        try:
            # Bepaal afmetingen
            map_width = self.model.width
            map_height = self.model.height

            # Gebruik een vaste celgrootte voor export
            export_cell_size = 32  # Pixels per cel in de export

            # Creëer een nieuwe afbeelding
            image_width = map_width * export_cell_size
            image_height = map_height * export_cell_size

            # Maximum afmetingen limiteren
            max_dimension = 4000  # Maximum toelaatbare afmeting
            if image_width > max_dimension or image_height > max_dimension:
                scale_factor = min(
                    max_dimension / image_width, max_dimension / image_height
                )
                export_cell_size = int(export_cell_size * scale_factor)
                image_width = map_width * export_cell_size
                image_height = map_height * export_cell_size

                # Waarschuw bij schalen
                messagebox.showinfo(
                    "Export geschaald",
                    f"De kaart is te groot voor export op volledige grootte. "
                    f"De afbeelding is geschaald naar {image_width}x{image_height} pixels.",
                    parent=self.winfo_toplevel(),
                )

            try:
                # Creëer afbeelding en tekencontext
                from PIL import Image, ImageDraw

                img = Image.new("RGB", (image_width, image_height), "#333333")
                draw = ImageDraw.Draw(img)
            except ImportError:
                messagebox.showerror(
                    "Export fout",
                    "PIL (Python Imaging Library) is vereist voor afbeeldingsexport maar niet gevonden.\n"
                    "Installeer PIL met: pip install pillow",
                    parent=self.winfo_toplevel(),
                )
                return False

            # Teken elke cel
            for row in range(map_height):
                for col in range(map_width):
                    x1 = col * export_cell_size
                    y1 = row * export_cell_size
                    x2 = x1 + export_cell_size
                    y2 = y1 + export_cell_size

                    # Verzamel alle zichtbare lagen op deze positie
                    cells = self.model.get_cell_at_all_layers(row, col)

                    # Teken elke laag, beginnend bij de onderste
                    for layer_idx, terrain in cells:
                        if not self.model.layers[layer_idx].visible:
                            continue  # Skip onzichtbare lagen

                        # Haal kleur op basis van terreintype
                        color_hex = self.config.get(
                            f"terrain_colors.{terrain}", "#CCCCCC"
                        )
                        # Converteer hex naar rgb
                        r = int(color_hex[1:3], 16)
                        g = int(color_hex[3:5], 16)
                        b = int(color_hex[5:7], 16)
                        color = (r, g, b)

                        # Teken cel rechthoek
                        draw.rectangle([x1, y1, x2, y2], fill=color)

                        # Teken label op basis van terreintype
                        text_color = (0, 0, 0) if sum(color) > 380 else (255, 255, 255)

                        # Bepaal grootte voor tekst
                        if len(terrain) <= 1:
                            font_size = int(export_cell_size * 0.6)
                            # PIL heeft geen native TrueType support, moet eigen font laden
                            # Hier gebruiken we gewoon basic centering logica
                            text_width = len(terrain) * font_size * 0.6
                            text_x = x1 + (export_cell_size - text_width) / 2
                            text_y = y1 + (export_cell_size - font_size) / 2
                            draw.text((text_x, text_y), terrain, fill=text_color)
                        else:
                            # Twee regels tekst voor meerkarakter codes
                            top_char = terrain[0]
                            bottom_chars = terrain[1:]

                            font_size_top = int(export_cell_size * 0.5)
                            font_size_bottom = int(export_cell_size * 0.3)

                            # Top karakter
                            text_width_top = font_size_top * 0.6
                            text_x_top = x1 + (export_cell_size - text_width_top) / 2
                            text_y_top = y1 + export_cell_size * 0.2
                            draw.text(
                                (text_x_top, text_y_top), top_char, fill=text_color
                            )

                            # Bottom karakters
                            text_width_bottom = (
                                len(bottom_chars) * font_size_bottom * 0.6
                            )
                            text_x_bottom = (
                                x1 + (export_cell_size - text_width_bottom) / 2
                            )
                            text_y_bottom = y1 + export_cell_size * 0.6
                            draw.text(
                                (text_x_bottom, text_y_bottom),
                                bottom_chars,
                                fill=text_color,
                            )

            # Teken raster indien ingeschakeld
            if self.show_grid:
                grid_color = (102, 102, 102)  # Equivalent van #666666

                # Verticale lijnen
                for col in range(map_width + 1):
                    x = col * export_cell_size
                    draw.line([(x, 0), (x, image_height)], fill=grid_color, width=1)

                # Horizontale lijnen
                for row in range(map_height + 1):
                    y = row * export_cell_size
                    draw.line([(0, y), (image_width, y)], fill=grid_color, width=1)

            try:
                # Opslaan naar bestand
                img.save(filepath)
                return True
            except Exception as e:
                messagebox.showerror(
                    "Export fout",
                    f"Kon de afbeelding niet opslaan naar {filepath}:\n{
                        str(e)}",
                    parent=self.winfo_toplevel(),
                )
                return False

        except Exception as e:
            messagebox.showerror(
                "Export fout",
                f"Onverwachte fout bij exporteren als afbeelding:\n{str(e)}",
                parent=self.winfo_toplevel(),
            )
            return False

    # --- Layout management methoden ---

    # Doorstuur methoden voor de tkinter layout managers
    def grid(self, **kwargs):
        """Doorstuur naar de grid layout manager van tk."""
        super().grid(**kwargs)
        return self

    def grid_configure(self, **kwargs):
        """Doorstuur naar de grid_configure methode."""
        super().grid_configure(**kwargs)
        return self

    def grid_forget(self):
        """Doorstuur naar de grid_forget methode."""
        super().grid_forget()
        return self

    def grid_info(self):
        """Doorstuur naar de grid_info methode."""
        return super().grid_info()

    def grid_remove(self):
        """Doorstuur naar de grid_remove methode."""
        super().grid_remove()
        return self

    # --- Event handlers ---

    def _on_left_click(self, event):
        """Handler voor linker muisknop."""
        # Check of we op de minimap klikken
        if self.minimap_visible and self._is_click_on_minimap(event.x, event.y):
            self._on_minimap_click(event)
            return

        # Bepaal cel onder de klik
        cell = self._get_cell_at_position(event.x, event.y)
        if cell:
            row, col = cell

            # Plaats huidig terrain in deze cel
            self._modify_cell(row, col, self.current_terrain)

    def _on_left_drag(self, event):
        """Handler voor slepen met linker muisknop."""
        # Check of we op de minimap slepen
        if self.minimap_visible and self._is_click_on_minimap(event.x, event.y):
            self._on_minimap_drag(event)
            return

        # Bepaal cel onder muis
        cell = self._get_cell_at_position(event.x, event.y)
        if cell:
            row, col = cell

            # Wijzig cel met huidig terrein (als deze anders is)
            current_top_cell = self.model.get_top_cell(row, col)
            if current_top_cell[1] != self.current_terrain:
                self._modify_cell(row, col, self.current_terrain)

    def _on_left_release(self, event):
        """Handler voor loslaten van linker muisknop."""
        pass  # Niets speciaals nodig hier
        
    def _on_right_release(self, event):
        """Handler voor loslaten van rechter muisknop."""
        # Reset tracking variabele voor rechter muisknop drag
        if hasattr(self, 'last_right_drag_cell'):
            del self.last_right_drag_cell

    def _on_middle_click(self, event):
        """Handler voor middelste muisknop (pan starten)."""
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.canvas.config(cursor="fleur")  # Hand cursor for panning

    def _on_middle_drag(self, event):
        """Handler voor slepen met middelste muisknop (pannen)."""
        if self.drag_start_x is not None and self.drag_start_y is not None:
            # Bereken hoeveel we gaan verschuiven
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y

            # Update offset
            self.offset_x -= dx
            self.offset_y -= dy

            # Begrens offset (voorkom te ver scrollen)
            max_width = self.model.width * self.cell_size * self.zoom_factor
            max_height = self.model.height * self.cell_size * self.zoom_factor
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            # Laat toe om te pannen tot de kaartrand
            self.offset_x = max(0, min(self.offset_x, max_width - canvas_width))
            self.offset_y = max(0, min(self.offset_y, max_height - canvas_height))

            # Update start positie voor volgende beweging
            self.drag_start_x = event.x
            self.drag_start_y = event.y

            # Herteken de kaart
            self.redraw_map()

    def _on_right_click(self, event):
        """Handler voor rechter muisknop (verwijderen/leeg maken)."""
        # Check of we op de minimap klikken
        if self.minimap_visible and self._is_click_on_minimap(event.x, event.y):
            return
            
        # Bepaal cel onder de klik
        cell = self._get_cell_at_position(event.x, event.y)
        if cell:
            row, col = cell

            # Plaats een leeg terrein in deze cel
            self._modify_cell(row, col, " ")

    def _on_right_drag(self, event):
        """Handler voor slepen met rechter muisknop (verwijderen)."""
        # Check of we op de minimap slepen
        if self.minimap_visible and self._is_click_on_minimap(event.x, event.y):
            return
            
        # Bepaal cel onder muis
        cell = self._get_cell_at_position(event.x, event.y)
        if cell:
            row, col = cell
            
            # Controleer of dit dezelfde cel is als de vorige om herhaalde wijzigingen te voorkomen
            if hasattr(self, 'last_right_drag_cell') and self.last_right_drag_cell == (row, col):
                return
                
            # Onthoud deze cel om herhaalde wijzigingen te voorkomen
            self.last_right_drag_cell = (row, col)

            # Maak cel leeg (als deze niet al leeg is)
            current_top_cell = self.model.get_top_cell(row, col)
            if current_top_cell[1] != " ":
                self._modify_cell(row, col, " ")

    def _on_ctrl_left_click(self, event):
        """Handler voor Ctrl+linker muisknop (selectie starten)."""
        # Bepaal cel onder de klik
        cell = self._get_cell_at_position(event.x, event.y)
        if cell:
            # Start selectie
            self.selection_start = cell
            self.selection_end = cell
            self._draw_selection()

    def _on_ctrl_left_drag(self, event):
        """Handler voor Ctrl+linker muisknop slepen (selectie wijzigen)."""
        # Bepaal cel onder muis
        cell = self._get_cell_at_position(event.x, event.y)
        if cell and self.selection_start:
            # Update einde van selectie
            self.selection_end = cell
            self._draw_selection()

    def _on_ctrl_left_release(self, event):
        """Handler voor loslaten van Ctrl+linker muisknop (selectie voltooid)."""
        # Selectie is nu klaar voor gebruik
        pass

    def _on_shift_left_click(self, event):
        """Handler voor Shift+linker muisknop (lijntekenmodus)."""
        # Start lijn tekenen vanaf huidige cel
        cell = self._get_cell_at_position(event.x, event.y)
        if cell:
            self.line_start = cell
            # Teken alvast een punt op de startpositie
            row, col = cell
            self._modify_cell(row, col, self.current_terrain)

    def _on_shift_left_drag(self, event):
        """Handler voor Shift+linker muisknop slepen (lijn voorbeeld)."""
        # Toon voorbeeld van de lijn tijdens slepen
        if not hasattr(self, "line_start"):
            return

        cell = self._get_cell_at_position(event.x, event.y)
        if cell and self.line_start:
            # Verwijder eerdere lijn voorbeelden
            self.canvas.delete("line_preview")

            # Teken een lijn van start naar huidige positie
            start_row, start_col = self.line_start
            end_row, end_col = cell

            # Converteer naar pixel coördinaten
            cell_size = self.cell_size * self.zoom_factor
            x1 = start_col * cell_size - self.offset_x + cell_size / 2
            y1 = start_row * cell_size - self.offset_y + cell_size / 2
            x2 = end_col * cell_size - self.offset_x + cell_size / 2
            y2 = end_row * cell_size - self.offset_y + cell_size / 2

            # Teken lijn preview
            self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                fill="#00FFFF",
                width=2,
                dash=(4, 4),
                tags="line_preview",
            )

    def _on_shift_left_release(self, event):
        """Handler voor loslaten van Shift+linker muisknop (lijn tekenen)."""
        if not hasattr(self, "line_start"):
            return

        # Voltooi het lijntekenen
        cell = self._get_cell_at_position(event.x, event.y)
        if cell and self.line_start:
            # Verwijder voorbeeldlijn
            self.canvas.delete("line_preview")

            # Bereken lijn pixels met Bresenham algoritme
            start_row, start_col = self.line_start
            end_row, end_col = cell

            line_cells = self._get_line_cells(start_row, start_col, end_row, end_col)

            # Plaats terrein op elk punt in de lijn
            for row, col in line_cells:
                self._modify_cell(row, col, self.current_terrain)

        # Reset lijn start
        self.line_start = None

    def _on_delete_key(self, event):
        """Handler voor Delete toets (geselecteerde gebied leegmaken)."""
        if self.selection_start and self.selection_end:
            # Sorteer coördinaten
            start_row = min(self.selection_start[0], self.selection_end[0])
            start_col = min(self.selection_start[1], self.selection_end[1])
            end_row = max(self.selection_start[0], self.selection_end[0])
            end_col = max(self.selection_start[1], self.selection_end[1])

            # Maak alle cellen in selectie leeg
            for row in range(start_row, end_row + 1):
                for col in range(start_col, end_col + 1):
                    self._modify_cell(row, col, " ")

    def _on_mouse_move(self, event):
        """Handler voor muisbeweging (voor hover effects en positie tracking)."""
        # Bepaal cel onder muis
        cell = self._get_cell_at_position(event.x, event.y)

        # Updatepositie label via callback
        if self.on_mouse_position:
            self.on_mouse_position(
                None if not cell else cell[0], None if not cell else cell[1]
            )

    def _is_click_on_minimap(self, x, y):
        """
        Controleert of een klik op de minimap is.

        Args:
            x (int): X-coördinaat van de klik
            y (int): Y-coördinaat van de klik

        Returns:
            bool: True als de klik op de minimap is
        """
        if not self.minimap_visible:
            return False

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        minimap_size = min(self.minimap_size, canvas_width // 3, canvas_height // 3)
        minimap_x = canvas_width - minimap_size - 10
        minimap_y = canvas_height - minimap_size - 10

        return (
            minimap_x <= x <= minimap_x + minimap_size
            and minimap_y <= y <= minimap_y + minimap_size
        )

    def _on_minimap_click(self, event):
        """
        Handler voor klikken op de minimap.

        Args:
            event: Tkinter event
        """
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        minimap_size = min(self.minimap_size, canvas_width // 3, canvas_height // 3)
        minimap_x = canvas_width - minimap_size - 10
        minimap_y = canvas_height - minimap_size - 10

        # Bereken relatieve positie binnen minimap
        rel_x = event.x - minimap_x
        rel_y = event.y - minimap_y
        
        # Bereken aspectratio en padding zoals in _draw_minimap
        map_width = self.model.width
        map_height = self.model.height
        map_aspect = map_width / map_height if map_height > 0 else 1
        
        # Bereken de effectieve minimap grootte
        if map_aspect >= 1:  # Brede of vierkante kaart
            content_width = minimap_size
            content_height = minimap_size / map_aspect
            pad_x = 0
            pad_y = (minimap_size - content_height) / 2
        else:  # Hoge kaart
            content_width = minimap_size * map_aspect
            content_height = minimap_size
            pad_x = (minimap_size - content_width) / 2
            pad_y = 0
            
        # Bereken de schalingsfactoren
        scale_x = content_width / map_width
        scale_y = content_height / map_height
        
        # Corrigeer klikpositie met padding
        map_rel_x = (rel_x - pad_x) / scale_x
        map_rel_y = (rel_y - pad_y) / scale_y
        
        # Begrens binnen kaartafmetingen
        map_rel_x = max(0, min(map_width, map_rel_x))
        map_rel_y = max(0, min(map_height, map_rel_y))

        # Centreer de viewport op dit punt
        cell_size = self.cell_size * self.zoom_factor

        self.offset_x = map_rel_x * cell_size - canvas_width / 2
        self.offset_y = map_rel_y * cell_size - canvas_height / 2

        # Begrens offset
        max_width = self.model.width * self.cell_size * self.zoom_factor
        max_height = self.model.height * self.cell_size * self.zoom_factor

        self.offset_x = max(0, min(self.offset_x, max_width - canvas_width))
        self.offset_y = max(0, min(self.offset_y, max_height - canvas_height))

        # Herteken
        self.redraw_map()

    def _on_minimap_drag(self, event):
        """
        Handler voor slepen binnen de minimap.

        Args:
            event: Tkinter event
        """
        # Zelfde als klikken, pannen naar nieuwe locatie
        self._on_minimap_click(event)

    def _get_line_cells(self, start_row, start_col, end_row, end_col):
        """
        Berekent cellen langs een lijn met Bresenham algorithm.

        Args:
            start_row (int): Begin rij
            start_col (int): Begin kolom
            end_row (int): Eind rij
            end_col (int): Eind kolom

        Returns:
            list: List of (row, col) tuples along the line
        """
        line_cells = []

        # Bresenham lijn algoritme
        dx = abs(end_col - start_col)
        dy = -abs(end_row - start_row)
        sx = 1 if start_col < end_col else -1
        sy = 1 if start_row < end_row else -1
        err = dx + dy

        x, y = start_col, start_row

        while True:
            line_cells.append((y, x))

            if x == end_col and y == end_row:
                break

            e2 = 2 * err
            if e2 >= dy:
                if x == end_col:
                    break
                err += dy
                x += sx
            if e2 <= dx:
                if y == end_row:
                    break
                err += dx
                y += sy

        return line_cells
