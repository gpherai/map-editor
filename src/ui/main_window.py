# src/ui/main_window.py
# Hoofdvenster klasse voor de Map Editor UI

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
import webbrowser
import time
from PIL import Image, ImageTk, ImageDraw
import math

# Importeer de benodigde modules
# (Zorg dat deze bestanden bestaan op de juiste locaties relatief aan dit bestand)
try:
    from src.config import Config
    from src.utils.tooltip import CTkToolTip
    from src.models.map_model import MapModel
    from src.ui.terrain_panel import TerrainPanel
    from src.ui.map_canvas import MapCanvas
    from src.ui.layer_panel import LayerPanel
except ImportError as e:
    print(f"BELANGRIJKE FOUT: Kon een of meer modules niet importeren: {e}")
    print(
        "Controleer of alle benodigde .py bestanden (config, tooltip, map_model, terrain_panel, map_canvas, layer_panel) bestaan en correct in de mappenstructuur staan."
    )
    # Definieer dummy klassen om te voorkomen dat de rest crasht, maar de app
    # zal niet werken.

    class Config:
        def get(self, key, default=None):
            return default

        def set(self, key, value):
            pass

        def get_terrain_types(self):
            return {}

        def get_terrain_categories(self):
            return {}

    class CTkToolTip:
        def __init__(self, *args, **kwargs):
            pass

    class MapModel:
        def __init__(self, *args, **kwargs):
            self.width = 10
            self.height = 10
            self.current_file = None
            self.layers = []
            self.active_layer_index = 0
            self.active_layer = None

        def has_unsaved_changes(self):
            return False

        def can_undo(self):
            return False

        def can_redo(self):
            return False

        def new_map(self, w, h):
            self.width = w
            self.height = h
            print("Dummy: New map")

        def load_map(self, p):
            print(f"Dummy: Load map {p}")
            return False

        def save_map(self, p=None):
            print(f"Dummy: Save map {p}")
            return False

        def export_to_string(self):
            return "Dummy Export"

        def resize(self, w, h):
            print(f"Dummy: Resize to {w}x{h}")
            return self.width, self.height

        def fill(self, t):
            print(f"Dummy: Fill with {t}")
            return False

        def undo(self):
            print("Dummy: Undo")
            return False, "dummy"

        def redo(self):
            print("Dummy: Redo")
            return False, "dummy"

        def add_layer(self, n):
            print(f"Dummy: Add layer {n}")
            return 0

        def remove_layer(self, i):
            print(f"Dummy: Remove layer {i}")
            return None

        def get_top_cell(self, r, c):
            return None, None

        def set_cell(self, r, c, v):
            pass

    class TerrainPanel:
        def __init__(self, *args, **kwargs):
            print("Dummy TerrainPanel created")

        def pack(self, *args, **kwargs):
            pass

    class MapCanvas:
        def __init__(self, *args, **kwargs):
            print("Dummy MapCanvas created")

        def grid(self, *args, **kwargs):
            pass

        def bind(self, *args, **kwargs):
            pass

        def set_current_terrain(self, t):
            pass

        def redraw_map(self):
            pass

        def set_zoom(self, z):
            pass

        def set_grid_visible(self, v):
            pass

        def set_minimap_visible(self, v):
            pass

        def export_as_image(self, p):
            print(f"Dummy: Export image {p}")
            return False

    class LayerPanel:
        def __init__(self, *args, **kwargs):
            print("Dummy LayerPanel created")

        def pack(self, *args, **kwargs):
            pass

        def update_layer_list(self):
            pass

        def set_active_layer(self, i):
            pass


