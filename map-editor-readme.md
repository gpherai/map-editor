# Tri-Sharira RPG Map Editor

Een grafische tool voor het maken en bewerken van kaarten voor de Tri-Sharira RPG game, gebouwd met Python en CustomTkinter.

## Features

- **Layer-based Editing**: Werk met meerdere lagen voor terrein, objecten en NPC's
- **Tile-based System**: Intuïtief plaatsen en bewerken van terreintypes
- **User-friendly Interface**: Duidelijke UI met terrain selector en layer management
- **Advanced Tools**: 
  - Undo/redo functionaliteit
  - Zoom controls
  - Grid toggle
  - Minimap
  - Auto-save functie
- **Import/Export**: 
  - JSON-formaat opslag
  - PNG/JPEG export van kaarten
  - Recent files geschiedenis

## Installatie

### Vereisten
- Python 3.9 of hoger
- CustomTkinter
- Pillow (PIL)

### Setup
1. Clone de repository:
```bash
git clone [repository-url]
cd tri_sharira_rpg/tools/map_editor
```

2. Installeer dependencies:
```bash
pip install -r requirements.txt
```

3. Start de applicatie:
```bash
python map_editor_main.py
```

## Gebruik

### Basis Controls
- **Linker muisknop**: Plaats geselecteerd terrein
- **Rechter muisknop**: Verwijder terrein
- **Middelste muisknop/wiel**: Pan over de kaart
- **Scroll wiel**: Zoom in/uit

### Keyboard Shortcuts
- **Ctrl+N**: Nieuwe kaart
- **Ctrl+O**: Open kaart
- **Ctrl+S**: Opslaan
- **Ctrl+Shift+S**: Opslaan als
- **Ctrl+Z**: Ongedaan maken
- **Ctrl+Y**: Opnieuw uitvoeren
- **Ctrl++/=**: Inzoomen
- **Ctrl+-**: Uitzoomen
- **Ctrl+0**: Reset zoom naar 100%

### Terrein Types
De editor ondersteunt verschillende terrein types:
- Basis terrein (gras, water, pad, etc.)
- Gebouwen (huizen, tempels)
- Vegetatie (bomen)
- NPC plaatsing
- Speciale elementen

### Werken met Lagen
1. **Laag Management**:
   - Voeg nieuwe lagen toe
   - Verwijder lagen
   - Verander laag volgorde
   - Toggle zichtbaarheid
   - Vergrendel/ontgrendel lagen

2. **Laag Types**:
   - Terrein laag (basis landschap)
   - Object laag (gebouwen, decoraties)
   - NPC laag (karakters en interactieve elementen)

## Project Structuur

```
map_editor/
├── assets/              # Icons en visuele assets
├── data/               # Kaart bestanden en configuraties
├── exports/            # Geëxporteerde kaarten
├── src/
│   ├── models/        # Data models en logica
│   ├── ui/           # UI componenten
│   └── utils/        # Hulpfuncties
├── tools/             # Utility scripts
├── config.json        # Editor configuratie
├── map_editor_main.py # Hoofdscript
└── requirements.txt   # Python dependencies
```

## Configuratie

De editor kan worden aangepast via `config.json`:
- Default kaart dimensies
- UI thema en kleuren
- Terrein types en kleuren
- Auto-save interval
- Default paden voor opslaan/laden

## Development

### Uitbreiden Terrein Types
Nieuwe terrein types kunnen worden toegevoegd in `config.json`:
```json
"terrain_categories": {
    "Nieuwe Categorie": {
        "CODE": "Beschrijving"
    }
}
```

### Custom Kleuren
Terrein kleuren kunnen worden aangepast:
```json
"terrain_colors": {
    "CODE": "#HEXCOLOR"
}
```

## Technische Details

- **Architecture**: MVC (Model-View-Controller) pattern
- **UI Framework**: CustomTkinter voor moderne look & feel
- **Data Storage**: JSON voor kaart data, PNG/JPEG voor exports
- **Performance**: Efficiënte rendering voor grote kaarten
- **Error Handling**: Robuuste error catching en user feedback

## Known Issues & Roadmap

### Huidige Limitaties
- Maximum kaart grootte is 500x500 tiles
- Beperkte import formaten
- Geen orthogonale weergave

### Geplande Features
- Uitgebreide selectie tools
- Lijn en gebied vulling
- Custom tile import
- Uitgebreide minimap functionaliteit
- Auto-tiling systeem

## Support

Voor bugs en feature requests, open een issue in de repository.

## License

[License informatie toevoegen]
