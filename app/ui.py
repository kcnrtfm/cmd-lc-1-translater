"""Textual interface for MIDI port selection and message monitoring."""

from textual.app import App, ComposeResult
from textual.message import Message
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Checkbox, Label, RichLog, Select, Static

from app.midi import MidiRouter


class MonitorLog(RichLog, can_focus=False):
    """Read-only MIDI monitor excluded from keyboard focus."""


class MidiEvent(Message):
    def __init__(self, direction: str, detail: str) -> None:
        super().__init__()
        self.direction = direction
        self.detail = detail


class MidiApp(App):
    TITLE = "CMD LC-1 Translator"
    BINDINGS = [("e", "toggle_encoder_absolute", "Encoders -> absoluto")]

    CSS = """
    Screen { layout: vertical; }
    #controls { height: 12; padding: 1 2; border: ascii $accent; }
    .port-row { height: 2; align: left middle; }
    .port-label { width: 15; }
    Select { width: 1fr; border: ascii $accent; }
    Button { height: 3; min-width: 16; margin-right: 1; border: ascii $accent; }
    #encoder-absolute { height: 3; margin-left: 2; padding-top: 1; }
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
        self.router = MidiRouter(self._input_message, self._output_message)

    def compose(self) -> ComposeResult:
        with Vertical(id="controls"):
            with Horizontal(classes="port-row"):
                yield Label("Entrada MIDI", classes="port-label")
                yield Select([], id="input-port", prompt="Seleccionar entrada", compact=True)
            with Horizontal(classes="port-row"):
                yield Label("Salida MIDI", classes="port-label")
                yield Select([], id="output-port", prompt="Seleccionar salida", compact=True)
            with Horizontal(id="actions"):
                yield Button("Actualizar", id="refresh")
                yield Button("Conectar", id="connect")
                yield Button("Desconectar", id="disconnect", disabled=True)
                yield Checkbox("[E] Encoders -> absoluto", id="encoder-absolute")
            yield Label("Desconectado", id="status")
        with Horizontal(id="monitors"):
            with Vertical(classes="monitor"):
                yield Static("ENTRADA MIDI", classes="monitor-title")
                yield MonitorLog(id="input-log", max_lines=500, wrap=False)
            with Vertical(classes="monitor"):
                yield Static("SALIDA MIDI", classes="monitor-title")
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
            try:
                self.refresh_ports()
            except Exception as exc:
                self.query_one("#status", Label).update(f"Error: {exc}")
        elif event.button.id == "connect":
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
        elif event.button.id == "disconnect":
            self.router.disconnect()
            self._set_connected(False)

    @staticmethod
    def _format_message(message) -> str:
        return str(message)

    def _input_message(self, message) -> None:
        self.post_message(MidiEvent("input", self._format_message(message)))

    def _output_message(self, message) -> None:
        self.post_message(MidiEvent("output", self._format_message(message)))

    def on_midi_event(self, event: MidiEvent) -> None:
        self.query_one(f"#{event.direction}-log", RichLog).write(event.detail)

    def action_toggle_encoder_absolute(self) -> None:
        checkbox = self.query_one("#encoder-absolute", Checkbox)
        checkbox.value = not checkbox.value

    def on_unmount(self) -> None:
        self.router.disconnect()
