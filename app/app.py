#!/usr/bin/env python3
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer

class Croissant2App(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def action_quit(self) -> None:
        self.exit()


if __name__ == "__main__":
    app = Croissant2App()
    app.run()
