# src/utils/tooltip.py
# Tooltip widget voor CustomTkinter elementen

import customtkinter as ctk
import tkinter as tk


class CTkToolTip:
    """Een tooltip widget voor CustomTkinter elementen."""

    def __init__(
        self,
        widget,
        message,
        delay=500,
        font=None,
        bg_color=None,
        text_color=None,
        corner_radius=6,
        alpha=0.9,
        x_offset=10,
        y_offset=10,
        wraplength=180,
    ):
        """
        Creëert een tooltip voor een widget.

        Args:
            widget: Het widget waarvoor de tooltip wordt gemaakt
            message (str): De te tonen tekst
            delay (int): Vertraging voor tonen tooltip in milliseconden
            font: Lettertype voor de tooltip
            bg_color: Achtergrondkleur, None = automatisch op basis van huidige theme
            text_color: Tekstkleur, None = automatisch op basis van huidige theme
            corner_radius (int): Afronding van de hoeken
            alpha (float): Transparantie van de tooltip
            x_offset (int): Horizontale offset t.o.v. muispositie
            y_offset (int): Verticale offset t.o.v. muispositie
            wraplength (int): Aantal pixels om tekst te wrappen (0 is geen wrap)
        """
        self.widget = widget
        self.message = message
        self.delay = delay
        self.font = font
        self.corner_radius = corner_radius
        self.alpha = alpha
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.wraplength = wraplength

        # Bepaal kleuren op basis van het huidige thema
        if bg_color is None:
            self.bg_color = (
                ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
                if ctk.get_appearance_mode() == "Dark"
                else ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
            )
            if isinstance(self.bg_color, tuple):
                self.bg_color = (
                    self.bg_color[1]
                    if ctk.get_appearance_mode() == "Dark"
                    else self.bg_color[0]
                )
        else:
            self.bg_color = bg_color

        if text_color is None:
            self.text_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
            if isinstance(self.text_color, tuple):
                self.text_color = (
                    self.text_color[1]
                    if ctk.get_appearance_mode() == "Dark"
                    else self.text_color[0]
                )
        else:
            self.text_color = text_color

        # Timer voor vertraagde weergave
        self.timer_id = None

        # Tooltip venster
        self.tooltip_window = None

        # Bind events
        self.widget.bind("<Enter>", self._on_enter)
        self.widget.bind("<Leave>", self._on_leave)
        self.widget.bind("<Motion>", self._on_motion)

        # Bind voor als widget vernietigd wordt
        self.widget.bind("<Destroy>", self._on_destroy)

    def _on_enter(self, event=None):
        """Handler voor mouse enter event."""
        self._schedule_tooltip()

    def _on_leave(self, event=None):
        """Handler voor mouse leave event."""
        self._unschedule_tooltip()
        self._hide_tooltip()

    def _on_motion(self, event=None):
        """Handler voor mouse motion event."""
        # Als tooltip al zichtbaar is, verplaats het
        if self.tooltip_window:
            self._update_position(event)

    def _on_destroy(self, event=None):
        """Handler voor widget destroy event."""
        self._unschedule_tooltip()
        self._hide_tooltip()

    def _schedule_tooltip(self):
        """Plant het tonen van de tooltip in."""
        # Cancel een eventuele bestaande timer
        self._unschedule_tooltip()

        # Start nieuwe timer
        self.timer_id = self.widget.after(self.delay, self._show_tooltip)

    def _unschedule_tooltip(self):
        """Annuleert het geplande tonen van de tooltip."""
        if self.timer_id:
            self.widget.after_cancel(self.timer_id)
            self.timer_id = None

    def _show_tooltip(self):
        """Toont de tooltip."""
        # Maak nieuw venster als er nog geen is
        if not self.tooltip_window:
            # Creëer toplevel venster
            self.tooltip_window = tw = ctk.CTkToplevel(self.widget)
            # Geen window decoraties
            tw.wm_overrideredirect(True)

            # Transparantie instellen indien ondersteund
            try:
                # Dit werkt alleen op Windows en sommige Unix systemen
                tw.wm_attributes("-alpha", self.alpha)
            except tk.TclError:
                pass  # Niet ondersteund op dit platform

            # Creëer frame met gewenste afronding en vulling
            self.tooltip_frame = ctk.CTkFrame(
                self.tooltip_window,
                fg_color=self.bg_color,
                corner_radius=self.corner_radius,
                border_width=0,
            )
            self.tooltip_frame.pack(fill="both", expand=True)

            # Tekst label met wraplength
            self.tooltip_label = ctk.CTkLabel(
                self.tooltip_frame,
                text=self.message,
                text_color=self.text_color,
                font=self.font,
                wraplength=self.wraplength,
                padx=8,
                pady=4,
            )
            self.tooltip_label.pack(padx=4, pady=4)

            # Wacht op correcte afmetingen
            self.tooltip_window.update_idletasks()

            # Bepaal positie
            self._set_position()

    def _set_position(self):
        """Berekent de optimale positie voor de tooltip."""
        if not self.tooltip_window:
            return

        # Krijg huidige muispositie
        cursor_x = self.widget.winfo_pointerx()
        cursor_y = self.widget.winfo_pointery()

        # Tooltip dimensies
        width = self.tooltip_window.winfo_width()
        height = self.tooltip_window.winfo_height()

        # Schermafmetingen
        screen_width = self.widget.winfo_screenwidth()
        screen_height = self.widget.winfo_screenheight()

        # Standaard positie rechts en onder muis
        x = cursor_x + self.x_offset
        y = cursor_y + self.y_offset

        # Controleer of tooltip buiten het scherm zou vallen
        if x + width > screen_width:
            x = cursor_x - width - self.x_offset  # Links van muis plaatsen

        if y + height > screen_height:
            y = cursor_y - height - self.y_offset  # Boven muis plaatsen

        # Stel positie in
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

    def _update_position(self, event):
        """
        Update de positie van de tooltip bij muisbeweging.

        Args:
            event: Tkinter event
        """
        if not self.tooltip_window:
            return

        # Bepaal absolute schermcoördinaten
        cursor_x = self.widget.winfo_pointerx()
        cursor_y = self.widget.winfo_pointery()

        # Tooltip dimensies
        width = self.tooltip_window.winfo_width()
        height = self.tooltip_window.winfo_height()

        # Schermafmetingen
        screen_width = self.widget.winfo_screenwidth()
        screen_height = self.widget.winfo_screenheight()

        # Standaard positie rechts en onder muis
        x = cursor_x + self.x_offset
        y = cursor_y + self.y_offset

        # Controleer of tooltip buiten het scherm zou vallen
        if x + width > screen_width:
            x = cursor_x - width - self.x_offset  # Links van muis plaatsen

        if y + height > screen_height:
            y = cursor_y - height - self.y_offset  # Boven muis plaatsen

        # Stel positie in
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

    def _hide_tooltip(self):
        """Verbergt de tooltip."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def update_text(self, new_message):
        """
        Update de tekst van de tooltip.

        Args:
            new_message (str): Nieuwe tekstbericht
        """
        self.message = new_message

        # Update label als tooltip zichtbaar is
        if self.tooltip_window and hasattr(self, "tooltip_label"):
            self.tooltip_label.configure(text=new_message)
