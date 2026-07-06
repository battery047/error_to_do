"""
串口调试页面UI
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QComboBox, QPushButton,
    QTextEdit, QCheckBox, QSplitter, QLineEdit,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont


class DevicesPage(QWidget):
    """串口调试工具页面"""

    send_data = Signal(bytes)
    clear_receive = Signal()

    def __init__(self, device_manager=None, parent=None):
        super().__init__(parent)
        self._serial = None
        self._setup_ui()
        self._connect_signals()

        self._timer = QTimer()
        self._timer.timeout.connect(self._poll_serial)
        self._timer.start(50)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ===== 串口设置 =====
        serial_group = QGroupBox("串口设置")
        serial_layout = QHBoxLayout(serial_group)

        port_layout = QHBoxLayout()
        port_label = QLabel("串口:")
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_combo)
        serial_layout.addLayout(port_layout)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setMaximumWidth(60)
        serial_layout.addWidget(self.refresh_btn)

        serial_layout.addWidget(QLabel("波特率:"))
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baudrate_combo.setCurrentText("9600")
        self.baudrate_combo.setMaximumWidth(100)
        serial_layout.addWidget(self.baudrate_combo)

        self.open_btn = QPushButton("打开串口")
        self.open_btn.setMinimumWidth(80)
        serial_layout.addWidget(self.open_btn)

        serial_layout.addStretch()
        layout.addWidget(serial_group)

        # ===== 分割器 =====
        splitter = QSplitter(Qt.Vertical)

        # ===== 上半：接收区 =====
        receive_widget = QWidget()
        receive_layout = QVBoxLayout(receive_widget)
        receive_layout.setContentsMargins(0, 0, 0, 0)
        receive_layout.setSpacing(4)

        receive_header = QHBoxLayout()
        receive_header.addWidget(QLabel("接收数据"))
        self.hex_display_check = QCheckBox("HEX显示")
        receive_header.addWidget(self.hex_display_check)
        receive_header.addStretch()
        self.clear_receive_btn = QPushButton("清空")
        self.clear_receive_btn.setMaximumWidth(60)
        receive_header.addWidget(self.clear_receive_btn)
        receive_layout.addLayout(receive_header)

        self.receive_text = QTextEdit()
        self.receive_text.setReadOnly(True)
        self.receive_text.setFont(QFont("Consolas", 10))
        receive_layout.addWidget(self.receive_text)

        splitter.addWidget(receive_widget)

        # ===== 下半：发送区 =====
        send_widget = QWidget()
        send_layout = QVBoxLayout(send_widget)
        send_layout.setContentsMargins(0, 0, 0, 0)
        send_layout.setSpacing(4)

        send_header = QHBoxLayout()
        send_header.addWidget(QLabel("发送数据"))
        self.hex_send_check = QCheckBox("HEX发送")
        send_header.addWidget(self.hex_send_check)

        send_header.addWidget(QLabel("换行:"))
        self.newline_combo = QComboBox()
        self.newline_combo.addItems(["无", "\\r\\n", "\\n", "\\r"])
        self.newline_combo.setMaximumWidth(80)
        send_header.addWidget(self.newline_combo)

        send_header.addStretch()
        self.send_btn = QPushButton("发送")
        self.send_btn.setMinimumWidth(80)
        send_header.addWidget(self.send_btn)
        send_layout.addLayout(send_header)

        send_input_layout = QHBoxLayout()
        self.send_text = QLineEdit()
        self.send_text.setPlaceholderText("输入要发送的数据...")
        self.send_text.setMinimumHeight(32)
        self.send_text.setFont(QFont("Consolas", 10))
        send_input_layout.addWidget(self.send_text)
        send_layout.addLayout(send_input_layout)

        splitter.addWidget(send_widget)

        splitter.setSizes([350, 150])
        layout.addWidget(splitter)

    def _connect_signals(self):
        self.clear_receive_btn.clicked.connect(self.clear_receive.emit)
        self.clear_receive_btn.clicked.connect(self._clear_receive)
        self.open_btn.clicked.connect(self._toggle_serial)
        self.send_btn.clicked.connect(self._send_data)
        self.refresh_btn.clicked.connect(self._refresh_ports)

    def _clear_receive(self):
        self.receive_text.clear()

    def update_port_list(self, ports: list):
        current = self.port_combo.currentText()
        self.port_combo.clear()
        if ports:
            self.port_combo.addItems(ports)
            if current in ports:
                self.port_combo.setCurrentText(current)

    def append_receive(self, data: bytes):
        if self.hex_display_check.isChecked():
            text = data.hex()
        else:
            text = data.decode('utf-8', errors='replace')
        self.receive_text.append(text)

    def _toggle_serial(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            self._serial = None
            self.open_btn.setText("打开串口")
            self.append_receive("\r\n[系统] 串口已关闭\r\n".encode())
        else:
            import serial
            port = self.port_combo.currentText().strip()
            baudrate = int(self.baudrate_combo.currentText())
            if not port:
                self.append_receive("\r\n[错误] 请选择串口\r\n".encode())
                return
            try:
                self._serial = serial.Serial(port, baudrate, timeout=0.1)
                self.open_btn.setText("关闭串口")
                msg = "\r\n[系统] 已连接 {} @ {}\r\n".format(port, baudrate)
                self.append_receive(msg.encode())
            except Exception as e:
                self.append_receive("\r\n[错误] {}\r\n".format(e).encode())

    def _send_data(self):
        if not self._serial or not self._serial.is_open:
            self.append_receive("\r\n[错误] 串口未打开\r\n".encode())
            return
        text = self.send_text.text()
        if not text:
            return
        try:
            if self.hex_send_check.isChecked():
                text = text.replace(" ", "").replace("\n", "").replace("\r", "")
                self.append_receive("\r\n[调试] 发送HEX: {}\r\n".format(text[:50]).encode())
                data = bytes.fromhex(text)
                self._serial.write(data)
                self.append_receive("\r\n[调试] 已发送 {} 字节\r\n".format(len(data)).encode())
            else:
                data = text.encode('utf-8')
                self._serial.write(data)
        except Exception as e:
            self.append_receive("\r\n[错误] {}\r\n".format(e).encode())

    def _refresh_ports(self):
        try:
            import serial.tools.list_ports
            ports = [p.device for p in serial.tools.list_ports.comports()]
            self.update_port_list(ports)
        except Exception:
            pass

    def _poll_serial(self):
        if self._serial and self._serial.is_open and self._serial.in_waiting > 0:
            try:
                data = self._serial.read(self._serial.in_waiting)
                self.append_receive(data)
            except Exception:
                pass