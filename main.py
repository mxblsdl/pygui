from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
)

from clockify_api_client.client import ClockifyAPIClient
import qdarkstyle
import sys
from pathlib import Path


def check_api(API_URL="api.clockify.me/v1"):
    config_file = Path.home() / ".clock.config"
    if not config_file.exists():
        print("API Key has not been configured.")
        api = input("Enter your API key")
        print(f"Using API version: {API_URL}")
        try:
            client = ClockifyAPIClient().build(api, API_URL)
        except:
            print("Problem with API key\nMake sure your key was entered correctly")
        print("API key entered successfully!")
        res = input("Would you like to save the API for future use? (y/n)")

        while res.lower() not in ["y", "n"]:
            res = input("Please enter either 'y' or 'n'")

        if res.lower() == "y":
            config_file.touch()
            config_file.write_text(f"""API_KEY={api}""")
            return client

        return client
    else:
        print("Using stored API Credentials")
        api_text = config_file.read_text()
        api_text = api_text.split("=")
        try:
            client = ClockifyAPIClient().build(api_text[1], API_URL)
        except:
            print("Problem with API key\nMake sure your key was entered correctly")
        return client


class TableWidget(QTableWidget):
    """create a table window"""

    def __init__(self) -> None:
        super().__init__()
        self.setRowCount(3)
        self.setColumnCount(3)

        x = self.verticalHeader().size().width()
        for i in range(self.columnCount()):
            x += self.columnWidth(i)

        y = self.horizontalHeader().size().height()
        for i in range(self.rowCount()):
            y += self.rowHeight(i)

        self.setFixedSize(x, y)

        # Example set header names
        self.setHorizontalHeaderLabels(["apple", "pear", "banana"])

        self.setItem(0, 0, QTableWidgetItem("Cell (1,1)"))
        self.setItem(0, 1, QTableWidgetItem("Cell (1,2)"))

    # Have a function within the class that sets the data
    def setData(self, data) -> None:
        pass


class AnotherWindow(QWidget):
    """
    This "window" is a QWidget. If it has no parent, it
    will appear as a free-floating window as we want.
    """

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.v = 1
        self.label = QLabel(str(self.v))
        layout.addWidget(self.label)
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.w1 = TableWidget()
        self.w2 = AnotherWindow()

        l = QVBoxLayout()
        button1 = QPushButton("Push for Window")
        button1.clicked.connect(lambda x: self.toggle_window(self.w1))
        l.addWidget(button1)

        button2 = QPushButton("Increment")
        button2.clicked.connect(self.incrementValue)
        l.addWidget(button2)

        w = QWidget()
        w.setLayout(l)
        self.setCentralWidget(w)

    def incrementValue(self):
        self.w1.v += 1
        self.w1.label.setText(str(self.w1.v))

    def toggle_window(self, window):
        if window.isVisible():
            window.hide()
        else:
            window.show()


app = QApplication(sys.argv)
app.setStyleSheet(qdarkstyle.load_stylesheet())

w = MainWindow()
w.show()
app.exec()
