#!/usr/bin/env python3
import sqlite3
import os
import datetime
import sys
from typing import List, Optional

try:
    from textual.app import App, ComposeResult
    from textual.widgets import (
        Header,
        Footer,
        DataTable,
        Input,
        Select,
        Label,
        Button,
        Static,
    )
    from textual.containers import Horizontal, Vertical, Container
    from textual.binding import Binding
    from textual import on, work
    from textual.reactive import reactive
except ImportError:
    print(
        "Error: 'textual' library not found. Please install it with 'pip install textual' or 'poetry add textual'."
    )
    sys.exit(1)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "log.db")


class LogViewerApp(App):
    """A TUI application to view IRC logs from an SQLite database."""

    TITLE = "LogStream TUI"
    SUB_TITLE = "IRC Log Viewer"

    CSS = """
    Screen {
        layout: horizontal;
    }

    #sidebar {
        width: 35;
        background: $panel;
        border-right: tall $background;
        padding: 1;
        height: 100%;
    }

    .filter-group {
        margin-bottom: 1;
    }

    .filter-label {
        color: $accent;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }

    #main {
        width: 1fr;
        height: 100%;
    }

    DataTable {
        height: 1fr;
    }

    #status-bar {
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
        width: 100%;
    }

    Select, Input {
        margin-bottom: 1;
    }

    Button {
        width: 100%;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "toggle_sort", "Toggle Sort"),
        Binding("f", "focus_sidebar", "Focus Filters"),
        Binding("c", "clear_filters", "Clear Filters"),
    ]

    sort_desc = reactive(True)

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        super().__init__()
        self.db_path = db_path
        self.db_conn = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="sidebar"):
            yield Label("FILTERS", classes="filter-label")

            yield Label("Server")
            yield Select([], id="select-server", prompt="All Servers")

            yield Label("Channel")
            yield Select([], id="select-channel", prompt="All Channels")

            yield Label("Event Type")
            yield Select(
                [
                    (t, t)
                    for t in ["pubmsg", "privmsg", "action", "join", "part", "quit", "nick", "kick"]
                ],
                id="select-event-type",
                prompt="All Events",
            )

            yield Label("Nickname")
            yield Input(placeholder="Search nick...", id="input-nickname")

            yield Label("Message")
            yield Input(placeholder="Search message...", id="input-message")

            yield Button("Search", variant="primary", id="btn-search")
            yield Button("Clear Filters", id="btn-clear")

        with Vertical(id="main"):
            yield DataTable(zebra_stripes=True)
            yield Label("0 results", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        try:
            self.db_conn = sqlite3.connect(self.db_path)
            self.db_conn.row_factory = sqlite3.Row
            self.populate_servers()
            self.query_logs()
        except sqlite3.Error as e:
            self.notify(f"Database error: {e}", severity="error")

    def populate_servers(self) -> None:
        cursor = self.db_conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT server FROM logs ORDER BY server ASC")
            servers = [(row["server"], row["server"]) for row in cursor.fetchall()]
            self.query_one("#select-server", Select).set_options(servers)
        except sqlite3.Error:
            pass

    @on(Select.Changed, "#select-server")
    def on_server_changed(self, event: Select.Changed) -> None:
        server = event.value
        cursor = self.db_conn.cursor()
        if not isinstance(server, str):
            self.query_one("#select-channel", Select).set_options([])
        else:
            try:
                cursor.execute(
                    "SELECT DISTINCT channel FROM logs WHERE server = ? AND channel != '' ORDER BY channel ASC",
                    (server,),
                )
                channels = [(row["channel"], row["channel"]) for row in cursor.fetchall()]
                self.query_one("#select-channel", Select).set_options(channels)
            except sqlite3.Error:
                pass
        self.query_logs()

    @on(Select.Changed, "#select-channel")
    @on(Select.Changed, "#select-event-type")
    def on_filter_changed(self) -> None:
        self.query_logs()

    @on(Input.Submitted)
    @on(Button.Pressed, "#btn-search")
    def on_search(self) -> None:
        self.query_logs()

    @on(Button.Pressed, "#btn-clear")
    def action_clear_filters(self) -> None:
        self.query_one("#select-server", Select).value = Select.BLANK
        self.query_one("#select-channel", Select).value = Select.BLANK
        self.query_one("#select-event-type", Select).value = Select.BLANK
        self.query_one("#input-nickname", Input).value = ""
        self.query_one("#input-message", Input).value = ""
        self.query_logs()

    def action_toggle_sort(self) -> None:
        self.sort_desc = not self.sort_desc
        self.query_logs()

    def action_refresh(self) -> None:
        self.query_logs()

    def action_focus_sidebar(self) -> None:
        self.query_one("#select-server").focus()

    @work(exclusive=True)
    async def query_logs(self) -> None:
        if not self.db_conn:
            return

        table = self.query_one(DataTable)
        table.loading = True

        server = self.query_one("#select-server", Select).value
        channel = self.query_one("#select-channel", Select).value
        event_type = self.query_one("#select-event-type", Select).value
        nickname = self.query_one("#input-nickname", Input).value
        message = self.query_one("#input-message", Input).value

        clauses = []
        params = []

        if isinstance(server, str):
            clauses.append("server = ?")
            params.append(server)
        if isinstance(channel, str):
            clauses.append("channel = ?")
            params.append(channel)
        if isinstance(event_type, str):
            clauses.append("event_type = ?")
            params.append(event_type)
        if nickname:
            clauses.append("nickname LIKE ?")
            params.append(f"%{nickname}%")
        if message:
            clauses.append("message LIKE ?")
            params.append(f"%{message}%")

        where_clause = " WHERE " + " AND ".join(clauses) if clauses else ""
        order = "DESC" if self.sort_desc else "ASC"

        query = f"SELECT * FROM logs{where_clause} ORDER BY timestamp {order} LIMIT 1000"

        try:
            cursor = self.db_conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            table.clear(columns=True)
            table.add_columns("Timestamp", "Channel", "Event", "User", "Message")

            for row in rows:
                dt = datetime.datetime.fromtimestamp(row["timestamp"])
                ts = dt.strftime("%Y-%m-%d %H:%M:%S")

                msg = row["message"] or ""
                ev_type = row["event_type"]

                # Color coding based on event type
                color = ""
                if ev_type == "join":
                    color = "[green]"
                elif ev_type in ("part", "quit"):
                    color = "[red]"
                elif ev_type == "kick":
                    color = "[bold red]"
                elif ev_type == "action":
                    color = "[italic purple]"
                elif ev_type == "nick":
                    color = "[blue]"

                if color:
                    ev_display = f"{color}{ev_type}[/]"
                    msg_display = f"{color}{msg}[/]"
                    nick_display = f"{color}{row['nickname']}[/]"
                else:
                    ev_display = ev_type
                    msg_display = msg
                    nick_display = row["nickname"]

                table.add_row(
                    ts,
                    row["channel"] or "-",
                    ev_display,
                    nick_display,
                    msg_display,
                    key=str(row["id"]),
                )

            self.query_one("#status-bar", Label).update(
                f"{len(rows)} results found | Sort: {'Newest' if self.sort_desc else 'Oldest'} | DB: {os.path.basename(self.db_path)}"
            )
        except sqlite3.Error as e:
            self.notify(f"Query error: {e}", severity="error")
        finally:
            table.loading = False

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection for 'context view'."""
        row_key = event.row_key.value
        if not row_key:
            return

        cursor = self.db_conn.cursor()
        cursor.execute("SELECT * FROM logs WHERE id = ?", (row_key,))
        row = cursor.fetchone()
        if not row:
            return

        # Context View: Filter by same server, channel, and day
        dt = datetime.datetime.fromtimestamp(row["timestamp"])
        start_of_day = int(datetime.datetime(dt.year, dt.month, dt.day).timestamp())
        end_of_day = start_of_day + 86400

        self.query_one("#select-server", Select).value = row["server"]
        # If channel is empty (like quit/nick), we show all channels for that server
        chan = row["channel"]
        if chan:
            self.query_one("#select-channel", Select).value = chan
        else:
            self.query_one("#select-channel", Select).value = Select.BLANK

        self.query_one("#select-event-type", Select).value = Select.BLANK
        self.query_one("#input-nickname", Input).value = ""
        self.query_one("#input-message", Input).value = ""

        self.run_context_search(row["server"], chan, start_of_day, end_of_day, row_key)

    @work(exclusive=True)
    async def run_context_search(self, server, channel, start, end, highlight_id):
        table = self.query_one(DataTable)
        table.loading = True

        clauses = ["server = ?", "timestamp BETWEEN ? AND ?"]
        params = [server, start, end]

        if channel:
            clauses.append("channel = ?")
            params.append(channel)

        query = f"SELECT * FROM logs WHERE {' AND '.join(clauses)} ORDER BY timestamp ASC"
        cursor = self.db_conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()

        table.clear(columns=True)
        table.add_columns("Timestamp", "Channel", "Event", "User", "Message")

        target_index = 0
        for i, row in enumerate(rows):
            dt = datetime.datetime.fromtimestamp(row["timestamp"])
            ts = dt.strftime("%H:%M:%S")

            msg = row["message"] or ""
            ev_type = row["event_type"]

            # Color coding based on event type
            color = ""
            if ev_type == "join":
                color = "[green]"
            elif ev_type in ("part", "quit"):
                color = "[red]"
            elif ev_type == "kick":
                color = "[bold red]"
            elif ev_type == "action":
                color = "[italic purple]"
            elif ev_type == "nick":
                color = "[blue]"

            if color:
                ev_display = f"{color}{ev_type}[/]"
                msg_display = f"{color}{msg}[/]"
                nick_display = f"{color}{row['nickname']}[/]"
            else:
                ev_display = ev_type
                msg_display = msg
                nick_display = row["nickname"]

            table.add_row(
                ts, row["channel"] or "-", ev_display, nick_display, msg_display, key=str(row["id"])
            )
            if str(row["id"]) == str(highlight_id):
                target_index = i

        chan_display = channel if channel else "all channels"
        self.query_one("#status-bar", Label).update(
            f"Context View: {len(rows)} results for {chan_display} on {datetime.datetime.fromtimestamp(start).strftime('%Y-%m-%d')}"
        )
        table.loading = False
        if rows:
            table.move_cursor(row=target_index)


if __name__ == "__main__":
    db_arg = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB_PATH
    if not os.path.exists(db_arg):
        print(f"Error: Database file '{db_arg}' not found.")
        sys.exit(1)

    app = LogViewerApp(db_arg)
    app.run()
