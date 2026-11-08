# CMD LC-1 Translator

Interfaz de terminal para seleccionar puertos MIDI, reenviar mensajes sin cambios y monitorear entrada y salida.

## Requisitos

Python 3.10+ y loopMIDI para crear un puerto de salida virtual (por ejemplo `CMD-LC1-translated`).

```bash
python -m pip install -r requirements.txt
python main.py
```

Seleccionar la entrada CMD LC-1 y la salida virtual de loopMIDI; pulsar **Conectar**. En Ableton Live, activar la entrada MIDI virtual.

## Módulos

- `app/midi.py`: puertos y passthrough MIDI.
- `app/ui.py`: selectores y monitores MIDI.
- `main.py`: arranque.

Por ahora no se modifica ningún mensaje MIDI.
