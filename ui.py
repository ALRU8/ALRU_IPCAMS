import asyncio
import sys
import webbrowser
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QSpinBox, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QGroupBox, QRadioButton,
    QTextEdit
)
from camera_detect import detect_camera
from camera_model import Camera
from network_utils import get_local_networks
from onvif_utils import get_rtsp_uri
from rtsp_utils import build_rtsp_url
from settings import COMMON_CAMERA_PORTS, COMMON_RTSP_PATHS
from subnet_scan import scan_subnet
from video_player import VideoWindow
from ws_discovery import discover_onvif_cameras


class ScanWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, cidr: str, scan_mode: str):
        super().__init__()
        self.cidr = cidr
        self.scan_mode = scan_mode

    def run(self):
        try:
            cameras = []
            if self.scan_mode == "onvif":
                self.progress.emit("Поиск ONVIF камер...")
                cameras.extend(discover_onvif_cameras())
                merged = merge_cameras(cameras)
            elif self.scan_mode == "ipc":
                self.progress.emit("Поиск IP камер (IPC)...")
                from camera_service import CameraService
                service = CameraService()
                merged = asyncio.run(service.discover_ipc(self.cidr))
            elif self.scan_mode == "nvr":
                self.progress.emit("Поиск NVR/XVR/HVR/DVR...")
                from camera_service import CameraService
                service = CameraService()
                merged = asyncio.run(service.discover_nvr(self.cidr))
            elif self.scan_mode == "other":
                self.progress.emit("Поиск других устройств...")
                from camera_service import CameraService
                service = CameraService()
                merged = asyncio.run(service.discover_other(self.cidr))
            else:
                self.progress.emit("Проверяю типичные порты камер...")
                cameras.extend(asyncio.run(scan_subnet(self.cidr, COMMON_CAMERA_PORTS)))
                merged = merge_cameras(cameras)

            for camera in merged:
                self.progress.emit(f"Определяю тип устройства: {camera.ip}")
                detect_camera(camera)
            self.finished.emit(merged)
        except Exception as exc:
            self.failed.emit(str(exc))


class LoginDialog(QDialog):
    def __init__(self, camera: Camera, parent=None):
        super().__init__(parent)
        self.camera = camera
        self.setWindowTitle(f"ONVIF доступ к {camera.ip}")
        self.info_label = QLabel(self.camera_info())
        self.info_label.setWordWrap(True)
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(camera.port or 80)
        self.username_input = QLineEdit("admin")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.show_password = QCheckBox("Показать пароль")
        self.show_password.toggled.connect(self.toggle_password)
        self.help_button = QPushButton("Справочник заводских данных")
        self.help_button.clicked.connect(self.open_default_passwords_page)
        form = QFormLayout()
        form.addRow("Камера", self.info_label)
        form.addRow("ONVIF порт", self.port_input)
        form.addRow("Логин", self.username_input)
        form.addRow("Пароль", self.password_input)
        form.addRow("", self.show_password)
        buttons = QDialogButtonBox()
        buttons.addButton("Проверить", QDialogButtonBox.AcceptRole)
        buttons.addButton("Отмена", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.help_button)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def camera_info(self) -> str:
        parts = [self.camera.ip]
        if self.camera.camera_type:
            parts.append(self.camera.camera_type)
        if self.camera.manufacturer:
            parts.append(self.camera.manufacturer)
        if self.camera.model:
            parts.append(self.camera.model)
        return " | ".join(parts)

    def toggle_password(self, checked: bool):
        self.password_input.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    def open_default_passwords_page(self):
        webbrowser.open("https://www.ispyconnect.com/docs/ispy/default-camera-passwords")

    def values(self) -> tuple[int, str, str]:
        return self.port_input.value(), self.username_input.text().strip(), self.password_input.text()


