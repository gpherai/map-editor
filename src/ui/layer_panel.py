# src/ui/layer_panel.py
# Paneel voor laagbeheer in Map Editor

import customtkinter as ctk
import tkinter as tk
from tkinter import simpledialog, messagebox
from src.utils.tooltip import CTkToolTip


class LayerFrame(ctk.CTkFrame):
    """Frame voor een enkele laag in het laagbeheer paneel."""

    def __init__(
        self,
        parent,
        layer_name,
        layer_index,
        active=False,
        visible=True,
        locked=False,
        on_active=None,
        on_visible=None,
        on_locked=None,
        on_rename=None,
    ):
        """
        Initialiseert een laag frame in het lagen paneel.

        Args:
            parent: Het ouderwidget
            layer_name (str): Naam van de laag
            layer_index (int): Index van de laag in het model
            active (bool): Of deze laag actief is
            visible (bool): Of de laag zichtbaar is
            locked (bool): Of de laag vergrendeld is
            on_active: Callback wanneer deze laag actief wordt
            on_visible: Callback wanneer zichtbaarheid wijzigt
            on_locked: Callback wanneer vergrendeling wijzigt
            on_rename: Callback wanneer naam wijzigt
        """
        # Bepaal kleuren op basis van status
        fg_color = "#4C4C4C" if active else "transparent"  # Donkerder als actief

        super().__init__(parent, fg_color=fg_color, height=36, corner_radius=6)

        self.layer_name = layer_name
        self.layer_index = layer_index
        self.active = active
        self.visible = visible
        self.locked = locked

        # Callbacks
        self.on_active = on_active
        self.on_visible = on_visible
        self.on_locked = on_locked
        self.on_rename = on_rename

        # Maak UI elementen
        self._create_ui()

        # Bind acties
        self.bind("<Button-1>", self._on_click)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<Button-3>", self._on_right_click)

    def _create_ui(self):
        """Bouwt de UI voor de laag frame."""
        self.grid_columnconfigure(0, weight=0)  # Actief indicator
        self.grid_columnconfigure(1, weight=1)  # Naam (groeit mee)
        self.grid_columnconfigure(2, weight=0)  # Zichtbaar toggle
        self.grid_columnconfigure(3, weight=0)  # Vergrendel toggle

        # Actief indicator (linkerrand)
        active_color = "#FF5500" if self.active else self.cget("fg_color")
        self.active_indicator = ctk.CTkFrame(
            self, width=4, fg_color=active_color, corner_radius=0
        )
        self.active_indicator.grid(row=0, column=0, sticky="ns", padx=(0, 5))

        # Laagnaam
        self.name_label = ctk.CTkLabel(self, text=self.layer_name, anchor="w")
        self.name_label.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.name_label.bind("<Button-1>", self._on_click)

        # Voeg tooltip toe aan naam label
        CTkToolTip(
            self.name_label,
            f"Laag: {
                self.layer_name}\nKlik om actief te maken\nDubbelklik om te hernoemen",
        )

        # Zichtbaarheid toggle
        self.visible_var = tk.BooleanVar(value=self.visible)

        self.visible_switch = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.visible_var,
            command=self._toggle_visible,
            width=20,
            height=20,
            checkbox_width=16,
            checkbox_height=16,
        )
        self.visible_switch.grid(row=0, column=2, padx=5, pady=5)

        # Eye tooltip
        CTkToolTip(self.visible_switch, "Laag zichtbaarheid aan/uit")

        # Vergrendeling toggle
        self.locked_var = tk.BooleanVar(value=self.locked)

        self.locked_switch = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.locked_var,
            command=self._toggle_locked,
            width=20,
            height=20,
            checkbox_width=16,
            checkbox_height=16,
        )
        self.locked_switch.grid(row=0, column=3, padx=5, pady=5)

        # Lock tooltip
        CTkToolTip(self.locked_switch, "Laag vergrendelen tegen bewerking")

    def _on_click(self, event=None):
        """Handler voor klikken op de laag (maakt deze actief)."""
        if self.on_active:
            self.on_active(self.layer_index)

    def _on_double_click(self, event=None):
        """Handler voor dubbelklikken op de laag (hernoemen)."""
        new_name = simpledialog.askstring(
            "Laag hernoemen",
            "Nieuwe naam voor laag:",
            initialvalue=self.layer_name,
            parent=self.winfo_toplevel(),
        )

        if new_name:
            self.layer_name = new_name
            self.name_label.configure(text=new_name)

            # Update tooltip
            CTkToolTip(
                self.name_label,
                f"Laag: {
                    self.layer_name}\nKlik om actief te maken\nDubbelklik om te hernoemen",
            )

            if self.on_rename:
                self.on_rename(self.layer_index, new_name)

    def _on_right_click(self, event=None):
        """Handler voor rechts klikken op de laag (context menu)."""
        # Toon context menu
        context_menu = tk.Menu(self, tearoff=0)
        context_menu.add_command(
            label="Hernoemen", command=lambda: self._on_double_click()
        )
        context_menu.add_separator()
        context_menu.add_command(
            label="Zichtbaarheid",
            command=lambda: self._toggle_visible(),
            accelerator="✓" if self.visible else "✗",
        )
        context_menu.add_command(
            label="Vergrendelen",
            command=lambda: self._toggle_locked(),
            accelerator="✓" if self.locked else "✗",
        )

        context_menu.tk_popup(event.x_root, event.y_root)

    def _toggle_visible(self):
        """Wijzigt de zichtbaarheid van de laag."""
        self.visible = self.visible_var.get()

        if self.on_visible:
            self.on_visible(self.layer_index, self.visible)

    def _toggle_locked(self):
        """Wijzigt de vergrendeling van de laag."""
        self.locked = self.locked_var.get()

        if self.on_locked:
            self.on_locked(self.layer_index, self.locked)

    def set_active(self, active):
        """
        Stelt de actieve staat van de laag in.

        Args:
            active (bool): Of de laag actief is
        """
        self.active = active

        # Update visuele indicatoren
        active_color = "#FF5500" if active else "transparent"
        self.active_indicator.configure(fg_color=active_color)

        # Update achtergrondkleur
        bg_color = "#4C4C4C" if active else "transparent"
        self.configure(fg_color=bg_color)


