"""
日志页面UI - 波形显示、特征对比、通信日志
"""
import numpy as np
from datetime import datetime
from typing import List, Dict
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QCheckBox, QComboBox,
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QTextCursor, QColor, QFont

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


class WaveformCanvas(FigureCanvas):
    """波形显示画布"""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8, 2.5), dpi=100)
        self.fig.set_facecolor('#ffffff')
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#fafbfc')
        super().__init__(self.fig)
        self.setParent(parent)
        self.setMinimumHeight(180)
        self.setMaximumHeight(220)

    def plot_waveform(self, data: np.ndarray, title: str = "波形显示", fs: int = 1000):
        self.ax.clear()
        self.ax.set_facecolor('#fafbfc')
        n = len(data)
        if fs and n > 0:
            t = np.arange(n) / fs
            self.ax.plot(t, data, linewidth=0.8, color='#1a237e')
            self.ax.set_xlabel("时间 (s)", fontsize=9)
        else:
            self.ax.plot(data, linewidth=0.8, color='#1a237e')
            self.ax.set_xlabel("采样点", fontsize=9)
        self.ax.set_ylabel("电压 (V)", fontsize=9)
        self.ax.set_title(title, fontsize=11, fontweight='bold', color='#2c3e50')
        self.ax.grid(True, alpha=0.3, linestyle='--')
        self.ax.tick_params(labelsize=8)
        self.fig.tight_layout()
        self.draw()