class MapEditorApp(ctk.CTkFrame):
    """Hoofdklasse voor de Map Editor applicatie UI."""

    def __init__(self, master, **kwargs):
        """
        Initialiseert het hoofdvenster van de Map Editor.

        Args:
                master: Het root tkinter venster
                **kwargs: Extra argumenten voor CTkFrame
        """
        super().__init__(master, **kwargs)

        # Configuratie laden
        self.config = Config()

        # Set up het hoofdvenster
        self._setup_main_window()

        # Model initialiseren
        self.model = MapModel(self.config)

        # UI variabelen
        self.current_terrain = self.config.get("default_tile", "G")
        self.zoom_factor = self.config.get("canvas_zoom_factor", 1.0)
        self.show_grid = self.config.get("show_grid", True)
        self.minimap_visible = self.config.get("show_minimap", True)
        self._status_timer_id = None  # Initialiseer timer ID voor statusbalk

        # UI elementen maken
        self._create_menu()
        self._create_main_layout()  # Maakt de hoofd frames (left, map, right)
        self._setup_status_bar()  # Maakt de statusbalk onderaan
        self._create_widgets()  # Vult de panelen (left, map, right) met widgets
        self._setup_tooltips()
        self._setup_bindings()

        # UI vullen met initiële data
        self._update_ui_from_model()

        # Setup autosave timer (indien ingeschakeld)
        autosave_interval = self.config.get("autosave_interval", 0)
        if autosave_interval > 0:
            # Minuten naar milliseconden
            self._setup_autosave(autosave_interval * 60 * 1000)

        # Toon welkomstmelding
        self.set_status(
            f"Welkom bij de Tri-Sharira Map Editor - Nieuwe kaart {
                self.model.width}x{
                self.model.height}"
        )

    def _setup_main_window(self):
        """Configureert de basis van het hoofdvenster."""
        self.master.title(self.config.get("app_name", "Tri-Sharira Map Editor"))

        # Stel venstergrootte in
        window_width = self.config.get("window_width", 1280)
        window_height = self.config.get("window_height", 800)
        self.master.geometry(f"{window_width}x{window_height}")
        self.master.minsize(800, 600)

        # Icon instellen (indien beschikbaar)
        # Pad relatief aan DIT bestand (main_window.py in src/ui)
        try:
            # Ga 3 niveaus omhoog (ui -> src -> map_editor) en dan naar assets
            base_path = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            icon_path = os.path.join(base_path, "assets", "icon.png")
            print(f"Zoeken naar icoon: {icon_path}")  # Debug print
            if os.path.exists(icon_path):
                try:
                    icon = tk.PhotoImage(file=icon_path)
                    self.master.iconphoto(True, icon)
                    print("Icoon geladen.")
                except Exception as e:
                    print(f"Kon icoon niet laden (fout in tk.PhotoImage): {e}")
            else:
                print("Icoon bestand niet gevonden.")
        except Exception as e:
            print(f"Fout bij bepalen icoon pad: {e}")

        # Frame vullen in het hoofdvenster
        self.pack(fill=tk.BOTH, expand=True)

        # Protocol voor afsluiten
        self.master.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_menu(self):
        """Maakt de menubalk aan."""
        self.menu_bar = tk.Menu(self.master)
        self.master.config(menu=self.menu_bar)

        # Bestandsmenu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Bestand", menu=file_menu)
        file_menu.add_command(
            label="Nieuw", command=self._new_map, accelerator="Ctrl+N"
        )
        file_menu.add_command(
            label="Openen...", command=self._open_map, accelerator="Ctrl+O"
        )
        file_menu.add_command(
            label="Opslaan", command=self._save_map, accelerator="Ctrl+S"
        )
        file_menu.add_command(
            label="Opslaan als...",
            command=self._save_map_as,
            accelerator="Ctrl+Shift+S",
        )

        # Submenu voor recente bestanden
        self.recent_files_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recente bestanden", menu=self.recent_files_menu)
        self._update_recent_files_menu()

        file_menu.add_separator()
        file_menu.add_command(label="Exporteren als JSON", command=self._export_map)
        file_menu.add_command(
            label="Exporteren als afbeelding", command=self._export_as_image
        )
        file_menu.add_separator()
        file_menu.add_command(
            label="Afsluiten", command=self._on_closing, accelerator="Alt+F4"
        )

        # Bewerken menu
        edit_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Bewerken", menu=edit_menu)
        edit_menu.add_command(
            label="Ongedaan maken",
            command=self._undo,
            accelerator="Ctrl+Z",
            state=tk.DISABLED,
        )
        edit_menu.add_command(
            label="Opnieuw uitvoeren",
            command=self._redo,
            accelerator="Ctrl+Y",
            state=tk.DISABLED,
        )
        edit_menu.add_separator()
        edit_menu.add_command(
            label="Kaartgrootte wijzigen", command=self._resize_map_dialog
        )
        edit_menu.add_command(
            label="Alles vullen met huidig terrein", command=self._fill_all
        )

        # Beeld menu
        view_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Beeld", menu=view_menu)

        # Zoom submenu
        zoom_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Zoom", menu=zoom_menu)
        zoom_menu.add_command(
            label="Inzoomen", command=self._zoom_in, accelerator="Ctrl++"
        )
        zoom_menu.add_command(
            label="Uitzoomen", command=self._zoom_out, accelerator="Ctrl+-"
        )
        zoom_menu.add_command(
            label="Standaard zoom (100%)",
            command=self._zoom_reset,
            accelerator="Ctrl+0",
        )

        # Grid checkbox
        self.show_grid_var = tk.BooleanVar(value=self.show_grid)
        view_menu.add_checkbutton(
            label="Raster tonen", variable=self.show_grid_var, command=self._toggle_grid
        )

        # Minimap checkbox
        self.minimap_var = tk.BooleanVar(value=self.minimap_visible)
        view_menu.add_checkbutton(
            label="Minimap tonen",
            variable=self.minimap_var,
            command=self._toggle_minimap,
        )

        # Thema submenu
        theme_menu = tk.Menu(view_menu, tearoff=0)
        view_menu.add_cascade(label="Thema", menu=theme_menu)
        theme_menu.add_command(label="Donker", command=lambda: self._set_theme("dark"))
        theme_menu.add_command(label="Licht", command=lambda: self._set_theme("light"))
        theme_menu.add_command(
            label="Systeemthema", command=lambda: self._set_theme("system")
        )

        # Lagen menu
        layers_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Lagen", menu=layers_menu)
        layers_menu.add_command(label="Voeg laag toe", command=self._add_layer)
        layers_menu.add_command(
            label="Verwijder actieve laag", command=self._remove_layer
        )
        layers_menu.add_separator()
        layers_menu.add_command(
            label="Verplaats laag omhoog", command=lambda: self._move_layer(-1)
        )
        layers_menu.add_command(
            label="Verplaats laag omlaag", command=lambda: self._move_layer(1)
        )

        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Controls", command=self._show_controls)
        help_menu.add_command(label="Terrein legenda", command=self._show_legend)
        help_menu.add_command(label="Over Map Editor", command=self._show_about)

        # Keyboard shortcuts
        self.master.bind("<Control-n>", lambda e: self._new_map())
        self.master.bind("<Control-o>", lambda e: self._open_map())
        self.master.bind("<Control-s>", lambda e: self._save_map())
        self.master.bind("<Control-Shift-S>", lambda e: self._save_map_as())
        self.master.bind("<Control-z>", lambda e: self._undo())
        self.master.bind("<Control-y>", lambda e: self._redo())
        self.master.bind("<Control-plus>", lambda e: self._zoom_in())
        # Also for Ctrl+= since it's Shift+=
        self.master.bind("<Control-equal>", lambda e: self._zoom_in())
        self.master.bind("<Control-minus>", lambda e: self._zoom_out())
        self.master.bind("<Control-0>", lambda e: self._zoom_reset())

    def _create_main_layout(self):
        """Creëert de hoofdlayout van de applicatie."""
        # Main layout gridsysteem
        self.grid_columnconfigure(0, weight=0, minsize=250)  # Terreinpaneel (vast)
        self.grid_columnconfigure(1, weight=3)  # Kaartgebied (groeit mee)
        self.grid_columnconfigure(2, weight=0, minsize=250)  # Lagenpaneel (vast)
        self.grid_rowconfigure(0, weight=1)  # Hoofd UI rij
        # Statusbalk rij (vaste hoogte)
        self.grid_rowconfigure(1, weight=0)

        # Linker paneel (terrein selector)
        self.left_panel = ctk.CTkFrame(self)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)

        # Kaartgebied (midden)
        self.map_area = ctk.CTkFrame(self)
        self.map_area.grid(row=0, column=1, sticky="nsew", padx=5, pady=10)
        self.map_area.grid_rowconfigure(0, weight=0)  # Info panel
        self.map_area.grid_rowconfigure(1, weight=1)  # Canvas
        self.map_area.grid_columnconfigure(0, weight=1)

        # Rechter paneel (laagbeheer)
        self.right_panel = ctk.CTkFrame(self)
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(5, 10), pady=10)

    def _setup_status_bar(self):
        """Maakt de statusbalk onderin het venster met uitgebreide informatie."""
        self.status_bar = ctk.CTkFrame(self, height=30)
        # Plaats statusbalk in rij 1, over alle kolommen
        self.status_bar.grid(
            row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10)
        )
        # Vasthouden op gedefinieerde hoogte
        self.status_bar.grid_propagate(False)

        # Status label links
        self.status_label = ctk.CTkLabel(self.status_bar, text="Gereed", anchor="w")
        self.status_label.grid(row=0, column=0, sticky="w", padx=10)

        # Scheidingslijn
        separator1 = ctk.CTkFrame(self.status_bar, width=1, height=20, fg_color="gray")
        separator1.grid(row=0, column=1, padx=5)

        # Positie label
        self.position_label = ctk.CTkLabel(
            self.status_bar, text="Positie: -", anchor="w", width=150
        )
        self.position_label.grid(row=0, column=2, sticky="w", padx=10)

        # Scheidingslijn
        separator2 = ctk.CTkFrame(self.status_bar, width=1, height=20, fg_color="gray")
        separator2.grid(row=0, column=3, padx=5)

        # Actieve laag indicator
        self.status_layer_label = ctk.CTkLabel(
            self.status_bar, text="Laag: -", anchor="w", width=150
        )
        self.status_layer_label.grid(row=0, column=4, sticky="w", padx=10)

        # Scheidingslijn
        separator3 = ctk.CTkFrame(self.status_bar, width=1, height=20, fg_color="gray")
        separator3.grid(row=0, column=5, padx=5)

        # Zoom indicator
        self.status_zoom_label = ctk.CTkLabel(
            self.status_bar, text="Zoom: 100%", anchor="w", width=100
        )
        self.status_zoom_label.grid(row=0, column=6, sticky="w", padx=10)

        # Scheidingslijn
        separator4 = ctk.CTkFrame(self.status_bar, width=1, height=20, fg_color="gray")
        separator4.grid(row=0, column=7, padx=5)

        # Map info label (bestandsinfo, grootte)
        self.status_map_info = ctk.CTkLabel(
            self.status_bar, text="Geen kaart geladen", anchor="e"
        )
        self.status_map_info.grid(row=0, column=8, sticky="e", padx=10)

        # Configureer statusbalk grid
        self.status_bar.grid_columnconfigure(0, weight=0)  # Status vaste breedte
        self.status_bar.grid_columnconfigure(1, weight=0)  # Separator vaste breedte
        self.status_bar.grid_columnconfigure(2, weight=0)  # Positie vaste breedte
        self.status_bar.grid_columnconfigure(3, weight=0)  # Separator vaste breedte
        self.status_bar.grid_columnconfigure(4, weight=0)  # Laag vaste breedte
        self.status_bar.grid_columnconfigure(5, weight=0)  # Separator vaste breedte
        self.status_bar.grid_columnconfigure(6, weight=0)  # Zoom vaste breedte
        self.status_bar.grid_columnconfigure(7, weight=0)  # Separator vaste breedte
        self.status_bar.grid_columnconfigure(8, weight=1)  # Map info vult de rest

    def _create_widgets(self):
        """Maakt de verschillende UI-widgets in de panelen."""
        # Map info panel (boven canvas)
        self.info_panel = ctk.CTkFrame(self.map_area)
        self.info_panel.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Kaartafmetingen indicator
        self.dimensions_label = ctk.CTkLabel(
            self.info_panel,
            text=f"Kaartafmetingen: {
                self.model.width}x{
                self.model.height} tiles",
            anchor="w",
        )
        self.dimensions_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

        # Actieve laag indicator
        self.active_layer_label = ctk.CTkLabel(
            self.info_panel, text="Actieve laag: Terrein", anchor="e"
        )
        self.active_layer_label.grid(row=0, column=1, sticky="e", padx=10, pady=5)

        # Grid layout voor info panel
        self.info_panel.grid_columnconfigure(0, weight=1)
        self.info_panel.grid_columnconfigure(1, weight=1)

        # Map canvas in midden paneel
        self.map_canvas = MapCanvas(
            self.map_area,
            model=self.model,
            config=self.config,
            # width/height worden nu door grid bepaald, niet hier instellen
            on_cell_change=self._on_cell_changed,
            on_mouse_position=self._update_position_label,
        )
        self.map_canvas.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Terrein panel (links)
        self.terrain_panel = TerrainPanel(
            self.left_panel,
            config=self.config,
            on_terrain_selected=self._on_terrain_selected,
        )
        self.terrain_panel.pack(fill="both", expand=True, padx=5, pady=5)

        # Layers panel (rechts)
        self.layer_panel = LayerPanel(
            self.right_panel,
            model=self.model,
            on_active_layer_changed=self._on_active_layer_changed,
            on_layer_visibility_changed=self._on_layer_visibility_changed,
            on_layer_locked_changed=self._on_layer_locked_changed,
        )
        self.layer_panel.pack(fill="both", expand=True, padx=5, pady=5)

        # Minimap frame in de rechteronderhoek van de canvas
        if self.minimap_visible:
            self._setup_minimap()

    def _setup_minimap(self):
        """Maakt de minimap aan in de rechteronderhoek van de canvas."""
        # Minimap wordt volledig afgehandeld in de map_canvas module
        pass

    def _setup_bindings(self):
        """Stelt event bindings in voor interactie."""
        # Controleer of map_canvas bestaat
        if not hasattr(self, "map_canvas"):
            print("Fout: map_canvas niet geïnitialiseerd voor bindings.")
            return

        # Canvas bindings voor zoom (muis wiel)
        # Gebruik lambda om event door te geven aan handler
        self.map_canvas.bind(
            "<MouseWheel>", lambda e: self._on_mousewheel(e)
        )  # Windows
        self.map_canvas.bind(
            "<Button-4>", lambda e: self._on_mousewheel(e)
        )  # Linux scroll up
        self.map_canvas.bind(
            "<Button-5>", lambda e: self._on_mousewheel(e)
        )  # Linux scroll down

    def _setup_tooltips(self):
        """Voegt tooltips toe aan UI-elementen."""
        # Controleer of alle elementen bestaan voordat tooltips worden
        # toegevoegd
        try:
            if hasattr(self, "terrain_panel"):
                CTkToolTip(
                    self.terrain_panel,
                    "Selecteer hier het terreintype dat je wilt plaatsen.\n"
                    "Klik op een terreintype om het te selecteren.",
                )
            if hasattr(self, "dimensions_label"):
                CTkToolTip(
                    self.dimensions_label,
                    "Huidige afmetingen van de kaart in aantal cellen.",
                )
            if hasattr(self, "active_layer_label"):
                CTkToolTip(
                    self.active_layer_label,
                    "De momenteel geselecteerde laag waarop wordt getekend.",
                )
            if hasattr(self, "status_label"):
                CTkToolTip(self.status_label, "Statusmeldingen en feedback")
            if hasattr(self, "position_label"):
                CTkToolTip(
                    self.position_label, "Huidige positie van de muiscursor op de kaart"
                )
            if hasattr(self, "status_layer_label"):
                CTkToolTip(self.status_layer_label, "Actieve tekenlaag")
            if hasattr(self, "status_zoom_label"):
                CTkToolTip(self.status_zoom_label, "Huidige zoomfactor")
            if hasattr(self, "status_map_info"):
                CTkToolTip(self.status_map_info, "Informatie over de huidige kaart")
        except Exception as e:
            print(f"Fout bij instellen tooltips: {e}")

    def _setup_autosave(self, interval_ms):
        """
        Stelt de autosave timer in.

        Args:
                interval_ms (int): Interval in milliseconden
        """

        def autosave_callback():
            try:
                if self.model.has_unsaved_changes() and self.model.current_file:
                    print(
                        f"Autosave: Wijzigingen gedetecteerd in {
                            self.model.current_file}, bezig met opslaan..."
                    )
                    saved = self._save_map()  # Gebruik de bestaande save functie
                    if saved:
                        self.set_status(
                            f"Automatisch opgeslagen: {
                                time.strftime('%H:%M:%S')}",
                            duration=5000,
                        )
                    else:
                        print("Autosave: Opslaan mislukt.")
                else:
                    # print("Autosave: Geen wijzigingen of geen bestand om op te slaan.")
                    pass
            except Exception as e:
                print(f"Fout tijdens autosave callback: {e}")
            finally:
                # Hernieuw de timer ALTIJD, tenzij de app sluit
                if self.master.winfo_exists():  # Controleer of hoofdvenster nog bestaat
                    self.master.after(interval_ms, autosave_callback)

        # Start de timer
        print(f"Autosave ingesteld met interval: {interval_ms} ms")
        self.master.after(interval_ms, autosave_callback)

    def _update_ui_from_model(self):
        """Update de UI-elementen met data uit het model."""
        print("Updating UI from model...")
        try:
            # Update dimensies label
            if hasattr(self, "dimensions_label"):
                self.dimensions_label.configure(
                    text=f"Kaartafmetingen: {
                        self.model.width}x{
                        self.model.height} tiles"
                )

            # Update actieve laag label
            active_layer = self.model.active_layer
            if hasattr(self, "active_layer_label"):
                if active_layer:
                    self.active_layer_label.configure(
                        text=f"Actieve laag: {active_layer.name}"
                    )
                else:
                    self.active_layer_label.configure(text="Actieve laag: -")

            # Update venster titel
            self._update_window_title()

            # Update undo/redo status
            self._update_undo_redo_status()

            # Update layer panel met model data
            if hasattr(self, "layer_panel") and hasattr(
                self.layer_panel, "update_layer_list"
            ):
                self.layer_panel.update_layer_list()
            else:
                print("Layer panel of update_layer_list niet gevonden.")

            # Herlaad canvas met model data
            if hasattr(self, "map_canvas") and hasattr(self.map_canvas, "redraw_map"):
                self.map_canvas.redraw_map()
            else:
                print("Map canvas of redraw_map niet gevonden.")

            # Update alle statusbalk elementen
            self._update_status_bar()
            print("UI update voltooid.")
        except Exception as e:
            print(f"Fout tijdens UI update: {e}")
            messagebox.showerror(
                "UI Update Fout", f"Kon de UI niet bijwerken:\n{e}", parent=self.master
            )

    def _update_window_title(self):
        """Update de venstertitel met huidige bestandsnaam."""
        try:
            title = self.config.get("app_name", "Tri-Sharira Map Editor")

            if self.model.current_file:
                filename = os.path.basename(self.model.current_file)
                title = f"{filename} - {title}"

            if self.model.has_unsaved_changes():
                title = f"*{title}"

            self.master.title(title)
        except Exception as e:
            print(f"Fout bij updaten window title: {e}")
            self.master.title("Tri-Sharira Map Editor - Fout")

    def _update_undo_redo_status(self):
        """Update de status van undo/redo menu-items."""
        try:
            # Update Edit menu undo/redo items
            # Moet wellicht via self.menu_bar gaan ipv direct nametowidget
            edit_menu = (
                self.menu_bar.winfo_children()[1]
                if len(self.menu_bar.winfo_children()) > 1
                else None
            )  # Aanname: 2e menu is Bewerken
            if not edit_menu:  # Fallback via naam (minder betrouwbaar)
                edit_menu = self.menu_bar.nametowidget(
                    self.menu_bar.entrycget("Bewerken", "menu")
                )

            if edit_menu:
                undo_state = tk.NORMAL if self.model.can_undo() else tk.DISABLED
                redo_state = tk.NORMAL if self.model.can_redo() else tk.DISABLED
                edit_menu.entryconfig("Ongedaan maken", state=undo_state)
                edit_menu.entryconfig("Opnieuw uitvoeren", state=redo_state)
            else:
                print("Kon Bewerken menu niet vinden voor undo/redo status.")
        except Exception as e:
            print(f"Fout bij updaten undo/redo status: {e}")

    def _update_recent_files_menu(self):
        """Update het recente bestanden submenu."""
        try:
            # Leeg het menu eerst
            self.recent_files_menu.delete(0, tk.END)

            # Voeg recente bestanden toe
            recent_files = self.config.get("recent_files", [])

            if recent_files:
                for filepath in recent_files:
                    # Verkorte weergave van het pad
                    if len(filepath) > 60:
                        display_path = "..." + filepath[-57:]
                    else:
                        display_path = filepath

                    self.recent_files_menu.add_command(
                        label=display_path,
                        command=lambda f=filepath: self._open_recent_file(f),
                    )
            else:
                # Als er geen recente bestanden zijn
                self.recent_files_menu.add_command(
                    label="(Geen recente bestanden)", state=tk.DISABLED
                )

            # Voeg separator en wis geschiedenis optie toe
            if recent_files:
                self.recent_files_menu.add_separator()
                self.recent_files_menu.add_command(
                    label="Geschiedenis wissen", command=self._clear_recent_files
                )
        except Exception as e:
            print(f"Fout bij updaten recente bestanden menu: {e}")

    def set_status(self, message, duration=None):
        """
        Stelt een bericht in de statusbalk in, annuleert vorige timers.

        Args:
                message (str): Het weer te geven bericht
                duration (int, optional): Tijdsduur in ms. None = permanent.
        """
        # Annuleer eerst een eventuele vorige timer
        if hasattr(self, "_status_timer_id") and self._status_timer_id is not None:
            try:
                self.master.after_cancel(self._status_timer_id)
            except Exception as e:
                print(f"Kon timer niet annuleren: {e}")  # Voorkom crash
            self._status_timer_id = None

        # Stel het nieuwe bericht in
        if hasattr(self, "status_label"):  # Controleer of status_label bestaat
            self.status_label.configure(text=message)
        else:
            print("Fout: self.status_label niet gevonden in set_status")
            # We stoppen hier niet per se, misschien is statusbalk optioneel?
            # return # Stop als label niet bestaat

        # Als een tijdsduur is opgegeven, start een nieuwe timer en sla ID op
        if duration is not None and duration > 0:
            try:
                # Zorg dat master bestaat en after methode heeft
                if hasattr(self.master, "after"):
                    self._status_timer_id = self.master.after(
                        duration,
                        self._reset_status_to_default,  # Roep aparte methode aan
                    )
                else:
                    print("Fout: self.master heeft geen 'after' methode.")
                    self._status_timer_id = None
            except Exception as e:
                print(f"Kon timer niet starten: {e}")
                self._status_timer_id = None

    def _reset_status_to_default(self):
        """Reset de statusbalk naar de standaardtekst."""
        if hasattr(self, "status_label"):
            self.status_label.configure(text="Gereed")
        self._status_timer_id = None  # Reset timer ID

    def _update_position_label(self, row, col):
        """
        Update de positie-indicator in de statusbalk.

        Args:
                row (int): Rij onder de muis
                col (int): Kolom onder de muis
        """
        # Controleer of position_label bestaat
        if not hasattr(self, "position_label"):
            return

        if row is not None and col is not None:
            terrain = ""
            try:
                # Top cell bepalen voor weergave in statusbalk
                layer_idx, value = self.model.get_top_cell(row, col)
                if (
                    layer_idx is not None
                    and value
                    and layer_idx < len(self.model.layers)
                ):
                    layer_name = self.model.layers[layer_idx].name
                    terrain = f" [{value} op {layer_name}]"
            except Exception as e:
                print(f"Fout bij ophalen top cell info: {e}")
                terrain = " [Fout]"

            self.position_label.configure(text=f"Positie: {col},{row}{terrain}")
        else:
            self.position_label.configure(text="Positie: -")

    def _update_status_bar(self):
        """Update alle elementen in de statusbalk met actuele informatie."""
        try:
            # Update laag info
            active_layer = self.model.active_layer
            if hasattr(self, "status_layer_label"):
                if active_layer:
                    self.status_layer_label.configure(text=f"Laag: {active_layer.name}")
                else:
                    self.status_layer_label.configure(text="Laag: -")

            # Update zoom info
            zoom_percentage = int(self.zoom_factor * 100)
            if hasattr(self, "status_zoom_label"):
                self.status_zoom_label.configure(text=f"Zoom: {zoom_percentage}%")

            # Update map info
            if hasattr(self, "status_map_info"):
                if self.model.current_file:
                    filename = os.path.basename(self.model.current_file)
                    map_size = f"{self.model.width}x{self.model.height}"
                    self.status_map_info.configure(text=f"{filename} ({map_size})")
                else:
                    map_size = f"{self.model.width}x{self.model.height}"
                    self.status_map_info.configure(text=f"Nieuwe kaart ({map_size})")
        except Exception as e:
            print(f"Fout bij updaten statusbalk: {e}")

    # --- Event Handlers ---

    def _on_terrain_selected(self, terrain_id):
        """
        Handler voor terrein selectie uit het terreinpaneel.

        Args:
                terrain_id (str): ID van geselecteerd terrein
        """
        self.current_terrain = terrain_id
        try:
            terrain_desc = self.config.get_terrain_types().get(terrain_id, "")
            self.set_status(f"Geselecteerd: {terrain_id} - {terrain_desc}")
        except Exception as e:
            print(f"Fout bij ophalen terrein description: {e}")
            self.set_status(f"Geselecteerd: {terrain_id}")

        # Update terrein in map canvas
        if hasattr(self, "map_canvas"):
            self.map_canvas.set_current_terrain(terrain_id)

    def _on_cell_changed(self, row, col, new_value):
        """
        Handler voor wanneer een cel is gewijzigd.

        Args:
                row (int): Rij
                col (int): Kolom
                new_value (str): Nieuwe waarde
        """
        # Update undo/redo status
        self._update_undo_redo_status()

        # Update window title indien nodig
        if self.model.has_unsaved_changes():
            self._update_window_title()

    def _on_active_layer_changed(self, layer_index):
        """
        Handler voor wanneer de actieve laag gewijzigd is.

        Args:
                layer_index (int): Index van de nieuwe actieve laag
        """
        # Update de actieve laag label
        active_layer = self.model.active_layer
        if hasattr(self, "active_layer_label"):
            if active_layer:
                self.active_layer_label.configure(
                    text=f"Actieve laag: {active_layer.name}"
                )
            else:
                self.active_layer_label.configure(text="Actieve laag: -")

        # Update statusbalk laag info
        self._update_status_bar()

        # Update canvas (optioneel, alleen als rendering verandert)
        # self.map_canvas.redraw_map()

    def _on_layer_visibility_changed(self, layer_index, visible):
        """
        Handler voor wanneer de zichtbaarheid van een laag gewijzigd is.

        Args:
                layer_index (int): Index van de laag
                visible (bool): Nieuwe zichtbaarheidsstatus
        """
        # Update canvas
        if hasattr(self, "map_canvas"):
            self.map_canvas.redraw_map()

    def _on_layer_locked_changed(self, layer_index, locked):
        """
        Handler voor wanneer de vergrendelingsstatus van een laag gewijzigd is.

        Args:
                layer_index (int): Index van de laag
                locked (bool): Nieuwe vergrendelingsstatus
        """
        # Update canvas (optioneel, misschien alleen cursor veranderen?)
        # self.map_canvas.redraw_map()
        pass  # Geen directe actie nodig hier, canvas checkt zelf lock status

    def _on_mousewheel(self, event):
        """
        Handler voor muiswiel events voor zoom.

        Args:
                event: Tkinter event
        """
        # Bepaal zoom richting en factor
        # event.delta is betrouwbaarder dan event.num op verschillende OS'en
        if event.delta > 0:  # Scroll up/in
            self._zoom_in()
        elif event.delta < 0:  # Scroll down/out
            self._zoom_out()

    def _on_closing(self):
        """Handler voor wanneer het venster gesloten wordt."""
        # Controleer of er onopgeslagen wijzigingen zijn
        try:
            if self.model.has_unsaved_changes():
                answer = messagebox.askyesnocancel(
                    "Niet-opgeslagen wijzigingen",
                    "Er zijn onopgeslagen wijzigingen. Wil je opslaan voordat je afsluit?",
                    parent=self.master,
                )

                if answer is True:  # Ja
                    saved = self._save_map()
                    if not saved:
                        # Als opslaan mislukt of geannuleerd is, annuleer
                        # afsluiten
                        return
                elif answer is None:  # Cancel
                    return
                # else: answer is False (Nee), ga door met sluiten

            # Sla instellingen op (venstergrootte, etc.)
            self._save_settings()

        except Exception as e:
            print(f"Fout tijdens afsluiten (check wijzigingen/save settings): {e}")
            # Probeer toch door te gaan met sluiten
        finally:
            # Sluit het venster
            print("Map Editor wordt afgesloten.")
            self.master.destroy()

    def _save_settings(self):
        """Slaat de huidige instellingen op."""
        try:
            # Venstergrootte
            if (
                self.master.winfo_exists()
                and self.master.winfo_width() > 100
                and self.master.winfo_height() > 100
            ):
                self.config.set("window_width", self.master.winfo_width())
                self.config.set("window_height", self.master.winfo_height())

            # Zoom
            self.config.set("canvas_zoom_factor", self.zoom_factor)

            # Grid en minimap
            self.config.set("show_grid", self.show_grid)
            self.config.set("show_minimap", self.minimap_visible)
            print("Instellingen opgeslagen.")
        except Exception as e:
            print(f"Kon instellingen niet opslaan: {e}")

    # --- UI Action Methods ---

    def _new_map(self):
        """Maakt een nieuwe, lege kaart."""
        try:
            if self.model.has_unsaved_changes():
                answer = messagebox.askyesnocancel(
                    "Niet-opgeslagen wijzigingen",
                    "Er zijn onopgeslagen wijzigingen. Wil je opslaan voordat je een nieuwe kaart maakt?",
                    parent=self.master,
                )

                if answer is True:  # Ja
                    saved = self._save_map()
                    if not saved:
                        return  # Stop als opslaan mislukt/geannuleerd
                elif answer is None:
                    return  # Cancel

            # Laat gebruiker nieuwe afmetingen kiezen
            new_width = self.model.width
            new_height = self.model.height

            dialog = ResizeDialog(
                self.master, initial_width=new_width, initial_height=new_height
            )
            if dialog.result:
                new_width, new_height = dialog.result
            else:
                return  # Geannuleerd

            # Maak nieuwe kaart
            self.model.new_map(new_width, new_height)

            # Update UI
            self._update_ui_from_model()

            self.set_status(f"Nieuwe kaart aangemaakt ({new_width}x{new_height})")
        except Exception as e:
            messagebox.showerror(
                "Fout bij Nieuwe Kaart",
                f"Kon geen nieuwe kaart maken:\n{e}",
                parent=self.master,
            )

    def _open_map(self):
        """Opent een kaartbestand via een bestandsdialoog."""
        try:
            if self.model.has_unsaved_changes():
                answer = messagebox.askyesnocancel(
                    "Niet-opgeslagen wijzigingen",
                    "Er zijn onopgeslagen wijzigingen. Wil je opslaan voordat je een nieuwe kaart opent?",
                    parent=self.master,
                )
                if answer is True:  # Ja
                    saved = self._save_map()
                    if not saved:
                        return  # Stop
                elif answer is None:
                    return  # Cancel

            # Bepaal initiële map
            initial_dir = (
                os.path.dirname(self.model.current_file)
                if self.model.current_file
                else self.config.get("default_save_dir", "./data")
            )
            os.makedirs(initial_dir, exist_ok=True)  # Zorg dat map bestaat

            # Toon bestandsdialoog
            file_path = filedialog.askopenfilename(
                parent=self.master,
                title="Open kaartbestand",
                initialdir=initial_dir,
                filetypes=[("JSON bestanden", "*.json"), ("Alle bestanden", "*.*")],
            )

            if not file_path:
                return  # Geannuleerd

            # Laad de kaart
            success = self.model.load_map(file_path)

            if success:
                self._update_ui_from_model()
                self._update_recent_files_menu()  # Update recente lijst
                self.set_status(
                    f"Kaart geladen: {
                        os.path.basename(file_path)}"
                )
            else:
                messagebox.showerror(
                    "Fout bij openen",
                    f"Kon het bestand niet openen: {file_path}",
                    parent=self.master,
                )
        except Exception as e:
            messagebox.showerror(
                "Fout bij Openen", f"Kon kaart niet openen:\n{e}", parent=self.master
            )

    def _open_recent_file(self, filepath):
        """
        Opent een bestand uit de recente bestanden lijst.

        Args:
                filepath (str): Volledig pad naar het bestand
        """
        try:
            if not os.path.exists(filepath):
                messagebox.showerror(
                    "Bestand niet gevonden",
                    f"Het bestand bestaat niet meer: {filepath}",
                    parent=self.master,
                )
                # Verwijder uit recente bestanden
                recent_files = self.config.get("recent_files", [])
                if filepath in recent_files:
                    recent_files.remove(filepath)
                    self.config.set("recent_files", recent_files)
                    self._update_recent_files_menu()
                return

            # Controleer onopgeslagen wijzigingen
            if self.model.has_unsaved_changes():
                answer = messagebox.askyesnocancel(
                    "Niet-opgeslagen wijzigingen",
                    "Er zijn onopgeslagen wijzigingen. Wil je opslaan voordat je een nieuw bestand opent?",
                    parent=self.master,
                )
                if answer is True:  # Ja
                    saved = self._save_map()
                    if not saved:
                        return  # Stop
                elif answer is None:
                    return  # Cancel

            # Laad de kaart
            success = self.model.load_map(filepath)

            if success:
                self._update_ui_from_model()
                self._update_recent_files_menu()  # Zet bovenaan
                self.set_status(f"Kaart geladen: {os.path.basename(filepath)}")
            else:
                messagebox.showerror(
                    "Fout bij openen",
                    f"Kon het bestand niet openen: {filepath}",
                    parent=self.master,
                )
        except Exception as e:
            messagebox.showerror(
                "Fout bij Openen Recent",
                f"Kon recent bestand niet openen:\n{e}",
                parent=self.master,
            )

    def _clear_recent_files(self):
        """Wist de lijst met recente bestanden."""
        try:
            self.config.set("recent_files", [])
            self._update_recent_files_menu()
            self.set_status("Recente bestanden gewist", duration=3000)
        except Exception as e:
            print(f"Fout bij wissen recente bestanden: {e}")

    def _save_map(self):
        """
        Slaat de huidige kaart op.

        Returns:
                bool: True als succesvol of geannuleerd, False bij fout
        """
        try:
            if not self.model.current_file:
                return (
                    self._save_map_as()
                )  # Roep 'Save As' aan als er geen huidig pad is

            success = self.model.save_map()  # Sla op naar huidig pad/formaat

            if success:
                self._update_window_title()  # Verwijder '*'
                self.set_status(
                    f"Kaart opgeslagen: {
                        os.path.basename(
                            self.model.current_file)}",
                    duration=3000,
                )
                return True
            else:
                messagebox.showerror(
                    "Fout bij opslaan", "Kon de kaart niet opslaan.", parent=self.master
                )
                return False
        except Exception as e:
            messagebox.showerror(
                "Fout bij Opslaan", f"Kon kaart niet opslaan:\n{e}", parent=self.master
            )
            return False

    def _save_map_as(self):
        """
        Slaat de kaart op onder een nieuwe naam.

        Returns:
                bool: True als succesvol of geannuleerd, False bij fout
        """
        try:
            # Bepaal initiële map en bestandsnaam
            initial_dir = (
                os.path.dirname(self.model.current_file)
                if self.model.current_file
                else self.config.get("default_save_dir", "./data")
            )
            initial_file = (
                os.path.basename(self.model.current_file)
                if self.model.current_file
                else "nieuwe_kaart.json"
            )
            os.makedirs(initial_dir, exist_ok=True)  # Zorg dat map bestaat

            # Toon bestandsdialoog
            file_path = filedialog.asksaveasfilename(
                parent=self.master,
                title="Kaart opslaan als",
                initialdir=initial_dir,
                initialfile=initial_file,
                defaultextension=".json",
                filetypes=[("JSON bestanden", "*.json"), ("Alle bestanden", "*.*")],
            )

            if not file_path:
                return True  # Geannuleerd door gebruiker, beschouw als 'succesvol' geannuleerd

            # Sla op als JSON
            success = self.model.save_map(file_path)

            if success:
                self._update_window_title()  # Update titel met nieuwe naam
                self._update_recent_files_menu()  # Voeg toe aan recente lijst
                self.set_status(
                    f"Kaart opgeslagen als: {
                        os.path.basename(file_path)}",
                    duration=3000,
                )
                return True
            else:
                messagebox.showerror(
                    "Fout bij opslaan",
                    f"Kon de kaart niet opslaan als: {file_path}",
                    parent=self.master,
                )
                return False
        except Exception as e:
            messagebox.showerror(
                "Fout bij Opslaan Als",
                f"Kon kaart niet opslaan als:\n{e}",
                parent=self.master,
            )
            return False

    def _export_map(self):
        """
        Exporteert de kaart naar een JSON-formaat en toont deze in een dialoog.
        """
        try:
            export_string = self.model.export_to_string()

            # Toon exportdialoog
            dialog = ExportDialog(
                self.master,
                title="Geëxporteerde JSON Kaart",
                export_text=export_string,
                format_type="json",
            )
        except Exception as e:
            messagebox.showerror(
                "Fout bij Exporteren",
                f"Kon kaart niet exporteren:\n{e}",
                parent=self.master,
            )

    def _export_as_image(self):
        """Exporteert de kaart als afbeelding."""
        try:
            # Bepaal bestandspad voor opslaan
            initial_dir = self.config.get("export_dir", "./exports")
            os.makedirs(initial_dir, exist_ok=True)

            # Stel initiële bestandsnaam voor
            if self.model.current_file:
                base_filename = os.path.splitext(
                    os.path.basename(self.model.current_file)
                )[0]
                initial_filename = f"{base_filename}_export.png"
            else:
                initial_filename = "map_export.png"

            # Toon bestandsdialoog
            file_path = filedialog.asksaveasfilename(
                parent=self.master,
                title="Exporteer als afbeelding",
                initialdir=initial_dir,
                initialfile=initial_filename,
                defaultextension=".png",
                filetypes=[
                    ("PNG bestanden", "*.png"),
                    ("JPEG bestanden", "*.jpg;*.jpeg"),
                    ("Alle bestanden", "*.*"),
                ],
            )

            if not file_path:
                return  # Geannuleerd

            # Render en exporteer de kaart
            # Vraag canvas om een afbeelding te maken
            if not hasattr(self, "map_canvas"):
                messagebox.showerror(
                    "Fout", "Map Canvas is niet beschikbaar.", parent=self.master
                )
                return

            success = self.map_canvas.export_as_image(file_path)

            if success:
                self.set_status(
                    f"Kaart geëxporteerd als afbeelding: {
                        os.path.basename(file_path)}",
                    duration=5000,
                )
                # Vraag of de gebruiker de afbeelding wil openen
                if messagebox.askyesno(
                    "Exporteren voltooid",
                    f"Kaart geëxporteerd als:\n{file_path}\n\nWil je de afbeelding openen?",
                    parent=self.master,
                ):
                    # Open afbeelding in standaard programma
                    try:
                        if os.name == "nt":  # Windows
                            os.startfile(os.path.normpath(file_path))
                        elif sys.platform == "darwin":  # macOS
                            subprocess.call(("open", file_path))
                        else:  # Linux
                            import subprocess

                            subprocess.call(("xdg-open", file_path))
                    except Exception as e:
                        messagebox.showerror(
                            "Fout bij openen",
                            f"Kon de afbeelding niet openen:\n{
                                str(e)}",
                            parent=self.master,
                        )
            else:
                messagebox.showerror(
                    "Fout bij exporteren",
                    "Kon de kaart niet exporteren als afbeelding.",
                    parent=self.master,
                )

        except Exception as e:
            messagebox.showerror(
                "Fout bij Exporteren Afbeelding",
                f"Kon kaart niet exporteren:\n{e}",
                parent=self.master,
            )

    def _resize_map_dialog(self):
        """Toont een dialoog om de kaartgrootte te wijzigen."""
        try:
            dialog = ResizeDialog(
                self.master,
                initial_width=self.model.width,
                initial_height=self.model.height,
            )

            if dialog.result:
                new_width, new_height = dialog.result
                if new_width != self.model.width or new_height != self.model.height:
                    # Wijzig de grootte
                    old_width, old_height = self.model.resize(new_width, new_height)
                    # Update UI
                    self._update_ui_from_model()
                    self.set_status(
                        f"Kaartgrootte gewijzigd van {old_width}x{old_height} naar {new_width}x{new_height}"
                    )
        except Exception as e:
            messagebox.showerror(
                "Fout bij Grootte Wijzigen",
                f"Kon kaartgrootte niet wijzigen:\n{e}",
                parent=self.master,
            )

    def _fill_all(self):
        """Vult de hele actieve laag met het huidige terreintype."""
        try:
            # Controleer of de laag niet vergrendeld is
            if self.model.active_layer and self.model.active_layer.locked:
                messagebox.showwarning(
                    "Laag vergrendeld",
                    "De actieve laag is vergrendeld.",
                    parent=self.master,
                )
                return

            # Vraag bevestiging
            if messagebox.askyesno(
                "Alles vullen",
                f"Wil je de hele actieve laag vullen met '{
                        self.current_terrain}'?",
                parent=self.master,
            ):
                # Vul de hele laag
                success = self.model.fill(self.current_terrain)
                if success:
                    self.map_canvas.redraw_map()
                    self._update_undo_redo_status()
                    if self.model.has_unsaved_changes():
                        self._update_window_title()
                    self.set_status(
                        f"Laag gevuld met '{
                            self.current_terrain}'"
                    )
        except Exception as e:
            messagebox.showerror(
                "Fout bij Vullen", f"Kon laag niet vullen:\n{e}", parent=self.master
            )

    def _undo(self):
        """Maakt de laatste actie ongedaan."""
        try:
            if self.model.can_undo():
                success, action_type = self.model.undo()
                if success:
                    self._update_ui_from_model()
                    self.set_status(f"Ongedaan gemaakt: {action_type}", duration=3000)
        except Exception as e:
            messagebox.showerror(
                "Fout bij Ongedaan Maken",
                f"Kon actie niet ongedaan maken:\n{e}",
                parent=self.master,
            )

    def _redo(self):
        """Voert de laatst ongedaan gemaakte actie opnieuw uit."""
        try:
            if self.model.can_redo():
                success, action_type = self.model.redo()
                if success:
                    self._update_ui_from_model()
                    self.set_status(f"Opnieuw uitgevoerd: {action_type}", duration=3000)
        except Exception as e:
            messagebox.showerror(
                "Fout bij Opnieuw Uitvoeren",
                f"Kon actie niet opnieuw uitvoeren:\n{e}",
                parent=self.master,
            )

    def _zoom_in(self):
        """Zoomt in op de kaart."""
        old_zoom = self.zoom_factor
        self.zoom_factor = min(
            self.config.get("max_zoom", 3.0), self.zoom_factor * 1.2
        )  # Gebruik config voor max

        if abs(old_zoom - self.zoom_factor) > 0.001:  # Check op kleine verandering
            if hasattr(self, "map_canvas") and hasattr(self.map_canvas, "set_zoom"):
                self.map_canvas.set_zoom(self.zoom_factor)
            else:
                print("Fout: self.map_canvas of set_zoom niet gevonden in _zoom_in")

            # Update statusbalk
            zoom_percentage = int(self.zoom_factor * 100)
            if hasattr(self, "status_zoom_label"):
                self.status_zoom_label.configure(text=f"Zoom: {zoom_percentage}%")

            self.set_status(f"Zoom: {zoom_percentage}%", duration=2000)

    def _zoom_out(self):
        """Zoomt uit op de kaart."""
        old_zoom = self.zoom_factor
        self.zoom_factor = max(
            self.config.get("min_zoom", 0.3), self.zoom_factor / 1.2
        )  # Gebruik config voor min

        if abs(old_zoom - self.zoom_factor) > 0.001:  # Check op kleine verandering
            if hasattr(self, "map_canvas") and hasattr(self.map_canvas, "set_zoom"):
                self.map_canvas.set_zoom(self.zoom_factor)
            else:
                print("Fout: self.map_canvas of set_zoom niet gevonden in _zoom_out")

            # Update statusbalk
            zoom_percentage = int(self.zoom_factor * 100)
            if hasattr(self, "status_zoom_label"):
                self.status_zoom_label.configure(text=f"Zoom: {zoom_percentage}%")

            self.set_status(f"Zoom: {zoom_percentage}%", duration=2000)

    def _zoom_reset(self):
        """Reset de zoom naar 100%."""
        old_zoom = self.zoom_factor
        self.zoom_factor = 1.0

        if abs(old_zoom - self.zoom_factor) > 0.001:  # Check op kleine verandering
            if hasattr(self, "map_canvas") and hasattr(self.map_canvas, "set_zoom"):
                self.map_canvas.set_zoom(self.zoom_factor)
            else:
                print("Fout: self.map_canvas of set_zoom niet gevonden in _zoom_reset")

            # Update statusbalk
            if hasattr(self, "status_zoom_label"):
                self.status_zoom_label.configure(text="Zoom: 100%")

            self.set_status("Zoom: 100%", duration=2000)

    def _toggle_grid(self):
        """Schakelt de zichtbaarheid van het raster."""
        self.show_grid = self.show_grid_var.get()
        if hasattr(self, "map_canvas"):
            self.map_canvas.set_grid_visible(self.show_grid)
        setting = "ingeschakeld" if self.show_grid else "uitgeschakeld"
        self.set_status(f"Raster {setting}", duration=2000)

    def _toggle_minimap(self):
        """Schakelt de zichtbaarheid van de minimap."""
        self.minimap_visible = self.minimap_var.get()
        setting = "ingeschakeld" if self.minimap_visible else "uitgeschakeld"
        self.set_status(f"Minimap {setting}", duration=2000)
        # Update de minimap zichtbaarheid in de canvas
        if hasattr(self, "map_canvas"):
            self.map_canvas.set_minimap_visible(self.minimap_visible)

    def _set_theme(self, theme):
        """
        Stelt het thema (appearance mode) in.

        Args:
                theme (str): "dark", "light" of "system"
        """
        try:
            ctk.set_appearance_mode(theme)
            self.config.set("theme_mode", theme)
            self.set_status(f"Thema gewijzigd naar: {theme}", duration=3000)
        except Exception as e:
            print(f"Fout bij instellen thema: {e}")

    def _add_layer(self):
        """Voegt een nieuwe laag toe."""
        try:
            # Vraag naam voor de nieuwe laag
            layer_name = simpledialog.askstring(
                "Nieuwe laag", "Geef een naam voor de nieuwe laag:", parent=self.master
            )
            if not layer_name:
                return  # Geannuleerd

            # Voeg laag toe
            new_index = self.model.add_layer(layer_name)

            # Update UI
            if hasattr(self, "layer_panel"):
                self.layer_panel.update_layer_list()
                self.layer_panel.set_active_layer(new_index)  # Maak nieuwe laag actief
            self._update_status_bar()  # Update statusbalk met nieuwe actieve laag

            self.set_status(f"Nieuwe laag toegevoegd: {layer_name}")
        except Exception as e:
            messagebox.showerror(
                "Fout bij Laag Toevoegen",
                f"Kon laag niet toevoegen:\n{e}",
                parent=self.master,
            )

    def _remove_layer(self):
        """Verwijdert de actieve laag."""
        try:
            if len(self.model.layers) <= 1:
                messagebox.showwarning(
                    "Kan laag niet verwijderen",
                    "Er moet minimaal één laag behouden blijven.",
                    parent=self.master,
                )
                return

            # Vraag bevestiging
            active_layer = self.model.active_layer
            if active_layer and messagebox.askyesno(
                "Laag verwijderen",
                f"Wil je de laag '{active_layer.name}' verwijderen?",
                parent=self.master,
            ):
                # Verwijder de laag
                removed_layer = self.model.remove_layer(self.model.active_layer_index)

                if removed_layer:
                    # Update UI
                    if hasattr(self, "layer_panel"):
                        self.layer_panel.update_layer_list()  # Update lijst en selectie
                    self._update_status_bar()  # Update statusbalk
                    if hasattr(self, "map_canvas"):
                        self.map_canvas.redraw_map()  # Teken opnieuw

                    self.set_status(f"Laag verwijderd: {removed_layer.name}")
        except Exception as e:
            messagebox.showerror(
                "Fout bij Laag Verwijderen",
                f"Kon laag niet verwijderen:\n{e}",
                parent=self.master,
            )

    def _move_layer(self, delta):
        """
        Verplaatst de actieve laag omhoog of omlaag.

        Args:
                delta (int): -1 voor omhoog, 1 voor omlaag
        """
        try:
            success = self.model.move_layer(delta)
            if success:
                if hasattr(self, "layer_panel"):
                    self.layer_panel.update_layer_list()
                if hasattr(self, "map_canvas"):
                    self.map_canvas.redraw_map()
                direction = "omhoog" if delta < 0 else "omlaag"
                self.set_status(f"Laag {direction} verplaatst", duration=2000)
            else:
                self.set_status("Kon laag niet verplaatsen", duration=2000)
        except Exception as e:
            messagebox.showerror(
                "Fout bij Laag Verplaatsen",
                f"Kon laag niet verplaatsen:\n{e}",
                parent=self.master,
            )

    def _show_controls(self):
        """Toont hulp voor toetsenbord en muis controls."""
        controls_text = """
Toetsenbord:
  Ctrl+N		  Nieuwe kaart
  Ctrl+O		  Openen
  Ctrl+S		  Opslaan
  Ctrl+Shift+S	  Opslaan als
  Ctrl+Z		  Ongedaan maken
  Ctrl+Y		  Opnieuw uitvoeren
  Ctrl++/=		  Inzoomen
  Ctrl+-		  Uitzoomen
  Ctrl+0		  Zoom resetten (100%)
  Del			  Geselecteerde cel(len) wissen (nog niet imp.)

Muis:
  Linkermuisknop  Terrein plaatsen
  Rechtermuisknop Terrein 'pipet' (selecteert terrein onder cursor)
  Muiswiel		  Zoomen in/uit
  Ctrl+Slepen	  Gebied selecteren (nog niet imp.)
  Shift+Klik	  Lijn tekenen (nog niet imp.)
		"""
        messagebox.showinfo("Controls", controls_text, parent=self.master)

    def _show_legend(self):
        """Toont een legenda van terreintypen."""
        try:
            terrain_types = self.config.get_terrain_types()
            categories = self.config.get("terrain_categories", {})
            legend_text = "Terrein legenda:\n\n"
            for category_name, types in categories.items():
                legend_text += f"--- {category_name} ---\n"
                for code, desc in types.items():
                    if code != " ":  # Skip leeg
                        legend_text += f"  {code} - {desc}\n"
                legend_text += "\n"
            messagebox.showinfo(
                "Terrein legenda", legend_text.strip(), parent=self.master
            )
        except Exception as e:
            messagebox.showerror(
                "Fout bij Legenda", f"Kon legenda niet tonen:\n{e}", parent=self.master
            )

    def _show_about(self):
        """Toont informatie over de Map Editor."""
        try:
            about_text = f"""
Tri-Sharira RPG Map Editor

Versie: {self.config.get("version", "0.1.0")}

Een tool voor het ontwerpen van kaarten voor de Tri-Sharira RPG game.
Ontwikkeld met Python en CustomTkinter.

© 2025 Gerald & Gemini
			"""
            messagebox.showinfo(
                "Over Map Editor", about_text.strip(), parent=self.master
            )
        except Exception as e:
            messagebox.showerror(
                "Fout bij Over", f"Kon 'Over' info niet tonen:\n{e}", parent=self.master
            )