class LayerPanel(ctk.CTkScrollableFrame):
    """Paneel voor het beheren van lagen in de Map Editor."""

    def __init__(
        self,
        parent,
        model,
        on_active_layer_changed=None,
        on_layer_visibility_changed=None,
        on_layer_locked_changed=None,
        **kwargs,
    ):
        """
        Initialiseert het lagen paneel.

        Args:
            parent: Het ouderwidget
            model: Het kaartmodel (MapModel)
            on_active_layer_changed: Callback bij wijzigen van actieve laag
            on_layer_visibility_changed: Callback bij wijzigen van laagzichtbaarheid
            on_layer_locked_changed: Callback bij wijzigen van laagvergrendeling
            **kwargs: Extra argumenten voor CTkScrollableFrame
        """
        super().__init__(parent, **kwargs)

        self.model = model
        self.on_active_layer_changed = on_active_layer_changed
        self.on_layer_visibility_changed = on_layer_visibility_changed
        self.on_layer_locked_changed = on_layer_locked_changed

        self.layer_frames = {}  # Houdt LayerFrame widgets bij per laag index

        # Maak UI elementen
        self._create_ui()

        # Voeg tooltips toe
        self._setup_tooltips()

    def _create_ui(self):
        """Bouwt de UI van het lagenpaneel op."""
        # Titel
        self.header_label = ctk.CTkLabel(
            self, text="Lagen", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.header_label.pack(pady=(0, 10), anchor="w")

        # Knoppenbalk
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(fill="x", pady=(0, 10))

        # Voeg laag toe knop
        self.add_layer_button = ctk.CTkButton(
            self.button_frame, text="+", width=30, command=self._add_layer
        )
        self.add_layer_button.pack(side="left", padx=5, pady=5)

        # Verwijder laag knop
        self.remove_layer_button = ctk.CTkButton(
            self.button_frame, text="-", width=30, command=self._remove_layer
        )
        self.remove_layer_button.pack(side="left", padx=5, pady=5)

        # Laag omhoog knop
        self.move_up_button = ctk.CTkButton(
            self.button_frame, text="↑", width=30, command=lambda: self._move_layer(-1)
        )
        self.move_up_button.pack(side="left", padx=5, pady=5)

        # Laag omlaag knop
        self.move_down_button = ctk.CTkButton(
            self.button_frame, text="↓", width=30, command=lambda: self._move_layer(1)
        )
        self.move_down_button.pack(side="left", padx=5, pady=5)

        # Container voor laagframes
        self.layers_container = ctk.CTkFrame(self, fg_color="transparent")
        self.layers_container.pack(fill="both", expand=True, pady=5)

        # Vul met laagframes uit het model
        self.update_layer_list()

    def _setup_tooltips(self):
        """Voegt tooltips toe aan de elementen in het laag paneel."""
        # Tooltip voor de header
        CTkToolTip(
            self.header_label,
            "Beheer de verschillende lagen van de kaart.\n"
            "Elke laag kan afzonderlijk bewerkt worden.",
        )

        # Tooltip voor de add-laag knop
        CTkToolTip(self.add_layer_button, "Voeg een nieuwe laag toe aan de kaart")

        # Tooltip voor de verwijder-laag knop
        CTkToolTip(self.remove_layer_button, "Verwijder de geselecteerde laag")

        # Tooltip voor de omhoog-knop
        CTkToolTip(self.move_up_button, "Verplaats de geselecteerde laag naar boven")

        # Tooltip voor de omlaag-knop
        CTkToolTip(
            self.move_down_button, "Verplaats de geselecteerde laag naar beneden"
        )

    def update_layer_list(self):
        """Vernieuwt de lijst met lagen op basis van het model."""
        # Verwijder bestaande laagframes
        for widget in self.layers_container.winfo_children():
            widget.destroy()

        self.layer_frames = {}

        # Nieuwe laagframes voor elk laag in model (van boven naar beneden)
        # We doorlopen het omgekeerd om de bovenste lagen bovenaan te tonen
        for i in range(len(self.model.layers) - 1, -1, -1):
            layer = self.model.layers[i]

            # Maak een frame voor deze laag
            frame = LayerFrame(
                self.layers_container,
                layer_name=layer.name,
                layer_index=i,
                active=(i == self.model.active_layer_index),
                visible=layer.visible,
                locked=layer.locked,
                on_active=self._on_layer_active,
                on_visible=self._on_layer_visible,
                on_locked=self._on_layer_locked,
                on_rename=self._on_layer_rename,
            )

            frame.pack(fill="x", pady=2)

            # Sla referentie op
            self.layer_frames[i] = frame

    def set_active_layer(self, layer_index):
        """
        Stelt de actieve laag in.

        Args:
            layer_index (int): Index van de te activeren laag
        """
        # Reset alle laagframes naar inactief
        for idx, frame in self.layer_frames.items():
            frame.set_active(idx == layer_index)

    def _on_layer_active(self, layer_index):
        """
        Handler voor activeren van een laag.

        Args:
            layer_index (int): Index van de te activeren laag
        """
        # Update model
        if self.model.set_active_layer(layer_index):
            # Update UI
            self.set_active_layer(layer_index)

            # Callback
            if self.on_active_layer_changed:
                self.on_active_layer_changed(layer_index)

    def _on_layer_visible(self, layer_index, visible):
        """
        Handler voor wijzigen van laagzichtbaarheid.

        Args:
            layer_index (int): Index van de laag
            visible (bool): Nieuwe zichtbaarheidsstatus
        """
        # Update model - laag zichtbaarheid schakelen
        self.model.toggle_layer_visibility(layer_index)

        # Callback
        if self.on_layer_visibility_changed:
            self.on_layer_visibility_changed(layer_index, visible)

    def _on_layer_locked(self, layer_index, locked):
        """
        Handler voor wijzigen van laagvergrendeling.

        Args:
            layer_index (int): Index van de laag
            locked (bool): Nieuwe vergrendelingsstatus
        """
        # Update model - laag vergrendeling schakelen
        self.model.toggle_layer_lock(layer_index)

        # Callback
        if self.on_layer_locked_changed:
            self.on_layer_locked_changed(layer_index, locked)

    def _on_layer_rename(self, layer_index, new_name):
        """
        Handler voor hernoemen van een laag.

        Args:
            layer_index (int): Index van de laag
            new_name (str): Nieuwe naam voor de laag
        """
        # Update model
        if 0 <= layer_index < len(self.model.layers):
            self.model.layers[layer_index].name = new_name
            self.model.unsaved_changes = True

    def _add_layer(self):
        """Voegt een nieuwe laag toe."""
        # Vraag gebruiker om een naam
        layer_name = simpledialog.askstring(
            "Nieuwe laag",
            "Geef een naam voor de nieuwe laag:",
            parent=self.winfo_toplevel(),
        )

        if layer_name:
            # Voeg laag toe aan model
            new_index = self.model.add_layer(layer_name)

            # Update UI
            self.update_layer_list()

            # Maak nieuwe laag actief
            self._on_layer_active(new_index)

    def _remove_layer(self):
        """Verwijdert de actieve laag."""
        # Controleer of er meer dan één laag is
        if len(self.model.layers) <= 1:
            messagebox.showwarning(
                "Kan laag niet verwijderen",
                "Er moet minimaal één laag behouden blijven.",
                parent=self.winfo_toplevel(),
            )
            return

        # Vraag bevestiging
        active_layer = self.model.active_layer
        if active_layer and messagebox.askyesno(
            "Laag verwijderen",
            f"Wil je de laag '{active_layer.name}' verwijderen?",
            parent=self.winfo_toplevel(),
        ):
            # Verwijder laag uit model
            removed_layer = self.model.remove_layer(self.model.active_layer_index)

            if removed_layer:
                # Update UI
                self.update_layer_list()

    def _move_layer(self, delta):
        """
        Verplaatst de actieve laag omhoog/omlaag.

        Args:
            delta (int): -1 voor omhoog, 1 voor omlaag
        """
        # Verplaats laag in model
        success = self.model.move_layer(delta)
        
        if success:
            # Update UI
            self.update_layer_list()
            
            # Callback
            if self.on_active_layer_changed:
                self.on_active_layer_changed(self.model.active_layer_index)
        else:
            # Toon feedback aan gebruiker - kan zijn dat de laag al bovenaan/onderaan is
            direction = "omhoog" if delta < 0 else "omlaag"
            messagebox.showinfo(
                "Kan laag niet verplaatsen",
                f"De laag kan niet verder {direction} verplaatst worden.",
                parent=self.winfo_toplevel(),
            )