class LogPage(QWidget):
    """接收日志页面"""

    toggle_monitor = Signal(bool)
    refresh_ports = Signal()
    port_selected = Signal(str)
    clear_log = Signal()
    save_log = Signal()

    def __init__(self):
        super().__init__()
        self._current_waveform: np.ndarray = None
        self._dsp_features: List[float] = []
        self._local_features: Dict[str, float] = {}
        self._csv_name: str = ""
        self._log_count = 0
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        self.canvas = WaveformCanvas()
        main_layout.addWidget(self.canvas)

        self.feature_table = QTableWidget()
        self.feature_table.setColumnCount(4)
        self.feature_table.setHorizontalHeaderLabels(
            ["特征名称", "DSP值", "本地值", "差异(%)"]
        )
        self.feature_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.feature_table.setAlternatingRowColors(True)
        main_layout.addWidget(self.feature_table, 1)

        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 4, 0, 0)
        bottom_layout.setSpacing(4)

        ctrl_layout = QHBoxLayout()
        port_label = QLabel("串口:")
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(100)
        self.port_combo.setMaximumWidth(150)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setMinimumWidth(60)
        self.toggle_switch = QCheckBox("开启监控")
        self.show_raw_check = QCheckBox("原始数据")

        ctrl_layout.addWidget(port_label)
        ctrl_layout.addWidget(self.port_combo)
        ctrl_layout.addWidget(self.refresh_btn)
        ctrl_layout.addWidget(self.toggle_switch)
        ctrl_layout.addWidget(self.show_raw_check)
        ctrl_layout.addStretch()

        self.clear_table_btn = QPushButton("清除表格")
        self.clear_table_btn.setMaximumWidth(80)
        self.export_compare_btn = QPushButton("导出对比")
        self.export_compare_btn.setMaximumWidth(80)
        ctrl_layout.addWidget(self.clear_table_btn)
        ctrl_layout.addWidget(self.export_compare_btn)
        bottom_layout.addLayout(ctrl_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setMaximumHeight(150)
        self.log_text.setMinimumHeight(80)
        bottom_layout.addWidget(self.log_text)

        log_ctrl_layout = QHBoxLayout()
        log_ctrl_layout.addStretch()
        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.setMaximumWidth(80)
        self.save_btn = QPushButton("导出日志")
        self.save_btn.setMaximumWidth(80)
        log_ctrl_layout.addWidget(self.clear_btn)
        log_ctrl_layout.addWidget(self.save_btn)
        bottom_layout.addLayout(log_ctrl_layout)

        main_layout.addWidget(bottom_widget)

        self.toggle_switch.toggled.connect(self.toggle_monitor.emit)
        self.refresh_btn.clicked.connect(self.refresh_ports.emit)
        self.port_combo.currentTextChanged.connect(self.port_selected.emit)
        self.clear_btn.clicked.connect(self.clear_log.emit)
        self.save_btn.clicked.connect(self.save_log.emit)
        self.clear_btn.clicked.connect(self._clear_log)
        self.save_btn.clicked.connect(self._save_log)
        self.clear_table_btn.clicked.connect(self._clear_table)
        self.export_compare_btn.clicked.connect(self._export_compare)

    def set_csv_name(self, name: str):
        self._csv_name = name

    def update_port_list(self, ports: list):
        current = self.port_combo.currentText()
        self.port_combo.clear()
        self.port_combo.addItems(ports)
        if current in ports:
            self.port_combo.setCurrentText(current)

    def get_selected_port(self) -> str:
        return self.port_combo.currentText()

    @Slot(np.ndarray, int)
    def set_waveform(self, data: np.ndarray, fs: int = 1000):
        from core.feature_extractor import FeatureExtractor
        extractor = FeatureExtractor(fs=fs)
        self._current_waveform = data
        title = f"波形 ({len(data)}点, {fs}Hz)"
        self.canvas.plot_waveform(data, title, fs)
        self._local_features = extractor.extract(data)
        self._update_feature_table()
        self.append_log(f"[系统] 波形已加载: {len(data)}点, 采样率{fs}Hz", "INFO")

    @Slot(list, float)
    def add_received_data(self, features: list, timestamp: float):
        self._dsp_features = features
        self._update_feature_table()
        dt = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3]

        self.append_log(f"\n{'='*50}", "INFO")
        self.append_log(f"[DSP] 特征值 [{dt}]", "SUCCESS")
        self._print_features(features)

        if self._local_features:
            local_list = []
            from core.constants import FEATURE_NAMES
            for name in FEATURE_NAMES:
                val = self._local_features.get(name, float('nan'))
                local_list.append(val if np.isfinite(val) else 0.0)
            self.append_log(f"\n[本地] 特征值:", "INFO")
            self._print_features(local_list)
            self.append_log(f"{'='*50}\n", "INFO")

    @Slot(int, int, str)
    def on_send_progress(self, current: int, total: int, msg: str):
        self.append_log(f"[发送] {msg}", "DEBUG")

    @Slot(bool, str)
    def on_send_complete(self, success: bool, msg: str):
        level = "SUCCESS" if success else "ERROR"
        self.append_log(f"[发送] {msg}", level)

    def append_log(self, message: str, level: str = "INFO", raw_hex: str = None):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color_map = {
            "INFO": "#a6adc8",
            "WARNING": "#f9e2af",
            "ERROR": "#f38ba8",
            "SUCCESS": "#a6e3a1",
            "DEBUG": "#89b4fa",
        }
        color = color_map.get(level, "#a6adc8")
        html = (
            f'<span style="color:#585b70;">[{timestamp}]</span> '
            f'<span style="color:{color};">[{level}]</span> '
            f'<span style="color:#cdd6f4;">{message}</span>'
        )
        if raw_hex and self.show_raw_check.isChecked():
            html += f'<br><span style="color:#f9e2af;font-size:10px;">  HEX: {raw_hex}</span>'

        self.log_text.append(html)
        self.log_text.moveCursor(QTextCursor.End)
        self._log_count += 1

    def _print_features(self, features: list):
        names = [
            "T1_能量", "T2_LZ复杂度", "T3_均值", "T4_均方根", "T5_标准差",
            "T6_偏度", "T7_峭度", "T8_波形因子", "T9_裕度因子",
            "T10_脉冲因子", "T11_峰值因子", "T12_峭度因子",
            "T13_中心频率", "T14_均方频率", "T15_均方根频率",
            "T16_频率方差", "T17_频率标准差",
        ]
        for name, val in zip(names, features):
            self.append_log(f"  {name:15s}: {val:.6f}", "INFO")

    def _update_feature_table(self):
        from core.constants import FEATURE_NAMES
        self.feature_table.setRowCount(len(FEATURE_NAMES))
        for i, name in enumerate(FEATURE_NAMES):
            self.feature_table.setItem(i, 0, QTableWidgetItem(name))
            if i < len(self._dsp_features):
                dsp_val = self._dsp_features[i]
                dsp_text = f"{dsp_val:.6f}" if np.isfinite(dsp_val) else "-"
            else:
                dsp_text = "-"
            self.feature_table.setItem(i, 1, QTableWidgetItem(dsp_text))
            if self._local_features:
                local_val = self._local_features.get(name)
                if local_val is not None and np.isfinite(local_val):
                    local_text = f"{local_val:.6f}"
                else:
                    local_text = "-"
            else:
                local_text = "-"
            self.feature_table.setItem(i, 2, QTableWidgetItem(local_text))
            if i < len(self._dsp_features) and self._local_features:
                dsp_v = self._dsp_features[i]
                loc_v = self._local_features.get(name)
                if dsp_v is not None and loc_v is not None and np.isfinite(loc_v) and abs(loc_v) > 1e-12:
                    diff = abs(dsp_v - loc_v) / abs(loc_v) * 100
                    diff_text = f"{diff:.2f}%"
                    diff_item = QTableWidgetItem(diff_text)
                    if diff > 10:
                        diff_item.setForeground(QColor("#F44336"))
                    elif diff > 5:
                        diff_item.setForeground(QColor("#FF9800"))
                    else:
                        diff_item.setForeground(QColor("#4CAF50"))
                else:
                    diff_item = QTableWidgetItem("-")
            else:
                diff_item = QTableWidgetItem("-")
            self.feature_table.setItem(i, 3, diff_item)

    def _clear_table(self):
        self._dsp_features = []
        self.feature_table.setRowCount(0)

    def _export_compare(self):
        from core.settings_manager import SettingsManager
        sm = SettingsManager()
        compare_dir = Path(sm.get_compare_export_dir())
        if not compare_dir.is_absolute():
            compare_dir = Path(__file__).parent.parent / compare_dir
        compare_dir.mkdir(parents=True, exist_ok=True)

        csv_name = self._csv_name or "compare"
        default_name = f"{csv_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出特征对比", str(compare_dir / default_name),
            "CSV文件 (*.csv)"
        )
        if not path:
            return
        lines = ["特征名称,DSP值,本地值,差异(%)"]
        for i in range(self.feature_table.rowCount()):
            name = self.feature_table.item(i, 0).text() if self.feature_table.item(i, 0) else ""
            dsp = self.feature_table.item(i, 1).text() if self.feature_table.item(i, 1) else ""
            local = self.feature_table.item(i, 2).text() if self.feature_table.item(i, 2) else ""
            diff = self.feature_table.item(i, 3).text() if self.feature_table.item(i, 3) else ""
            lines.append(f"{name},{dsp},{local},{diff}")
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        self.append_log(f"[系统] 特征对比已导出: {path}", "SUCCESS")

    def _clear_log(self):
        self.log_text.clear()
        self._log_count = 0

    def _save_log(self):
        from core.settings_manager import SettingsManager
        sm = SettingsManager()
        log_dir = Path(sm.get_log_export_dir())
        if not log_dir.is_absolute():
            log_dir = Path(__file__).parent.parent / log_dir
        log_dir.mkdir(parents=True, exist_ok=True)

        csv_name = self._csv_name or "log"
        default_name = f"{csv_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", str(log_dir / default_name),
            "文本文件 (*.txt)"
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())
            self.append_log(f"[系统] 日志已导出: {path}", "SUCCESS")

    def get_log_text(self) -> str:
        return self.log_text.toPlainText()

    def set_monitor_state(self, enabled: bool):
        self.toggle_switch.setChecked(enabled)

    def set_controls_enabled(self, enabled: bool):
        self.port_combo.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)