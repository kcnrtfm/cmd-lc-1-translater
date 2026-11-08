"""Terminal UI for the CMD LC-1 Bass Liner."""

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Label, RichLog, Select, Static

from app.bass_controller import BassController
from app.bassline import BassLineGenerator
from app.midi import DualOutputMidiRouter, MidiInputListener
from app.transform import RelativeEncoderToAbsolute


class MonitorLog(RichLog, can_focus=False):
    """Read-only MIDI monitor excluded from keyboard focus."""


class MidiEvent(Message):
    def __init__(self, direction: str, detail: str, channel: int | None = None) -> None:
        super().__init__()
        self.direction = direction
        self.detail = detail
        self.channel = channel


class BassLinerApp(App):
    TITLE = "Bass Liner"

    BINDINGS = [
        ("a", "refresh_ports", "Actualizar"),
        ("c", "connect_ports", "Conectar"),
        ("d", "disconnect_ports", "Desconectar"),
        ("e", "toggle_encoder_absolute", "Encoders -> absoluto"),
        ("g", "toggle_generator", "Generador"),
    ]

    CSS = """
    Screen { layout: vertical; }
    #controls { height: 16; padding: 1 2; border: ascii $accent; }
    .port-row { height: 2; align: left middle; }
    .port-label { width: 19; }
    Select { width: 1fr; border: ascii $accent; }
    Button { height: 3; min-width: 16; margin-right: 1; border: ascii $accent; background: $panel; color: white; }
    Button:disabled { opacity: 1; background: $panel; color: white; border: ascii $accent; }
    #encoder-absolute { min-width: 29; margin-left: 2; }
    #bass-generator { min-width: 22; }
    Button:focus { border: ascii #888888; background: #666666; color: white; }
    Select:focus { border: ascii #888888; }
    Select:focus > SelectCurrent { background: #555555; color: white; }
    SelectOverlay:focus { border: ascii #888888; }
    SelectOverlay > .option-list--option-highlighted { background: #666666; color: white; }
    SelectOverlay > .option-list--option-hover { background: #555555; color: white; }
    #actions { height: 3; align: left middle; }
    #status { height: 1; padding-left: 1; }
    #monitors { height: 1fr; }
    .monitor { width: 1fr; border: ascii $secondary; }
    .monitor-title { height: 1; padding-left: 1; background: $panel; }
    RichLog { height: 1fr; }
    """

    def __init__(self) -> None:
        super().__init__()

        self.encoder_transform = RelativeEncoderToAbsolute()

        self.router = DualOutputMidiRouter(
            self._input_message,
            self._translated_output_message,
            self._bass_output_message,
            self.encoder_transform.process,
        )

        self.clock_input = MidiInputListener(self._clock_message)
        self.bass_generator = BassLineGenerator(self.router.send_bass)
        self.bass_controller = BassController(
            self.bass_generator,
            self.router.send_bass,
            self._controller_state_changed,
        )
        self.router.input_handler = self.bass_controller.process

        self.encoder_absolute = False

    def compose(self) -> ComposeResult:
        with Vertical(id="controls"):
            with Horizontal(classes="port-row"):
                yield Label("Entrada MIDI", classes="port-label")
                yield Select([], id="input-port", prompt="Seleccionar entrada", compact=True)

            with Horizontal(classes="port-row"):
                yield Label("Salida translated", classes="port-label")
                yield Select([], id="translated-port", prompt="CMD LC-1 translated", compact=True)

            with Horizontal(classes="port-row"):
                yield Label("Salida BassLiner", classes="port-label")
                yield Select([], id="bass-port", prompt="BassLiner", compact=True)

            with Horizontal(classes="port-row"):
                yield Label("Clock MIDI", classes="port-label")
                yield Select([], id="clock-port", prompt="BassLiner Clock", compact=True)

            with Horizontal(id="actions"):
                yield Button("(A)ctualizar", id="refresh")
                yield Button("(C)onectar", id="connect")
                yield Button("(D)esconectar", id="disconnect", disabled=True)
                yield Button("[ ] (E)ncoders -> absoluto", id="encoder-absolute")
                yield Button("[ ] (G)enerador", id="bass-generator")

            yield Label("Desconectado", id="status")

        with Horizontal(id="monitors"):
            with Vertical(classes="monitor"):
                yield Static("ENTRADA MIDI - canal: --", id="input-title", classes="monitor-title")
                yield MonitorLog(id="input-log", max_lines=500, wrap=False)

            with Vertical(classes="monitor"):
                yield Static("SALIDA TRANSLATED - canal: --", id="translated-title", classes="monitor-title")
                yield MonitorLog(id="translated-log", max_lines=500, wrap=False)

            with Vertical(classes="monitor"):
                yield Static("SALIDA BASS LINER - canal: --", id="bass-title", classes="monitor-title")
                yield MonitorLog(id="bass-log", max_lines=500, wrap=False)

    def on_mount(self) -> None:
        self.refresh_ports()

    def refresh_ports(self) -> None:
        for widget_id, names in (
            ("input-port", self.router.input_ports()),
            ("translated-port", self.router.output_ports()),
            ("bass-port", self.router.output_ports()),
            ("clock-port", self.router.input_ports()),
        ):
            selector = self.query_one(f"#{widget_id}", Select)
            previous = selector.value
            selector.set_options([(name, name) for name in names])

            if isinstance(previous, str) and previous in names:
                selector.value = previous

    def _set_connected(self, connected: bool) -> None:
        self.query_one("#connect", Button).disabled = connected
        self.query_one("#disconnect", Button).disabled = not connected

        for widget_id in ("input-port", "translated-port", "bass-port", "clock-port"):
            self.query_one(f"#{widget_id}", Select).disabled = connected

        if not connected:
            self.query_one("#status", Label).update("Desconectado")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh":
            self.action_refresh_ports()
        elif event.button.id == "connect":
            self.action_connect_ports()
        elif event.button.id == "disconnect":
            self.action_disconnect_ports()
        elif event.button.id == "encoder-absolute":
            self.action_toggle_encoder_absolute()
        elif event.button.id == "bass-generator":
            self.action_toggle_generator()

    def action_refresh_ports(self) -> None:
        try:
            self.refresh_ports()
        except Exception as exc:
            self.query_one("#status", Label).update(f"Error: {exc}")

    def action_connect_ports(self) -> None:
        if self.router.connected:
            return

        input_name = self.query_one("#input-port", Select).value
        translated_name = self.query_one("#translated-port", Select).value
        bass_name = self.query_one("#bass-port", Select).value
        clock_name = self.query_one("#clock-port", Select).value

        if not all(isinstance(name, str) for name in (input_name, translated_name, bass_name, clock_name)):
            self.query_one("#status", Label).update("Seleccioná entrada, dos salidas y clock")
            return

        try:
            self.router.connect(input_name, translated_name, bass_name)
            self.clock_input.connect(clock_name)
        except Exception as exc:
            self.clock_input.disconnect()
            self.router.disconnect()
            self.query_one("#status", Label).update(f"Error: {exc}")
            return

        self._set_connected(True)
        self.query_one("#status", Label).update("Conectado")

    def action_disconnect_ports(self) -> None:
        self.clock_input.disconnect()
        self.router.disconnect()
        self._set_connected(False)

    @staticmethod
    def _format_message(message) -> str:
        return str(message)

    def _input_message(self, message) -> None:
        channel = message.channel + 1 if hasattr(message, "channel") else None
        self.post_message(MidiEvent("input", self._format_message(message), channel))

    def _translated_output_message(self, message) -> None:
        channel = message.channel + 1 if hasattr(message, "channel") else None
        self.post_message(MidiEvent("translated", self._format_message(message), channel))

    def _bass_output_message(self, message) -> None:
        channel = message.channel + 1 if hasattr(message, "channel") else None
        self.post_message(MidiEvent("bass", self._format_message(message), channel))

    def _clock_message(self, message) -> None:
        self.bass_generator.process_transport(message)

    def _controller_state_changed(self, state: dict[str, object]) -> None:
        generator = "ON" if state["generator_enabled"] else "OFF"
        root = state["root"]
        root_text = "--" if root is None else str(root)
        detail = f"Generador {generator} | octava {state['octave']} | root MIDI {root_text}"
        self.post_message(MidiEvent("state", detail))

    def on_midi_event(self, event: MidiEvent) -> None:
        if event.direction == "state":
            self.query_one("#status", Label).update(event.detail)
            marker = "X" if self.bass_generator.enabled else " "
            self.query_one("#bass-generator", Button).label = f"[{marker}] (G)enerador"
            return

        title_map = {
            "input": "ENTRADA MIDI",
            "translated": "SALIDA TRANSLATED",
            "bass": "SALIDA BASS LINER",
        }

        if event.channel is not None:
            self.query_one(f"#{event.direction}-title", Static).update(
                f"{title_map[event.direction]} - canal: {event.channel}"
            )

        self.query_one(f"#{event.direction}-log", RichLog).write(event.detail)

    def action_toggle_encoder_absolute(self) -> None:
        self.encoder_absolute = not self.encoder_absolute
        self.encoder_transform.enabled = self.encoder_absolute
        marker = "X" if self.encoder_absolute else " "
        self.query_one("#encoder-absolute", Button).label = f"[{marker}] (E)ncoders -> absoluto"

    def action_toggle_generator(self) -> None:
        if self.bass_generator.enabled:
            self.bass_generator.disarm()
        else:
            self.bass_generator.arm()

        self._controller_state_changed(self.bass_controller.state)

    def on_unmount(self) -> None:
        self.bass_generator.disarm()
        self.clock_input.disconnect()
        self.router.disconnect()