# --- Hulpdialogen ---


class ResizeDialog:
    """Dialoog voor het wijzigen van de kaartgrootte."""

    def __init__(self, parent, initial_width=40, initial_height=30):
        self.result = None
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Kaartgrootte")
        self.dialog.geometry("300x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        # Center dialog (vereenvoudigd)
        self.dialog.after(
            10,
            lambda: self.dialog.geometry(
                f"+{
                    parent.winfo_rootx() + parent.winfo_width() // 2 - self.dialog.winfo_width() // 2}"
                f"+{
                    parent.winfo_rooty() + parent.winfo_height() // 2 - self.dialog.winfo_height() // 2}"
            ),
        )

        ctk.CTkLabel(self.dialog, text="Stel de nieuwe kaartgrootte in:").pack(
            pady=(20, 10)
        )
        input_frame = ctk.CTkFrame(self.dialog)
        input_frame.pack(fill="x", padx=20, pady=10)
        # Breedte
        width_frame = ctk.CTkFrame(input_frame)
        width_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(width_frame, text="Breedte:", width=80).pack(side="left", padx=5)
        self.width_var = tk.IntVar(value=initial_width)
        width_entry = ctk.CTkEntry(width_frame, textvariable=self.width_var, width=80)
        width_entry.pack(side="left", padx=5)
        # Hoogte
        height_frame = ctk.CTkFrame(input_frame)
        height_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(height_frame, text="Hoogte:", width=80).pack(side="left", padx=5)
        self.height_var = tk.IntVar(value=initial_height)
        height_entry = ctk.CTkEntry(
            height_frame, textvariable=self.height_var, width=80
        )
        height_entry.pack(side="left", padx=5)
        # Knoppen
        button_frame = ctk.CTkFrame(self.dialog)
        button_frame.pack(fill="x", padx=20, pady=20)
        ctk.CTkButton(button_frame, text="Annuleren", command=self.cancel).pack(
            side="right", padx=5
        )
        ctk.CTkButton(button_frame, text="OK", command=self.ok).pack(
            side="right", padx=5
        )
        width_entry.focus()  # Focus op eerste invoerveld
        self.dialog.wait_window()

    def ok(self):
        try:
            width = self.width_var.get()
            height = self.height_var.get()
            if not (
                5 <= width <= 500 and 5 <= height <= 500
            ):  # Realistischere limieten
                raise ValueError("Waarden moeten tussen 5 en 500 liggen.")
            self.result = (width, height)
            self.dialog.destroy()
        except (tk.TclError, ValueError) as e:
            messagebox.showerror(
                "Ongeldige invoer",
                f"Vul geldige getallen in (5-500).\nFout: {e}",
                parent=self.dialog,
            )

    def cancel(self):
        self.dialog.destroy()


class ExportDialog:
    """Dialoog voor het exporteren en weergeven van kaartdata als tekst."""

    def __init__(
        self, parent, title="Geëxporteerde Kaart", export_text="", format_type="json"
    ):
        self.format_type = format_type
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.after(
            10,
            lambda: self.dialog.geometry(
                f"+{
                    parent.winfo_rootx() + parent.winfo_width() // 2 - self.dialog.winfo_width() // 2}"
                f"+{
                    parent.winfo_rooty() + parent.winfo_height() // 2 - self.dialog.winfo_height() // 2}"
            ),
        )

        description = "Geëxporteerde kaartdata in JSON formaat:"
        ctk.CTkLabel(self.dialog, text=description).pack(
            padx=20, pady=(20, 5), anchor="w"
        )

        # Tekstgebied met scrollbars
        self.text_frame = ctk.CTkFrame(self.dialog)
        self.text_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.text_area = ctk.CTkTextbox(self.text_frame)
        self.text_area.pack(fill="both", expand=True, padx=5, pady=5)

        # Voeg de geëxporteerde tekst toe
        self.text_area.insert("1.0", export_text)
        self.text_area.configure(state="disabled")  # Maak read-only

        # Knoppen
        button_frame = ctk.CTkFrame(self.dialog)
        button_frame.pack(fill="x", padx=20, pady=20)

        save_button = ctk.CTkButton(
            button_frame, text="Opslaan als...", command=self.save_to_file
        )
        save_button.pack(side="left", padx=5)

        copy_button = ctk.CTkButton(
            button_frame, text="Kopieer naar klembord", command=self.copy_to_clipboard
        )
        copy_button.pack(side="left", padx=5)

        close_button = ctk.CTkButton(
            button_frame, text="Sluiten", command=self.dialog.destroy
        )
        close_button.pack(side="right", padx=5)

    def copy_to_clipboard(self):
        """Kopieert tekst naar het klembord."""
        try:
            # Haal tekst op uit read-only textbox
            self.text_area.configure(state="normal")
            text = self.text_area.get("1.0", "end-1c")
            self.text_area.configure(state="disabled")
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(text)
            messagebox.showinfo(
                "Gekopieerd",
                "De tekst is gekopieerd naar het klembord.",
                parent=self.dialog,
            )
        except Exception as e:
            messagebox.showerror(
                "Fout bij kopiëren",
                f"Kon niet kopiëren:\n{
                    str(e)}",
                parent=self.dialog,
            )

    def save_to_file(self):
        """Slaat de tekst op naar een bestand."""
        file_types = [("JSON bestanden", "*.json"), ("Alle bestanden", "*.*")]

        file_path = filedialog.asksaveasfilename(
            parent=self.dialog,
            title="Exporteren",
            filetypes=file_types,
            defaultextension=".json",
        )

        if not file_path:
            return

        try:
            self.text_area.configure(state="normal")
            text_to_save = self.text_area.get("1.0", "end-1c")
            self.text_area.configure(state="disabled")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text_to_save)
            messagebox.showinfo(
                "Opgeslagen",
                f"De tekst is opgeslagen als:\n{file_path}",
                parent=self.dialog,
            )
        except Exception as e:
            messagebox.showerror(
                "Fout bij opslaan",
                f"Kon niet opslaan:\n{
                    str(e)}",
                parent=self.dialog,
            )
