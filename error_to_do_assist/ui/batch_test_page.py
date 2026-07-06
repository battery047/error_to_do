"""
批量测试页面 - 文件夹CSV批量发送+日志
"""
import numpy as np
import pandas as pd
import time
import json
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QFormLayout,
    QLabel, QComboBox, QPushButton, QSpinBox, QTextEdit,
    QFileDialog, QProgressBar, QMessageBox, QCheckBox, QListWidget,
    QAbstractItemView, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QColor, QTextCursor

from core.feature_extractor import FeatureExtractor
from core.constants import FEATURE_NAMES, FEATURE_SHORT_NAMES


class BatchTestPage(QWidget):
    """批量测试页面"""

    send_requested = Signal(np.ndarray)
    send_features_requested = Signal(np.ndarray)
    refresh_ports = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._csv_folder: str = ""
        self._csv_files: list = []
        self._current_index: int = 0
        self._total_count: int = 0
        self._is_sending: bool = False
        self._send_timer = QTimer()
        self._send_timer.timeout.connect(self._send_next)
        self._batch_results: list = []  # 存储每批结果
        self._feature_extractor = None  # 修改1：复用特征提取器
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # ===== 配置区 =====
        config_group = QGroupBox("批量发送配置")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(6)

        # 第一行：文件夹选择
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("文件夹:"))
        self.folder_label = QLabel("未选择")
        self.folder_label.setStyleSheet("color:#757575;border:1px solid #ddd;padding:4px;border-radius:3px;background:white;")
        self.folder_label.setMinimumWidth(200)
        row1.addWidget(self.folder_label, 1)
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setMaximumWidth(80)
        self.browse_btn.setMinimumHeight(28)
        row1.addWidget(self.browse_btn)
        config_layout.addLayout(row1)

        # 第二行：采样率、电压列、跳过行
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("采样率:"))
        self.fs_spin = QSpinBox()
        self.fs_spin.setRange(100, 100000)
        self.fs_spin.setValue(1000)
        self.fs_spin.setSuffix("Hz")
        self.fs_spin.setMaximumWidth(100)
        row2.addWidget(self.fs_spin)

        row2.addSpacing(15)
        row2.addWidget(QLabel("电压列:"))
        self.voltage_col_spin = QSpinBox()
        self.voltage_col_spin.setRange(0, 10)
        self.voltage_col_spin.setValue(1)
        self.voltage_col_spin.setMaximumWidth(60)
        row2.addWidget(self.voltage_col_spin)

        row2.addSpacing(15)
        row2.addWidget(QLabel("跳过行:"))
        self.skip_rows_spin = QSpinBox()
        self.skip_rows_spin.setRange(0, 100)
        self.skip_rows_spin.setValue(0)
        self.skip_rows_spin.setMaximumWidth(60)
        row2.addWidget(self.skip_rows_spin)

        row2.addStretch()
        config_layout.addLayout(row2)

        # 第三行：最大点数、文件数、模式
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("最大点数:"))
        self.max_points_spin = QSpinBox()
        self.max_points_spin.setRange(100, 50000)
        self.max_points_spin.setValue(1000)
        self.max_points_spin.setSuffix("点")
        self.max_points_spin.setMaximumWidth(100)
        row3.addWidget(self.max_points_spin)

        row3.addSpacing(15)
        row3.addWidget(QLabel("文件数:"))
        self.file_count_spin = QSpinBox()
        self.file_count_spin.setRange(1, 1000)
        self.file_count_spin.setValue(10)
        self.file_count_spin.setSuffix("个")
        self.file_count_spin.setMaximumWidth(80)
        row3.addWidget(self.file_count_spin)

        row3.addSpacing(15)
        row3.addWidget(QLabel("模式:"))
        self.send_mode_combo = QComboBox()
        self.send_mode_combo.addItems(["仅发送波形", "仅发送特征", "波形+特征"])
        self.send_mode_combo.setMaximumWidth(130)
        row3.addWidget(self.send_mode_combo)

        row3.addStretch()
        config_layout.addLayout(row3)

        layout.addWidget(config_group)

        # ===== 控制按钮 =====
        ctrl_layout = QHBoxLayout()
        self.scan_btn = QPushButton("扫描文件")
        self.scan_btn.setMinimumHeight(30)
        ctrl_layout.addWidget(self.scan_btn)

        self.start_btn = QPushButton("开始批量发送")
        self.start_btn.setMinimumHeight(30)
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("QPushButton{background-color:#E64A19;color:white;font-weight:bold;border-radius:5px;}QPushButton:hover{background-color:#F4511E;}QPushButton:disabled{background-color:#BDBDBD;}")
        ctrl_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setMinimumHeight(30)
        self.stop_btn.setEnabled(False)
        ctrl_layout.addWidget(self.stop_btn)

        self.export_btn = QPushButton("导出结果")
        self.export_btn.setMinimumHeight(30)
        ctrl_layout.addWidget(self.export_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(22)
        self.progress_bar.setFormat("就绪")
        ctrl_layout.addWidget(self.progress_bar, 1)

        layout.addLayout(ctrl_layout)

        # ===== 文件列表 =====
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(80)
        self.file_list.setFont(QFont("Microsoft YaHei", 9))
        self.file_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.file_list.setStyleSheet("QListWidget{border:1px solid #ddd;border-radius:3px;background:white;color:#333;} QListWidget::item{padding:2px 6px;}")
        layout.addWidget(self.file_list)

        # ===== 日志区 =====
        log_group = QGroupBox("")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 4, 8, 6)
        log_layout.setSpacing(4)

        # 标题和按钮同行
        log_header = QHBoxLayout()
        log_title = QLabel("发送日志")
        log_title.setStyleSheet("font-weight:bold;color:#1a237e;background:transparent;")
        log_header.addWidget(log_title)
        log_header.addStretch()
        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.setMaximumWidth(70)
        self.clear_log_btn.setMinimumHeight(22)
        self.clear_log_btn.setStyleSheet("QPushButton{padding:2px 8px;font-size:11px;}")
        self.export_log_btn = QPushButton("导出日志")
        self.export_log_btn.setMaximumWidth(70)
        self.export_log_btn.setMinimumHeight(22)
        self.export_log_btn.setStyleSheet("QPushButton{padding:2px 8px;font-size:11px;}")
        log_header.addWidget(self.clear_log_btn)
        log_header.addWidget(self.export_log_btn)
        log_layout.addLayout(log_header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 8))
        self.log_text.setMinimumHeight(200)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)    

    def _connect_signals(self):
        self.browse_btn.clicked.connect(self._browse_folder)
        self.scan_btn.clicked.connect(self._scan_files)
        self.start_btn.clicked.connect(self._start_batch)
        self.stop_btn.clicked.connect(self._stop_batch)
        self.export_btn.clicked.connect(self._export_results)
        self.clear_log_btn.clicked.connect(self._clear_log)
        self.export_log_btn.clicked.connect(self._export_log)

    def _browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "选择CSV文件夹")
        if path:
            self._csv_folder = path
            self.folder_label.setText(path)

    def _scan_files(self):
        if not self._csv_folder:
            QMessageBox.warning(self, "提示", "请先选择文件夹")
            return
        self._csv_files = sorted(Path(self._csv_folder).glob("*.csv"))
        self.file_list.clear()
        for f in self._csv_files:
            self.file_list.addItem(f"  {f.name}")
        count = min(len(self._csv_files), self.file_count_spin.value())
        self._total_count = count
        self.start_btn.setEnabled(count > 0)
        self._add_log(f"[系统] 扫描到 {len(self._csv_files)} 个CSV，将发送 {count} 个", "#89b4fa")

    def _start_batch(self):
        if not self._csv_files:
            return
        self._total_count = min(len(self._csv_files), self.file_count_spin.value())
        self._current_index = 0
        self._batch_results = []
        self._is_sending = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setMaximum(self._total_count)
        self.progress_bar.setValue(0)
        self._add_log(f"\n{'─'*50}", "#585b70")
        self._add_log(f"[系统] 开始批量发送，共 {self._total_count} 个文件", "#89b4fa")
        self._add_log(f"{'─'*50}", "#585b70")
        self._send_timer.stop()  # 添加这行
        self._send_next()

    def _stop_batch(self):
        self._is_sending = False
        self._send_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._add_log(f"\n[系统] 批量发送已停止", "#f38ba8")

    def _send_next(self):
        if not self._is_sending or self._current_index >= self._total_count:
            self._is_sending = False
            self._send_timer.stop()  # 添加这行
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self._add_log(f"{'─'*50}", "#585b70")
            self._add_log(f"[系统] 批量发送完成，共 {len(self._batch_results)} 个", "#a6e3a1")
            self._add_log(f"{'─'*50}\n", "#585b70")
            return

        csv_path = self._csv_files[self._current_index]
        batch_no = self._current_index + 1
        try:
            col = self.voltage_col_spin.value()
            skip = self.skip_rows_spin.value()
            max_pts = self.max_points_spin.value()
            df = pd.read_csv(csv_path, header=None, skiprows=skip)
            voltage = pd.to_numeric(df.iloc[:, col], errors='coerce').values
            voltage = np.nan_to_num(voltage, nan=0.0)
            if len(voltage) > max_pts:
                indices = np.linspace(0, len(voltage)-1, max_pts, dtype=int)
                voltage = voltage[indices]

            self._waveform_data = voltage.astype(np.float64)
            fs = self.fs_spin.value()

            # 本地提取特征（修改1：复用提取器）
            if self._feature_extractor is None or self._feature_extractor.fs != fs:
                self._feature_extractor = FeatureExtractor(fs=fs)
            local_feat = self._feature_extractor.extract(voltage)

            mode = self.send_mode_combo.currentText()

            self._add_log(f"[{batch_no}/{self._total_count}] {csv_path.name} ({len(voltage)}点, {mode})", "#f9e2af")

            # 记录本次结果
            result = {
                'batch': batch_no,
                'file': csv_path.name,
                'samples': len(voltage),
                'mode': mode,
                'timestamp': datetime.now().isoformat(),
            }

            if mode == "仅发送波形" or mode == "波形+特征":
                self.send_requested.emit(voltage)
                self._add_log(f"  >>> 波形数据已发送", "#a6adc8")
                result['waveform_sent'] = True

            if mode == "仅发送特征" or mode == "波形+特征":
                features = np.array([local_feat[n] for n in FEATURE_NAMES], dtype=np.float32)
                self.send_features_requested.emit(features)
                self._add_log(f"  >>> 本地特征已发送 (CMD=0x22)", "#a6adc8")
                result['features_sent'] = True
                result['local_features'] = {n: float(local_feat[n]) for n in FEATURE_NAMES}

            self._batch_results.append(result)

        except Exception as e:
            self._add_log(f"  [错误] {e}", "#f38ba8")

        self._current_index += 1
        self.progress_bar.setValue(self._current_index)
        self._send_timer.start(2500)

    def set_dsp_result(self, features: list, time_ms: float):
        """收到DSP特征和时间"""
        # 修改2：修正条件判断
        if not self._batch_results or not self._is_sending:
            return

        # 更新最后一次结果
        if self._batch_results:
            last = self._batch_results[-1]
            last['dsp_time_ms'] = round(time_ms, 2)
            last['dsp_features'] = {FEATURE_NAMES[i]: float(features[i]) for i in range(min(17, len(features)))}

        # 打印特征值
        self._add_log(f"  [DSP] 特征提取耗时: {time_ms:.2f}ms", "#a6e3a1")
        self._add_log(f"  ┌─────────────────────────────────────────┐", "#585b70")
        self._add_log(f"  │ 特征名称          │ 值                    │", "#585b70")
        self._add_log(f"  ├─────────────────────────────────────────┤", "#585b70")
        for i in range(0, 17, 2):
            n1 = FEATURE_SHORT_NAMES[i]
            v1 = features[i] if i < len(features) else 0
            if i + 1 < 17:
                n2 = FEATURE_SHORT_NAMES[i+1]
                v2 = features[i+1]
                self._add_log(f"  │ {n1:12s} │ {v1:12.4f} │ {n2:12s} │ {v2:12.4f} │", "#cdd6f4")
            else:
                self._add_log(f"  │ {n1:12s} │ {v1:12.4f} │                        │", "#cdd6f4")
        self._add_log(f"  └─────────────────────────────────────────┘", "#585b70")

    def _add_log(self, msg: str, color: str = "#cdd6f4"):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        html = f'<span style="color:#585b70;">[{ts}]</span> <span style="color:{color};">{msg}</span>'
        self.log_text.append(html)
        self.log_text.moveCursor(QTextCursor.End)

    def _clear_log(self):
        self.log_text.clear()

    def _export_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出日志", f"batch_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "文本(*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())

    def _export_results(self):
        """导出批量结果JSON（格式兼容RK3588导出文件）"""
        path, _ = QFileDialog.getSaveFileName(
            self, "导出结果",
            f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON(*.json)"
        )
        if not path:
            return

        # 转换成与RK3588兼容的格式
        export_results = []
        for r in self._batch_results:
            item = {
                'index': r['batch'],
                'file': r['file'],
                'timestamp': r['timestamp'],
                'samples': r['samples'],
                'mode': r['mode'],
                'true_label': self._extract_label_from_filename(r['file'])
            }
            # 本地特征
            if 'local_features' in r:
                item['local_features'] = r['local_features']
            # DSP 特征（DSP返回的17个特征值）
            if 'dsp_features' in r:
                item['dsp_features'] = r['dsp_features']
            # DSP 特征提取耗时
            if 'dsp_time_ms' in r:
                item['dsp_time_ms'] = r['dsp_time_ms']
            # 波形发送状态
            if 'waveform_sent' in r:
                item['waveform_sent'] = r['waveform_sent']
            # 特征发送状态
            if 'features_sent' in r:
                item['features_sent'] = r['features_sent']

            export_results.append(item)

        # 统计DSP耗时
        dsp_times = [r['dsp_time_ms'] for r in self._batch_results if 'dsp_time_ms' in r]

        summary = {
            'source': '上位机',
            'total_count': len(self._batch_results),
            'export_time': datetime.now().isoformat(),
            'dsp_stats': {
                'avg_ms': round(np.mean(dsp_times), 2) if dsp_times else 0,
                'min_ms': round(np.min(dsp_times), 2) if dsp_times else 0,
                'max_ms': round(np.max(dsp_times), 2) if dsp_times else 0,
            } if dsp_times else {},
            'results': export_results,
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        self._add_log(f"[系统] 结果已导出: {path}", "#a6e3a1")
        
        
    @staticmethod
    def _extract_label_from_filename(file_name: str) -> str:
        """从文件名提取真实故障类型标签"""
        name = Path(file_name).stem.lower()
        if 'normal' in name:
            return 'normal'
        elif '1and2' in name or '1_and_2' in name:
            return 'A_bridge_error'
        elif '1or4' in name or '1_or_4' in name:
            return 'T1&T4'
        elif '2or3' in name or '2_or_3' in name:
            return 'T2&T3'
        return 'unknown'

    def update_port_list(self, ports: list):
        pass