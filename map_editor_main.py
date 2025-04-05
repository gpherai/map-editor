# map_editor_main.py
# Verbeterde versie van de Tri-Sharira Map Editor met CustomTkinter
# Volgt MVC-architectuur, verbeterde UI en functionaliteit

import customtkinter as ctk
import tkinter as tk
import sys
import os

# --- CustomTkinter Thema Instellingen ---
# "dark" (donker), "light" (licht) of "system" (systeeminstelling)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

# --- Zorg dat het src-pad toegevoegd is aan PYTHONPATH ---
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    # Import de hoofdvenster klasse vanuit de UI module
    from ui.main_window import MapEditorApp
except ImportError as import_error:
    print(f"Fout bij importeren MapEditorApp: {import_error}")
    print(
        "Controleer of de mappenstructuur klopt en de benodigde __init__.py bestanden bestaan."
    )
    print(f"Huidige sys.path: {sys.path}")

    # Placeholder klasse als import mislukt
    class MapEditorApp:
        def __init__(self, master):
            master.title("Map Editor - Import Error")
            master.geometry("450x150")
            error_text = f"Fout: Kon MapEditorApp niet laden uit ui.main_window.\nControleer console voor details."
            label = ctk.CTkLabel(master, text=error_text, justify=tk.LEFT)
            label.pack(padx=20, pady=20, fill="both", expand=True)


def setup_directories():
    """Zorgt dat de benodigde mappen bestaan voor data, config en exports."""
    # Lijst van te controleren mappen
    required_dirs = [
        os.path.join(script_dir, "src"),
        os.path.join(script_dir, "src", "ui"),
        os.path.join(script_dir, "src", "models"),
        os.path.join(script_dir, "src", "utils"),
        os.path.join(script_dir, "data"),
        os.path.join(script_dir, "exports"),
    ]

    # Maak de mappen aan als ze nog niet bestaan
    for directory in required_dirs:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                print(f"Map aangemaakt: {directory}")
            except Exception as e:
                print(f"Kon map niet aanmaken: {directory}\nFout: {e}")


def main():
    """Initialiseert en start de Map Editor applicatie."""
    # Zorg dat benodigde mappen bestaan
    setup_directories()

    # Maak het hoofdvenster
    root = ctk.CTk()

    # Creëer en configureer de applicatie
    app = MapEditorApp(root)

    # Start de Tkinter event loop
    root.mainloop()


if __name__ == "__main__":
    main()
