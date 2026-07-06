"""
设置页面UI - CSV导入、串口配置、发送控制、SSH设置
"""
import numpy as np
import pandas as pd
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QComboBox, QPushButton, QSpinBox, QLineEdit,
    QFileDialog, QProgressBar, QMessageBox, QTabWidget,
)
from PySide6.QtCore import Qt, Signal, Slot

from core.constants import SEND_INTERVAL_MS


class SettingsPage(QWidget):
    """设置页面"""

    waveform_loaded = Signal(np.ndarray, int)
    send_requested = Signal(np.ndarray)
    send_features_requested = Signal(np.ndarray)
    save_settings = Signal(dict)
    connect_requested = Signal(str, int)
    disconnect_requested = Signal()
    ssh_connect_requested = Signal(str, int, str, str)
    ssh_disconnect_requested = Signal()

    def __init__(self):
        super().__init__()
        from core.settings_manager import SettingsManager
        self._settings_mgr = SettingsManager()
        self._current_csv_path: str = ""
        self._waveform_data: np.ndarray = None
        self._is_connected = False
        self._ssh_connected = False
        self._setup_ui()
        self._load_saved_settings()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.tab_widget = QTabWidget()

        # ===== 页签1: 数据导入 =====
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        data_layout.setSpacing(12)

        csv_group = QGroupBox("CSV数据导入")
        csv_layout = QVBoxLayout(csv_group)

        file_layout = QHBoxLayout()
        self.csv_path_label = QLabel("未选择文件")
        self.csv_path_label.setStyleSheet(
            "color: #757575; border: 1px solid #e0e0e0; "
            "padding: 6px; border-radius: 3px; background: white;"
        )
        self.csv_path_label.setMinimumHeight(32)
        file_layout.addWidget(self.csv_path_label, 1)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setMaximumWidth(100)
        file_layout.addWidget(self.browse_btn)
        csv_layout.addLayout(file_layout)

        param_layout = QFormLayout()
        self.fs_spin = QSpinBox()
        self.fs_spin.setRange(100, 100000)
        self.fs_spin.setValue(1000)
        self.fs_spin.setSuffix(" Hz")
        self.fs_spin.setFixedWidth(160)
        param_layout.addRow("采样率:", self.fs_spin)

        self.voltage_col_spin = QSpinBox()
        self.voltage_col_spin.setRange(0, 10)
        self.voltage_col_spin.setValue(1)
        self.voltage_col_spin.setFixedWidth(100)
        param_layout.addRow("电压列序号:", self.voltage_col_spin)

        self.skip_rows_spin = QSpinBox()
        self.skip_rows_spin.setRange(0, 100)
        self.skip_rows_spin.setValue(0)
        self.skip_rows_spin.setFixedWidth(100)
        param_layout.addRow("跳过行数:", self.skip_rows_spin)

        self.max_points_spin = QSpinBox()
        self.max_points_spin.setRange(100, 50000)
        self.max_points_spin.setValue(5000)
        self.max_points_spin.setSingleStep(500)
        self.max_points_spin.setSuffix(" 点")
        self.max_points_spin.setFixedWidth(160)
        param_layout.addRow("采样点数:", self.max_points_spin)

        csv_layout.addLayout(param_layout)

        self.load_btn = QPushButton("加载并显示波形")
        self.load_btn.setMinimumHeight(40)
        self.load_btn.setStyleSheet("""
            QPushButton {
                background-color: #388E3C;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #43A047; }
        """)
        csv_layout.addWidget(self.load_btn)
        data_layout.addWidget(csv_group)
        data_layout.addStretch()

        # ===== 页签2: 串口与发送 =====
        serial_tab = QWidget()
        serial_tab_layout = QVBoxLayout(serial_tab)
        serial_tab_layout.setSpacing(12)

        serial_group = QGroupBox("串口设置")
        serial_form = QFormLayout(serial_group)

        port_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.setMinimumHeight(30)
        port_layout.addWidget(self.port_combo, 1)

        self.refresh_port_btn = QPushButton("刷新")
        self.refresh_port_btn.setMaximumWidth(80)
        port_layout.addWidget(self.refresh_port_btn)
        serial_form.addRow("串口:", port_layout)

        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baudrate_combo.setCurrentText("9600")
        self.baudrate_combo.setFixedWidth(120)
        serial_form.addRow("波特率:", self.baudrate_combo)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 100)
        self.interval_spin.setValue(SEND_INTERVAL_MS)
        self.interval_spin.setSuffix(" ms")
        self.interval_spin.setFixedWidth(120)
        serial_form.addRow("发送间隔:", self.interval_spin)

        self.apply_btn = QPushButton("应用设置")
        self.apply_btn.setMinimumHeight(35)
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #FFB74D; }
        """)
        serial_form.addRow("", self.apply_btn)

        self.connect_btn = QPushButton("连接串口")
        self.connect_btn.setMinimumHeight(40)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #1E88E5; }
        """)
        serial_form.addRow("", self.connect_btn)

        self.conn_status_label = QLabel("- 未连接")
        self.conn_status_label.setStyleSheet("color: #F44336; font-weight: bold;")
        serial_form.addRow("状态:", self.conn_status_label)

        serial_tab_layout.addWidget(serial_group)

        send_group = QGroupBox("发送控制")
        send_layout = QVBoxLayout(send_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(28)
        self.progress_bar.setFormat("就绪")
        send_layout.addWidget(self.progress_bar)

        self.send_btn = QPushButton("发送数据到DSP")
        self.send_btn.setMinimumHeight(50)
        self.send_btn.setEnabled(False)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #E64A19;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #F4511E; }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        send_layout.addWidget(self.send_btn)

        self.send_features_btn = QPushButton("发送特征数据")
        self.send_features_btn.setMinimumHeight(45)
        self.send_features_btn.setEnabled(False)
        self.send_features_btn.setStyleSheet("""
            QPushButton {
                background-color: #7B1FA2;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #9C27B0; }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        send_layout.addWidget(self.send_features_btn)

        serial_tab_layout.addWidget(send_group)
        serial_tab_layout.addStretch()

        # ===== 页签3: SSH设置 =====
        ssh_tab = QWidget()
        ssh_layout = QVBoxLayout(ssh_tab)
        ssh_layout.setSpacing(12)

        ssh_group = QGroupBox("SSH连接设置")
        ssh_form = QFormLayout(ssh_group)

        self.ssh_host_edit = QLineEdit("192.168.1.100")
        self.ssh_host_edit.setMinimumHeight(30)
        ssh_form.addRow("主机IP:", self.ssh_host_edit)

        self.ssh_port_spin = QSpinBox()
        self.ssh_port_spin.setRange(1, 65535)
        self.ssh_port_spin.setValue(22)
        self.ssh_port_spin.setFixedWidth(100)
        ssh_form.addRow("端口:", self.ssh_port_spin)

        self.ssh_user_edit = QLineEdit("root")
        self.ssh_user_edit.setMinimumHeight(30)
        ssh_form.addRow("用户名:", self.ssh_user_edit)

        self.ssh_pass_edit = QLineEdit()
        self.ssh_pass_edit.setEchoMode(QLineEdit.Password)
        self.ssh_pass_edit.setMinimumHeight(30)
        self.ssh_pass_edit.setPlaceholderText("输入密码")
        ssh_form.addRow("密码:", self.ssh_pass_edit)

        self.ssh_connect_btn = QPushButton("连接SSH")
        self.ssh_connect_btn.setMinimumHeight(40)
        self.ssh_connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #1E88E5; }
        """)
        ssh_form.addRow("", self.ssh_connect_btn)

        self.ssh_status_label = QLabel("- 未连接")
        self.ssh_status_label.setStyleSheet("color: #F44336; font-weight: bold;")
        ssh_form.addRow("状态:", self.ssh_status_label)

        ssh_layout.addWidget(ssh_group)
        ssh_layout.addStretch()

        self.tab_widget.addTab(data_tab, "数据导入")
        self.tab_widget.addTab(serial_tab, "串口与发送")
        self.tab_widget.addTab(ssh_tab, "SSH设置")

        layout.addWidget(self.tab_widget)

    def _connect_signals(self):
        self.browse_btn.clicked.connect(self._browse_csv)
        self.load_btn.clicked.connect(self._load_csv)
        self.send_btn.clicked.connect(self._send_to_dsp)
        self.send_features_btn.clicked.connect(self._send_features_to_rk3566)
        self.connect_btn.clicked.connect(self._toggle_connection)
        self.refresh_port_btn.clicked.connect(self._refresh_ports)
        self.apply_btn.clicked.connect(self._apply_settings)
        self.ssh_connect_btn.clicked.connect(self._toggle_ssh)

    def _load_saved_settings(self):
        csv = self._settings_mgr.get_csv_settings()
        self.fs_spin.setValue(csv['fs'])
        self.voltage_col_spin.setValue(csv['voltage_column'])
        self.skip_rows_spin.setValue(csv['skip_rows'])
        self.max_points_spin.setValue(csv['max_points'])

        serial = self._settings_mgr.get_serial_settings()
        self.baudrate_combo.setCurrentText(str(serial['baudrate']))
        self.interval_spin.setValue(self._settings_mgr.get_send_settings()['send_interval_ms'])

        port = serial.get('port', '')
        if port:
            idx = self.port_combo.findText(port)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)

        # 加载SSH设置
        ssh = self._settings_mgr.get_ssh_settings()
        self.ssh_host_edit.setText(ssh['host'])
        self.ssh_port_spin.setValue(ssh['port'])
        self.ssh_user_edit.setText(ssh['username'])
        self.ssh_pass_edit.setText(ssh['password'])

    def update_port_list(self, ports: list):
        current = self.port_combo.currentText()
        self.port_combo.clear()
        if ports:
            self.port_combo.addItems(ports)
            if current in ports:
                self.port_combo.setCurrentText(current)
        else:
            self.port_combo.addItem("无可用串口")

    def set_settings(self, settings: dict):
        baudrate = str(settings.get('baudrate', 9600))
        self.baudrate_combo.setCurrentText(baudrate)

    def get_serial_settings(self) -> dict:
        return {
            'port': self.port_combo.currentText().strip(),
            'baudrate': int(self.baudrate_combo.currentText()),
            'bytesize': 8,
            'parity': 'N',
            'stopbits': 1,
        }

    def get_csv_name(self) -> str:
        if self._current_csv_path:
            return Path(self._current_csv_path).stem
        return ""

    def get_send_interval(self) -> int:
        return self.interval_spin.value()

    @Slot(int, int, str)
    def on_send_progress(self, current: int, total: int, msg: str):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        pct = current / total * 100 if total > 0 else 0
        self.progress_bar.setFormat(f"{msg} ({pct:.0f}%)")

    @Slot(bool, str)
    def on_send_complete(self, success: bool, msg: str):
        if success:
            self.progress_bar.setFormat("发送完成 - 等待DSP返回特征值...")
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }")
        else:
            self.progress_bar.setFormat(f"发送失败: {msg}")
            self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }")
        self.send_btn.setEnabled(True)

    @Slot(bool, str)
    def update_connection_status(self, connected: bool, msg: str):
        self._is_connected = connected
        if connected:
            self.connect_btn.setText("断开连接")
            self.conn_status_label.setText(f"- 已连接: {msg}")
            self.conn_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            if self._waveform_data is not None:
                self.send_btn.setEnabled(True)
                self.send_features_btn.setEnabled(True)
        else:
            self.connect_btn.setText("连接串口")
            self.conn_status_label.setText("- 未连接")
            self.conn_status_label.setStyleSheet("color: #F44336; font-weight: bold;")
            self.send_btn.setEnabled(False)
            self.send_features_btn.setEnabled(False)

    def update_ssh_status(self, connected: bool, msg: str):
        self._ssh_connected = connected
        if connected:
            self.ssh_connect_btn.setText("断开SSH")
            self.ssh_status_label.setText(f"- 已连接: {msg}")
            self.ssh_status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.ssh_connect_btn.setText("连接SSH")
            self.ssh_status_label.setText("- 未连接")
            self.ssh_status_label.setStyleSheet("color: #F44336; font-weight: bold;")

    def _apply_settings(self):
        port = self.port_combo.currentText().strip()
        baudrate = int(self.baudrate_combo.currentText())

        self._settings_mgr.set('Serial', 'port', port)
        self._settings_mgr.set('Serial', 'baudrate', str(baudrate))
        self._settings_mgr.set('Send', 'send_interval_ms', str(self.interval_spin.value()))

        QMessageBox.information(self, "成功", "设置已保存")

    def _browse_csv(self):
        last_dir = self._settings_mgr.get('CSV', 'last_directory', '')
        path, _ = QFileDialog.getOpenFileName(
            self, "选择CSV文件", last_dir,
            "CSV文件 (*.csv);;所有文件 (*.*)"
        )
        if path:
            self._current_csv_path = path
            self.csv_path_label.setText(path)
            self._settings_mgr.set('CSV', 'last_directory', str(Path(path).parent))

    def _load_csv(self):
        if not self._current_csv_path:
            QMessageBox.warning(self, "提示", "请先选择CSV文件")
            return
        try:
            col = self.voltage_col_spin.value()
            skip_rows = self.skip_rows_spin.value()
            max_points = self.max_points_spin.value()
            df = pd.read_csv(self._current_csv_path, header=None, skiprows=skip_rows)
            if df.shape[1] <= col:
                QMessageBox.warning(self, "错误", f"CSV只有{df.shape[1]}列")
                return
            voltage = pd.to_numeric(df.iloc[:, col], errors='coerce').values
            voltage = np.nan_to_num(voltage, nan=0.0)
            if len(voltage) == 0:
                QMessageBox.warning(self, "错误", "未读取到有效数据")
                return
            if len(voltage) > max_points:
                indices = np.linspace(0, len(voltage)-1, max_points, dtype=int)
                voltage = voltage[indices]
            self._waveform_data = voltage.astype(np.float64)
            fs = self.fs_spin.value()

            self._settings_mgr.set('CSV', 'voltage_column', str(col))
            self._settings_mgr.set('CSV', 'skip_rows', str(skip_rows))
            self._settings_mgr.set('CSV', 'fs', str(fs))
            self._settings_mgr.set('CSV', 'max_points', str(max_points))

            self.waveform_loaded.emit(voltage, fs)
            QMessageBox.information(self, "加载成功", f"已加载 {len(voltage)} 个采样点\n采样率: {fs} Hz")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载失败:\n{e}")

    def _send_to_dsp(self):
        if self._waveform_data is None or len(self._waveform_data) == 0:
            QMessageBox.warning(self, "提示", "请先加载CSV")
            return
        self.send_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("正在发送...")
        self.send_requested.emit(self._waveform_data)

    def _send_features_to_rk3566(self):
        if self._waveform_data is None or len(self._waveform_data) == 0:
            QMessageBox.warning(self, "提示", "请先加载CSV")
            return
        if not self._is_connected:
            QMessageBox.warning(self, "提示", "请先连接串口")
            return
        from core.feature_extractor import FeatureExtractor
        from core.constants import FEATURE_NAMES
        extractor = FeatureExtractor(fs=self.fs_spin.value())
        features_dict = extractor.extract(self._waveform_data)
        features = np.array([features_dict[name] for name in FEATURE_NAMES], dtype=np.float32)
        self.send_features_requested.emit(features)
        QMessageBox.information(self, "提示", "本地特征已发送到RK3566")

    def _toggle_connection(self):
        if self._is_connected:
            self.disconnect_requested.emit()
        else:
            port = self.port_combo.currentText().strip()
            baudrate = int(self.baudrate_combo.currentText())
            if not port:
                QMessageBox.warning(self, "提示", "请选择串口")
                return
            self.connect_requested.emit(port, baudrate)

    def _toggle_ssh(self):
        if self._ssh_connected:
            self.ssh_disconnect_requested.emit()
        else:
            host = self.ssh_host_edit.text().strip()
            port = self.ssh_port_spin.value()
            user = self.ssh_user_edit.text().strip()
            pwd = self.ssh_pass_edit.text()
            if not host:
                QMessageBox.warning(self, "提示", "请输入主机IP")
                return
            # 保存SSH设置
            self._settings_mgr.save_ssh_settings(host, port, user, pwd)
            self.ssh_connect_requested.emit(host, port, user, pwd)

    def _refresh_ports(self):
        try:
            import serial.tools.list_ports
            ports = [p.device for p in serial.tools.list_ports.comports()]
            self.update_port_list(ports)
        except Exception:
            pass