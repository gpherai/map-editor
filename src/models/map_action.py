# --- MapAction Class (Voor Undo/Redo) ---
class MapAction:
    """Klasse voor het bijhouden van acties voor undo/redo-functionaliteit."""
    def __init__(self, action_type, data):
        self.type = action_type
        self.data = data # Bevat alle info nodig om actie ongedaan te maken/opnieuw te doen
        self.timestamp = time.time()