class ManualRtspDialog(QDialog):
    def __init__(self, ip: str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RTSP вручную")
        self.ip = ip
        self.url_input = QLineEdit()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.path_input = QComboBox()
        self.path_input.setEditable(True)
        self.path_input.addItems(COMMON_RTSP_PATHS)
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(554)
        if ip:
            self.url_input.setText(build_rtsp_url(ip, COMMON_RTSP_PATHS[0]))
        self.build_button = QPushButton("Собрать URL")
        self.build_button.clicked.connect(self.build_url)
        form = QFormLayout()
        form.addRow("Готовый RTSP URL", self.url_input)
        form.addRow("IP", QLabel(ip or "Не задан"))
        form.addRow("Порт", self.port_input)
        form.addRow("Путь", self.path_input)
        form.addRow("Логин", self.username_input)
        form.addRow("Пароль", self.password_input)
        form.addRow("", self.build_button)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def build_url(self):
        if not self.ip:
            return
        url = build_rtsp_url(self.ip, self.path_input.currentText(), self.username_input.text().strip(), self.password_input.text(), self.port_input.value())
        self.url_input.setText(url)

    def accept(self):
        if not self.url_input.text().strip().lower().startswith("rtsp://"):
            QMessageBox.warning(self, "Ошибка", "RTSP URL должен начинаться с rtsp://")
            return
        super().accept()

    def value(self) -> str:
        return self.url_input.text().strip()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IP Camera Viewer")
        self.resize(1250, 700)
        self.cameras = []
        self.video_windows = []
        self.scan_thread = None
        self.scan_worker = None
        self.network_combo = QComboBox()
        self.cidr_input = QLineEdit()
        self.cidr_input.setPlaceholderText("Например: 192.168.1.0/24")
        self.refresh_button = QPushButton("Обновить сети")
        self.scan_button = QPushButton("Сканировать")
        self.manual_button = QPushButton("RTSP вручную")

        self.scan_mode_group = QGroupBox("Метод поиска")
        self.mode_ipc = QRadioButton("IPC")
        self.mode_nvr = QRadioButton("NVR/XVR/HVR/DVR")
        self.mode_onvif = QRadioButton("ONVIF")
        self.mode_other = QRadioButton("OTHER")
        self.mode_onvif.setChecked(True)
        mode_layout = QVBoxLayout()
        mode_layout.addWidget(self.mode_ipc)
        mode_layout.addWidget(self.mode_nvr)
        mode_layout.addWidget(self.mode_onvif)
        mode_layout.addWidget(self.mode_other)
        self.scan_mode_group.setLayout(mode_layout)

        self.status_label = QLabel("Готово")
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["IP", "Тип", "Производитель", "Имя", "Источник", "Статус", "Данные", "Действия"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(100)
        self.log_console.setPlaceholderText("Логи сканирования...")
        self.refresh_button.clicked.connect(self.refresh_networks)
        self.scan_button.clicked.connect(self.start_scan)
        self.manual_button.clicked.connect(lambda: self.open_manual_rtsp(None))
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Сеть"))
        top_row.addWidget(self.network_combo)
        top_row.addWidget(self.refresh_button)
        second_row = QHBoxLayout()
        second_row.addWidget(QLabel("CIDR вручную"))
        second_row.addWidget(self.cidr_input)
        second_row.addWidget(self.scan_button)
        second_row.addWidget(self.manual_button)
        layout = QVBoxLayout()
        layout.addLayout(top_row)
        layout.addLayout(second_row)
        layout.addWidget(self.scan_mode_group)
        layout.addWidget(self.table)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_console)
        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)
        self.refresh_networks()

    def refresh_networks(self):
        self.network_combo.clear()
        networks = get_local_networks()
        for item in networks:
            title = f"{item['interface']} — {item['cidr']} ({item['address']})"
            self.network_combo.addItem(title, item["cidr"])
        if not networks:
            self.network_combo.addItem("Сети не найдены", "")
        self.status_label.setText("Список сетей обновлён")

    def selected_cidr(self) -> str:
        manual = self.cidr_input.text().strip()
        if manual:
            return manual
        return self.network_combo.currentData() or ""

    def selected_scan_mode(self) -> str:
        if self.mode_ipc.isChecked():
            return "ipc"
        if self.mode_nvr.isChecked():
            return "nvr"
        if self.mode_onvif.isChecked():
            return "onvif"
        if self.mode_other.isChecked():
            return "other"
        return "fallback"

    def start_scan(self):
        cidr = self.selected_cidr()
        if not cidr:
            QMessageBox.warning(self, "Ошибка", "Выбери сеть или введи CIDR вручную")
            return
        mode = self.selected_scan_mode()
        
        self.scan_button.setEnabled(False)
        self.table.setRowCount(0)
        self.status_label.setText("Сканирование запущено")
        self.scan_thread = QThread(self)
        self.scan_worker = ScanWorker(cidr, mode)
        self.scan_worker.moveToThread(self.scan_thread)
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.progress.connect(self.status_label.setText)
        self.scan_worker.progress.connect(self.log_console.append)
        self.scan_worker.finished.connect(self.scan_finished)
        self.scan_worker.failed.connect(self.scan_failed)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.failed.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(lambda: self.scan_button.setEnabled(True))
        self.scan_thread.start()

    def scan_finished(self, cameras):
        self.cameras = cameras
        self.render_cameras()
        self.status_label.setText(f"Найдено устройств: {len(cameras)}")

    def scan_failed(self, message: str):
        self.status_label.setText("Ошибка сканирования")
        QMessageBox.critical(self, "Ошибка", message)

    def render_cameras(self):
        self.table.setRowCount(0)
        for index, camera in enumerate(self.cameras):
            self.table.insertRow(index)
            self.table.setItem(index, 0, QTableWidgetItem(camera.ip))
            self.table.setItem(index, 1, QTableWidgetItem(camera.camera_type or "Не определено"))
            self.table.setItem(index, 2, QTableWidgetItem(camera.manufacturer or "Неизвестно"))
            self.table.setItem(index, 3, QTableWidgetItem(camera.display_name))
            self.table.setItem(index, 4, QTableWidgetItem(camera.source))
            self.table.setItem(index, 5, QTableWidgetItem(camera.status))
            self.table.setItem(index, 6, QTableWidgetItem(self.camera_details(camera)))
            open_button = QPushButton("Открыть")
            rtsp_button = QPushButton("RTSP")
            open_button.clicked.connect(lambda checked=False, row=index: self.open_camera(row))
            rtsp_button.clicked.connect(lambda checked=False, row=index: self.open_manual_rtsp(self.cameras[row]))
            actions = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.addWidget(open_button)
            actions_layout.addWidget(rtsp_button)
            actions.setLayout(actions_layout)
            self.table.setCellWidget(index, 7, actions)

    def camera_details(self, camera: Camera) -> str:
        details = []
        if camera.model:
            details.append(f"Модель: {camera.model}")
        if camera.open_ports:
            details.append(f"Порты: {', '.join(str(port) for port in camera.open_ports)}")
        if camera.vendor_confidence:
            details.append(f"Производитель: {camera.vendor_confidence}%")
        if camera.type_confidence:
            details.append(f"Тип: {camera.type_confidence}%")
        if camera.onvif_url:
            details.append(camera.onvif_url)
        return "\n".join(details)

    def open_camera(self, row: int):
        camera = self.cameras[row]
        if camera.rtsp_url:
            self.open_video(camera.rtsp_url)
            return
        if camera.onvif_url:
            dialog = LoginDialog(camera, self)
            if dialog.exec() != QDialog.Accepted:
                return
            port, username, password = dialog.values()
            try:
                self.status_label.setText("Получаю RTSP через ONVIF...")
                camera.rtsp_url = get_rtsp_uri(camera.ip, port, username, password)
                self.render_cameras()
                self.open_video(camera.rtsp_url)
            except Exception as exc:
                QMessageBox.critical(self, "ONVIF ошибка", str(exc))
            return
        self.open_manual_rtsp(camera)

    def open_manual_rtsp(self, camera: Camera | None):
        dialog = ManualRtspDialog(camera.ip if camera else None, self)
        if dialog.exec() != QDialog.Accepted:
            return
        rtsp_url = dialog.value()
        if camera:
            camera.rtsp_url = rtsp_url
            self.render_cameras()
        self.open_video(rtsp_url)

    def open_video(self, rtsp_url: str):
        window = VideoWindow(rtsp_url)
        self.video_windows.append(window)
        window.show()


def merge_cameras(cameras: list[Camera]) -> list[Camera]:
    merged = {}
    for camera in cameras:
        if camera.ip in merged:
            merged[camera.ip].merge(camera)
        else:
            merged[camera.ip] = camera
    return sorted(merged.values(), key=lambda item: item.ip)


def run_app():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())