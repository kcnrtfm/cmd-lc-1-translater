# CMD LC-1 Translator / Bass Liner

Este repositorio contiene dos programas independientes que comparten la misma base MIDI:

- `main.py`: traductor para el Behringer CMD LC-1.
- `bass_liner.py`: generador de líneas de bajo sincronizado por MIDI Clock.

## Requisitos

- Windows
- Python 3.10+
- loopMIDI
- Ableton Live
- Behringer CMD LC-1

Instalación:

```cmd
py -m pip install -r requirements.txt
```

## 1. CMD LC-1 Translator

Ejecución:

```cmd
py main.py
```

Flujo:

```text
CMD LC-1 -> Translator -> CMD LC-1 translated -> Ableton
```

En loopMIDI crear un puerto virtual, por ejemplo:

```text
CMD LC-1 translated
```

En la interfaz seleccionar:

```text
Entrada MIDI -> CMD LC-1
Salida MIDI  -> CMD LC-1 translated
```

Controles:

```text
(A)ctualizar
(C)onectar
(D)esconectar
[ ] (E)ncoders -> absoluto
[ ] Co(N)tar pasos
```

### Encoders absolutos

El CMD LC-1 envía los encoders como mensajes relativos:

```text
63 -> giro en una dirección
65 -> giro en la otra dirección
```

Con `(E)ncoders -> absoluto` activo, los CC 16-23 del canal MIDI 8 se convierten a valores absolutos 0-127.

Actualmente cada paso modifica el valor en 4 unidades MIDI.

El resto de los mensajes se reenvía sin cambios.

### Contador de pasos

`Co(N)tar pasos` cuenta los mensajes de movimiento de los encoders y muestra el total directamente en el botón.

Se utilizó para medir aproximadamente 24 pasos por vuelta completa del encoder.

## 2. Bass Liner

Ejecución:

```cmd
py bass_liner.py
```

El Bass Liner reutiliza la entrada y salida MIDI del traductor y agrega un generador de patrones.

Flujo principal:

```text
CMD LC-1 -> Bass Liner -> CMD LC-1 translated -> Ableton
```

Sincronización:

```text
Ableton -> BassLiner Clock -> Bass Liner
```

### Puertos loopMIDI

Crear dos puertos virtuales:

```text
CMD LC-1 translated
BassLiner Clock
```

En la interfaz seleccionar:

```text
Entrada MIDI -> CMD LC-1
Salida MIDI  -> CMD LC-1 translated
Clock MIDI   -> BassLiner Clock
```

### Configuración de Ableton Live

Para recibir la salida musical:

```text
In: CMD LC-1 translated
Pista: ON
```

Para enviar MIDI Clock:

```text
Out: BassLiner Clock
Sincro: ON
Pista: OFF
Remote: OFF
```

### Generador de bajo

Activar:

```text
(G)enerar bajo
```

Después presionar una nota en el controlador.

La primera nota define la raíz del patrón.

El generador crea un patrón de 16 pasos restringido a una pentatónica menor, con silencios y repeticiones aleatorias.

Una vez generado:

- el patrón queda fijo;
- una nueva nota cambia la raíz;
- se conserva el mismo ritmo, silencios y relaciones interválicas;
- no se genera un patrón nuevo al cambiar de nota.

### MIDI Clock

El Bass Liner no usa BPM interno.

La reproducción depende exclusivamente de MIDI Clock enviado por Ableton.

MIDI Clock trabaja a 24 pulsos por negra.

El generador usa:

```text
6 clocks = 1 semicorchea
```

Mensajes de transporte:

```text
start    -> inicia desde el paso 1
stop     -> detiene y envía note_off
continue -> continúa
clock    -> avanza el patrón
```

## Atajos

Translator:

```text
A -> actualizar puertos
C -> conectar
D -> desconectar
E -> activar/desactivar conversión de encoders
N -> activar/desactivar contador de pasos
```

Bass Liner:

```text
A -> actualizar puertos
C -> conectar
D -> desconectar
E -> activar/desactivar conversión de encoders
G -> activar/desactivar generador de bajo
```

## Estructura

```text
main.py
bass_liner.py
requirements.txt
run.cmd
app/
  midi.py
  ui.py
  bass_ui.py
  bassline.py
  transform.py
```

## Lanzador Windows

`run.cmd` ejecuta el traductor principal:

```cmd
git pull origin main
py main.py
```

El archivo debe ejecutarse desde el repositorio.
