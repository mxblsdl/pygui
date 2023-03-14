from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
)

from clockify_api_client.client import ClockifyAPIClient
import sys
from pathlib import Path
from datetime import datetime, timedelta
import polars as pl


def subtotal(out, table, idx):
    day_total = out.filter(pl.col("date") == out["date"][idx])
    table.add_row("", "Subtotal", str(round(day_total["duration"].sum(), 2)))
    table.add_section()


class TableWidget(QTableWidget):
    """create a table window"""

    def __init__(self) -> None:
        super().__init__()

    # Have a function within the class that sets the data
    def setData(self, data) -> None:
        # Set row and col lengths
        r = data.select(pl.count()).item()
        c = len(data.columns)
        self.setRowCount(r)
        self.setColumnCount(c)

        self.setHorizontalHeaderLabels(data.columns)
        for idx, ind in enumerate(data.iter_rows(named=True)):
            self.setItem(idx, 0, QTableWidgetItem(ind["name"]))
            self.setItem(idx, 1, QTableWidgetItem(str(ind["date"])))
            self.setItem(idx, 2, QTableWidgetItem(str(ind["duration"])))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = "Testering"
        self.left = 10
        self.top = 10
        self.width = 400
        self.height = 140
        self.initUi()

    def initUi(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Create widgets
        self.textbox = QLineEdit("Enter API Key")
        self.button1 = QPushButton("Submit")

        self.checkAPI()

        # Create layout and widgets
        l = QVBoxLayout()
        self.w1 = TableWidget()

        label = QLabel(self.label)
        # TODO implement the prompt to save api key window if not found and submitted
        self.button1.clicked.connect(lambda x: self.call_api(self.w1))

        l.addWidget(label)
        l.addWidget(self.textbox)
        l.addWidget(self.button1)

        w = QWidget()
        w.setLayout(l)
        self.setCentralWidget(w)

    def checkAPI(self):
        if (Path.home() / ".clock.config").exists():
            self.textbox.setDisabled(True)
            self.label = "API key found"
        else:
            self.label = "API key not found"
            self.button1.setDisabled(True)

    def call_api(self, window):
        api_text = (Path.home() / ".clock.config").read_text()
        api_key = api_text.split("=")[1]
        client = ClockifyAPIClient().build(api_key, "api.clockify.me/v1")
        workspace_id, user_id = self.get_ids(client)
        projs = client.projects.get_projects(workspace_id)

        out = pl.DataFrame()
        dt = datetime.today()
        start = (
            dt - timedelta(days=dt.weekday()) - timedelta(weeks=1)
        )  # Make input to GUI
        start = start.replace(hour=0)  # set to beginning of day
        end = start + timedelta(days=6)

        for proj in projs:
            # Make API call from start date
            entries = client.time_entries.get_time_entries(
                workspace_id,
                user_id,
                params={
                    "project": proj["id"],
                    "page-size": 500,
                    "start": start.isoformat() + "Z",
                    "end": end.isoformat() + "Z",
                },
            )
            if not entries:
                continue

            # Parse results by project
            e = [e["timeInterval"] for e in entries]
            df = pl.DataFrame(e)
            df = self.create_cols(df, proj)

            # short circuit the for loop with agg data
            df = df.groupby(["name", "date"]).agg(pl.col("duration").sum().round(2))
            out = pl.concat([out, df])
            continue

        out = out.sort("date")
        out = out.with_columns(pl.col("duration").round(2))

        # TODO window to better spot
        # TODO build out set data function
        # window.setData(out)
        window.setData(out)
        window.show()

    def get_ids(self, client):
        workspaces = client.workspaces.get_workspaces()  # Returns list of workspaces.
        workspace_id = workspaces[0]["id"]
        user_id = client.users.get_current_user()["id"]
        return workspace_id, user_id

    def create_cols(self, df: pl.DataFrame, proj: str = ""):
        df = (
            df.with_columns(
                pl.col("start", "end")
                .str.strptime(pl.Datetime, fmt="%Y-%m-%dT%H:%M:%SZ")
                .dt.replace_time_zone("UTC")
                .dt.convert_time_zone("America/Los_Angeles")
            )
            .with_columns(
                (pl.col("end") - pl.col("start")).dt.seconds().alias("duration")
            )
            .with_columns((pl.col("duration") / 3600))
            .with_columns(pl.col("start").dt.truncate("1d").alias("date").cast(pl.Date))
            .with_columns(pl.lit(proj["name"]).alias("name"))
        )
        return df


app = QApplication(sys.argv)
w = MainWindow()
w.show()
app.exec()
