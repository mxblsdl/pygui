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
import qdarkstyle
import sys
from pathlib import Path
from datetime import datetime, timedelta
import polars as pl


def get_project_durations():
    # initialize client
    client = api_prompt()

    # Return the workspace id and user id
    # This assumes there is only one workspace for the user
    workspace_id, user_id = get_ids(client)
    projs = client.projects.get_projects(workspace_id)
    # Get all time entries
    # Params passed as dictionary items that filter results
    out = pl.DataFrame()

    dt = datetime.today()
    start = dt - timedelta(days=dt.weekday()) - timedelta(weeks=weeks_back)
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
        df = create_cols(df, proj)

        # short circuit the for loop with agg data
        if weekly:
            df = df.groupby(["name", "date"]).agg(pl.col("duration").sum().round(2))
            out = pl.concat([out, df])
            continue

        table = create_table(
            start, end, total_hours=round(df["duration"].sum(), ndigits=2)
        )
        for row in df.iter_rows(named=True):
            table.add_row(str(row["date"]), row["name"], str(round(row["duration"], 2)))

        print(table)

    if weekly:
        out = out.sort("date")
        out = out.with_columns(pl.col("duration").round(2))

        table = create_table(
            start, end, total_hours=round(out["duration"].sum(), ndigits=2)
        )

        for idx, ind in enumerate(out.iter_rows(named=True)):
            table.add_row(
                str(ind["date"]),
                ind["name"],
                str(ind["duration"]),
            )

            # End table creation with final break
            if out[idx + 1].is_empty():
                subtotal(out, table, idx)
                break

            # Add break between dates
            if out["date"][idx] != out["date"][idx + 1]:
                subtotal(out, table, idx)
        print(table)


def subtotal(out, table, idx):
    day_total = out.filter(pl.col("date") == out["date"][idx])
    table.add_row("", "Subtotal", str(round(day_total["duration"].sum(), 2)))
    table.add_section()


# def check_api(API_URL="api.clockify.me/v1"):
#     config_file = Path.home() / ".clock.config"
#     if not config_file.exists():
#         print("API Key has not been configured.")
#         api = input("Enter your API key")
#         print(f"Using API version: {API_URL}")
#         try:
#             client = ClockifyAPIClient().build(api, API_URL)
#         except:
#             print("Problem with API key\nMake sure your key was entered correctly")
#         print("API key entered successfully!")
#         res = input("Would you like to save the API for future use? (y/n)")

#         while res.lower() not in ["y", "n"]:
#             res = input("Please enter either 'y' or 'n'")

#         if res.lower() == "y":
#             config_file.touch()
#             config_file.write_text(f"""API_KEY={api}""")
#             return client

#         return client
#     else:
#         print("Using stored API Credentials")
#         api_text = config_file.read_text()
#         api_text = api_text.split("=")
#         try:
#             client = ClockifyAPIClient().build(api_text[1], API_URL)
#         except:
#             print("Problem with API key\nMake sure your key was entered correctly")
#         return client


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

        # # Set window size
        # x = self.verticalHeader().size().width()
        # for i in range(self.columnCount()):
        #     x += self.columnWidth(i)

        # y = self.horizontalHeader().size().height()
        # for i in range(self.rowCount()):
        #     y += self.rowHeight(i)

        # self.setFixedSize(x, y)

        # print(data)


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
# app.setStyleSheet(qdarkstyle.load_stylesheet())

w = MainWindow()
w.show()
app.exec()
