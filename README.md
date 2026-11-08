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

El Bass Liner divide el CMD LC-1 en dos rutas MIDI independientes.

```text
CMD LC-1
   |
   +-- zona BassLiner reservada --> BassLiner --> Ableton
   |
   +-- resto del controlador ----> CMD LC-1 translated --> Ableton

Ableton --> BassLiner Clock --> Bass Liner
```

### Puertos loopMIDI

Crear tres puertos virtuales:

```text
CMD LC-1 translated
BassLiner
BassLiner Clock
```

En la interfaz seleccionar:

```text
Entrada MIDI       -> CMD LC-1
Salida translated  -> CMD LC-1 translated
Salida BassLiner   -> BassLiner
Clock MIDI         -> BassLiner Clock
```

La interfaz muestra tres monitores:

```text
ENTRADA MIDI
SALIDA TRANSLATED
SALIDA BASS LINER
```

### Configuración de Ableton Live

Para el passthrough normal:

```text
In: CMD LC-1 translated
Pista: ON
```

Para el instrumento BassLiner:

```text
In: BassLiner
Pista: ON
```

La salida BassLiner utiliza el canal MIDI 9.

Para sincronización:

```text
Out: BassLiner Clock
Sincro: ON
Pista: OFF
Remote: OFF
```

### Zona reservada del CMD LC-1

La zona BassLiner trabaja sobre el canal MIDI 8 de entrada.

Los dos encoders reservados no se traducen ni se reenvían:

```text
CC 16 -> reservado
CC 20 -> reservado
```

Los 13 botones quedan asignados así:

```text
note 16 -> activar/desactivar generador
note 20 -> regenerar patrón

note 32 -> C
note 36 -> D
note 40 -> E
note 44 -> F
note 48 -> G
note 52 -> A
note 56 -> B
note 60 -> C de la octava siguiente

note 64 -> bajar octava
note 68 -> subir octava
note 72 -> reservado
```

Los controles internos no salen por ninguna salida MIDI.

Los ocho botones de nota se convierten a notas musicales y salen exclusivamente por `BassLiner`, canal 9.

Todo mensaje que no pertenece a la zona reservada sigue por `CMD LC-1 translated`.

### Octava y raíz

La octava inicial es 2.

Los botones de nota definen la raíz del patrón según la octava actual.

Los controles de octava cambian la altura del instrumento y transponen la raíz del patrón sin regenerar su estructura.

### Generador de bajo

El generador crea un patrón de 16 semicorcheas restringido a una pentatónica menor relativa a la raíz seleccionada.

El patrón conserva:

- posiciones rítmicas;
- silencios;
- relaciones interválicas.

Al cambiar de nota u octava, el patrón se transpone.

El botón físico `note 20` genera una nueva estructura aleatoria conservando la raíz actual.

El botón físico `note 16` activa o desactiva la reproducción generada.

### MIDI Clock

El Bass Liner no usa BPM interno.

La reproducción depende exclusivamente de MIDI Clock enviado por Ableton.

```text
24 clocks = 1 negra
6 clocks  = 1 semicorchea
```

Mensajes utilizados:

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
E -> activar/desactivar conversión de encoders no reservados
G -> activar/desactivar generador
```

## Estructura

```text
main.py
bass_liner.py
bass_liner_backup.py
requirements.txt
run.cmd
app/
  midi.py
  ui.py
  bass_ui.py
  bassline.py
  bass_controller.py
  transform.py
```

## Lanzador Windows

`run.cmd` ejecuta el traductor principal:

```cmd
git pull origin main
py main.py
```

El Bass Liner se ejecuta con:

```cmd
py bass_liner.py
```
