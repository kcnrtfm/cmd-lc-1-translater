"""Textual interface for MIDI port selection and message monitoring."""

from textual.app import App, ComposeResult
from textual.message import Message
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, RichLog, Select, Static

from app.midi import MidiRouter
from app.bassline import BassLineGenerator
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
        ("g", "generate_bassline", "Generar bajo"),
    ]

    CSS = """
    Screen { layout: vertical; }
    #controls { height: 12; padding: 1 2; border: ascii $accent; }
    .port-row { height: 2; align: left middle; }
    .port-label { width: 15; }
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
        self.router = MidiRouter(self._input_message, self._output_message, self.encoder_transform.process)
        self.encoder_absolute = False
        self.bass_generator = BassLineGenerator(self._send_generated_message)

    def compose(self) -> ComposeResult:
        with Vertical(id="controls"):
            with Horizontal(classes="port-row"):
                yield Label("Entrada MIDI", classes="port-label")
                yield Select([], id="input-port", prompt="Seleccionar entrada", compact=True)
            with Horizontal(classes="port-row"):
                yield Label("Salida MIDI", classes="port-label")
                yield Select([], id="output-port", prompt="Seleccionar salida", compact=True)
            with Horizontal(id="actions"):
                yield Button("(A)ctualizar", id="refresh")
                yield Button("(C)onectar", id="connect")
                yield Button("(D)esconectar", id="disconnect", disabled=True)
                yield Button("[ ] (E)ncoders -> absoluto", id="encoder-absolute")
                yield Button("(G)enerar bajo", id="bass-generator")
            yield Label("Desconectado", id="status")
        with Horizontal(id="monitors"):
            with Vertical(classes="monitor"):
                yield Static("ENTRADA MIDI - canal: --", id="input-title", classes="monitor-title")
                yield MonitorLog(id="input-log", max_lines=500, wrap=False)
            with Vertical(classes="monitor"):
                yield Static("SALIDA MIDI - canal: --", id="output-title", classes="monitor-title")
                yield MonitorLog(id="output-log", max_lines=500, wrap=False)

    def on_mount(self) -> None:
        self.refresh_ports()

    def refresh_ports(self) -> None:
        for widget_id, names in (
            ("input-port", self.router.input_ports()),
            ("output-port", self.router.output_ports()),
        ):
            selector = self.query_one(f"#{widget_id}", Select)
            previous = selector.value
            selector.set_options([(name, name) for name in names])
            if isinstance(previous, str) and previous in names:
                selector.value = previous

    def _set_connected(self, connected: bool) -> None:
        self.query_one("#connect", Button).disabled = connected
        self.query_one("#disconnect", Button).disabled = not connected
        self.query_one("#input-port", Select).disabled = connected
        self.query_one("#output-port", Select).disabled = connected
        self.query_one("#status", Label).update("Conectado" if connected else "Desconectado")

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
            self.action_generate_bassline()

    def action_refresh_ports(self) -> None:
        try:
            self.refresh_ports()
        except Exception as exc:
            self.query_one("#status", Label).update(f"Error: {exc}")

    def action_connect_ports(self) -> None:
        if self.router.connected:
            return
        input_name = self.query_one("#input-port", Select).value
        output_name = self.query_one("#output-port", Select).value
        if not isinstance(input_name, str) or not isinstance(output_name, str):
            self.query_one("#status", Label).update("Seleccioná entrada y salida")
            return
        try:
            self.router.connect(input_name, output_name)
        except Exception as exc:
            self.query_one("#status", Label).update(f"Error: {exc}")
            return
        self._set_connected(True)

    def action_disconnect_ports(self) -> None:
        if not self.router.connected:
            return
        self.router.disconnect()
        self._set_connected(False)

    @staticmethod
    def _format_message(message) -> str:
        return str(message)

    def _input_message(self, message) -> None:
        if self.bass_generator.accept_seed(message):
            self.post_message(MidiEvent("generator", f"Loop generado a 120 BPM desde nota {message.note}"))
        channel = message.channel + 1 if hasattr(message, "channel") else None
        self.post_message(MidiEvent("input", self._format_message(message), channel))

    def _output_message(self, message) -> None:
        channel = message.channel + 1 if hasattr(message, "channel") else None
        self.post_message(MidiEvent("output", self._format_message(message), channel))

    def on_midi_event(self, event: MidiEvent) -> None:
        if event.direction == "generator":
            self.query_one("#status", Label).update(event.detail)
            self.query_one("#bass-generator", Button).label = "[X] (G)enerar bajo"
            return
        if event.channel is not None:
            self.query_one(f"#{event.direction}-title", Static).update(
                f"{event.direction.upper()} MIDI - canal: {event.channel}"
            )
        self.query_one(f"#{event.direction}-log", RichLog).write(event.detail)

    def action_toggle_encoder_absolute(self) -> None:
        self.encoder_absolute = not self.encoder_absolute
        self.encoder_transform.enabled = self.encoder_absolute
        marker = "X" if self.encoder_absolute else " "
        self.query_one("#encoder-absolute", Button).label = f"[{marker}] (E)ncoders -> absoluto"

    def action_generate_bassline(self) -> None:
        if not self.bass_generator.enabled:
            self.bass_generator.arm()
            self.query_one("#bass-generator", Button).label = "[X] (G)enerar bajo"
            self.query_one("#status", Label).update("Esperando nota semilla - 120 BPM")
        else:
            self.bass_generator.disarm()
            self.query_one("#bass-generator", Button).label = "[ ] (G)enerar bajo"
            self.query_one("#status", Label).update("Generador detenido")

    def _send_generated_message(self, message) -> None:
        self.router.send(message)

    def on_unmount(self) -> None:
        self.bass_generator.disarm()
        self.router.disconnect()
