import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
)
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
import psutil
import win32gui
import win32process
import plotly.graph_objs as go
from plotly.offline import plot


# ... all imports remain the same ...


class DashboardPanel(QWidget):
    def __init__(self, activity_data, tracker_instance):
        super().__init__()
        self.tracker = tracker_instance
        self.activity_data = activity_data

        self.setStyleSheet("color: white; background-color: #222;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("📊 System Activity Summary")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        self.carousel = QStackedWidget()
        layout.addWidget(self.carousel)

        self.bar_chart = self.create_plotly_bar_chart()
        self.pie_chart = self.create_plotly_pie_chart()
        self.task_manager_view = self.create_task_manager_view()

        self.carousel.addWidget(self.bar_chart)
        self.carousel.addWidget(self.pie_chart)
        self.carousel.addWidget(self.task_manager_view)

        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀")
        self.next_btn = QPushButton("▶")
        for btn in [self.prev_btn, self.next_btn]:
            btn.setFixedSize(40, 30)
            btn.setStyleSheet(
                "background-color: white; color: black; border-radius: 6px;"
            )

        self.prev_btn.clicked.connect(self.go_previous)
        self.next_btn.clicked.connect(self.go_next)

        nav_layout.addStretch()
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)
        nav_layout.addStretch()
        layout.addLayout(nav_layout)

        # 👇 Force render the first chart to fix white screen
        self.carousel.setCurrentIndex(0)

    def go_previous(self):
        self.carousel.setCurrentIndex(
            (self.carousel.currentIndex() - 1) % self.carousel.count()
        )

    def go_next(self):
        self.carousel.setCurrentIndex(
            (self.carousel.currentIndex() + 1) % self.carousel.count()
        )

    def create_plotly_bar_chart(self):
        hourly_usage = [0] * 24
        for timestamp, _ in self.activity_data["log"]:
            hourly_usage[timestamp.hour] += 1

        fig = go.Figure(
            data=[
                go.Bar(
                    x=list(range(24)), y=hourly_usage, marker_color="rgb(90, 200, 250)"
                )
            ]
        )
        fig.update_layout(
            title="📈 Screen Time Per Hour",
            xaxis_title="Hour of Day",
            yaxis_title="Minutes",
            plot_bgcolor="#222",
            paper_bgcolor="#222",
            font=dict(color="white"),
        )

        html = plot(fig, output_type="div", include_plotlyjs="cdn")
        view = QWebEngineView()
        view.setHtml(html)
        view.setFixedHeight(300)  # 🔥 Make it taller

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(view)
        return container

    def create_plotly_pie_chart(self):
        labels = list(self.activity_data["apps"].keys())
        values = list(self.activity_data["apps"].values())

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.3,
                    textinfo="label+percent",
                    insidetextorientation="auto",
                )
            ]
        )
        fig.update_layout(
            title="📊 App Usage Share",
            paper_bgcolor="#222",
            font=dict(color="white"),
        )

        html = plot(fig, output_type="div", include_plotlyjs="cdn")
        view = QWebEngineView()
        view.setHtml(html)
        view.setFixedHeight(300)  # 🔥 Make it taller

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(view)
        return container

    def create_task_manager_view(self):
        container = QWidget()
        layout = QVBoxLayout(container)

        title = QLabel("💻 Live Task Manager (Visible Apps Only)")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.process_table = QTableWidget()
        self.process_table.setColumnCount(4)
        self.process_table.setHorizontalHeaderLabels(
            ["App", "CPU (%)", "Memory (MB)", "Uptime"]
        )
        self.process_table.setStyleSheet("color: white; background-color: #2e2e2e;")
        layout.addWidget(self.process_table)

        self.update_task_manager()
        return container

    def update_task_manager(self):
        visible_pids = set()

        def enum_handler(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    visible_pids.add(pid)
                except:
                    pass

        win32gui.EnumWindows(enum_handler, None)

        process_data = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_info", "create_time"]
        ):
            if proc.info["pid"] in visible_pids:
                try:
                    cpu = proc.info["cpu_percent"]
                    mem = proc.info["memory_info"].rss / (1024 * 1024)
                    name = proc.info["name"]
                    uptime_sec = (
                        datetime.datetime.now()
                        - datetime.datetime.fromtimestamp(proc.info["create_time"])
                    )
                    uptime = str(uptime_sec).split(".")[0]

                    process_data.append(
                        {
                            "name": name,
                            "cpu": round(cpu, 1),
                            "memory": round(mem, 1),
                            "uptime": uptime,
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        self.process_table.setRowCount(len(process_data))
        for row, proc in enumerate(process_data):
            self.process_table.setItem(row, 0, QTableWidgetItem(proc["name"]))
            self.process_table.setItem(row, 1, QTableWidgetItem(str(proc["cpu"])))
            self.process_table.setItem(row, 2, QTableWidgetItem(str(proc["memory"])))
            self.process_table.setItem(row, 3, QTableWidgetItem(proc["uptime"]))

        self.process_table.resizeColumnsToContents()
