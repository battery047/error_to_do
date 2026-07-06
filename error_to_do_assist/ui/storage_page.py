"""
存储页面UI - 日志查看 + CSV特征对比(离线)
"""
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QComboBox, QPushButton, QSpinBox,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QTextEdit, QSplitter,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor


class StoragePage(QWidget):
    """终端存储读取页面 - 上日志 + 下对比"""

    read_storage = Signal()
    save_storage = Signal()
    clear_display = Signal()
    show_local_log = Signal(str)
    refresh_log_list = Signal()

    def __init__(self):
        super().__init__()
        self._current_csv_path: str = ""
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Vertical)

        # ===== 上半部分：日志查看 =====
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        log_ctrl = QHBoxLayout()
        log_label = QLabel("本机日志:")
        self.log_combo = QComboBox()
        self.log_combo.setMinimumWidth(200)
        self.show_log_btn = QPushButton("显示")
        self.show_log_btn.setMaximumWidth(60)
        self.refresh_log_btn = QPushButton("刷新")
        self.refresh_log_btn.setMaximumWidth(60)
        self.open_log_file_btn = QPushButton("打开文件")
        self.open_log_file_btn.setMaximumWidth(80)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setMaximumWidth(60)

        log_ctrl.addWidget(log_label)
        log_ctrl.addWidget(self.log_combo, 1)
        log_ctrl.addWidget(self.show_log_btn)
        log_ctrl.addWidget(self.refresh_log_btn)
        log_ctrl.addWidget(self.open_log_file_btn)
        log_ctrl.addWidget(self.clear_btn)
        top_layout.addLayout(log_ctrl)

        self.display_text = QTextEdit()
        self.display_text.setReadOnly(True)
        self.display_text.setFont(QFont("Consolas", 9))
        top_layout.addWidget(self.display_text)

        splitter.addWidget(top_widget)

        # ===== 下半部分：离线特征对比（只显示表格）=====
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(6)

        compare_group = QGroupBox("离线特征对比")
        compare_layout = QVBoxLayout(compare_group)

        file_layout = QHBoxLayout()
        self.csv_path_label = QLabel("未选择对比文件")
        self.csv_path_label.setStyleSheet(
            "color: #757575; border: 1px solid #e0e0e0; "
            "padding: 6px; border-radius: 3px; background: white;"
        )
        self.csv_path_label.setMinimumHeight(30)
        file_layout.addWidget(self.csv_path_label, 1)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setMaximumWidth(80)
        file_layout.addWidget(self.browse_btn)

        self.load_compare_btn = QPushButton("加载对比表")
        self.load_compare_btn.setMaximumWidth(100)
        file_layout.addWidget(self.load_compare_btn)

        self.clear_compare_btn = QPushButton("清除")
        self.clear_compare_btn.setMaximumWidth(60)
        file_layout.addWidget(self.clear_compare_btn)

        compare_layout.addLayout(file_layout)

        # 特征对比表（只显示表格，无波形）
        self.feature_table = QTableWidget()
        self.feature_table.setColumnCount(4)
        self.feature_table.setHorizontalHeaderLabels(["特征名称", "CSV值", "DSP值", "差异(%)"])
        self.feature_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.feature_table.setAlternatingRowColors(True)
        compare_layout.addWidget(self.feature_table)

        bottom_layout.addWidget(compare_group)
        splitter.addWidget(bottom_widget)

        splitter.setSizes([400, 400])
        layout.addWidget(splitter)

    def _connect_signals(self):
        self.show_log_btn.clicked.connect(self._on_show_log_clicked)
        self.refresh_log_btn.clicked.connect(self.refresh_log_list.emit)
        self.open_log_file_btn.clicked.connect(self._on_open_log_file)
        self.clear_btn.clicked.connect(self.clear_display.emit)
        self.clear_btn.clicked.connect(self.clear_display_text)
        self.browse_btn.clicked.connect(self._browse_compare)
        self.load_compare_btn.clicked.connect(self._load_compare)
        self.clear_compare_btn.clicked.connect(self._clear_compare)

    def _on_show_log_clicked(self):
        selected = self.log_combo.currentData()
        if selected:
            self.show_local_log.emit(selected)

    def _on_open_log_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择日志文件", "", "日志文件 (*.log *.txt);;所有文件 (*.*)")
        if path:
            self.show_local_log.emit(path)

    def update_log_list(self, log_items: list):
        current = self.log_combo.currentData()
        self.log_combo.clear()
        for item in log_items:
            self.log_combo.addItem(item["display_name"], item["path"])
        if current:
            index = self.log_combo.findData(current)
            if index >= 0:
                self.log_combo.setCurrentIndex(index)

    def append_display(self, text: str):
        self.display_text.append(text)

    def clear_display_text(self):
        self.display_text.clear()

    def set_display_text(self, text: str):
        self.display_text.setPlainText(text)

    def get_display_text(self) -> str:
        return self.display_text.toPlainText()

    def _browse_compare(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择对比CSV文件", "", "CSV文件 (*.csv);;所有文件 (*.*)")
        if path:
            self._current_csv_path = path
            self.csv_path_label.setText(path)

    def _load_compare(self):
        if not self._current_csv_path:
            QMessageBox.warning(self, "提示", "请先选择对比CSV文件")
            return
        try:
            df = pd.read_csv(self._current_csv_path)
            # 期望列: 特征名称,CSV值,DSP值,差异(%)
            if df.shape[1] < 4:
                QMessageBox.warning(self, "错误", "文件格式不正确，需要4列")
                return

            self.feature_table.setRowCount(len(df))
            for i, row in df.iterrows():
                self.feature_table.setItem(i, 0, QTableWidgetItem(str(row.iloc[0])))
                self.feature_table.setItem(i, 1, QTableWidgetItem(str(row.iloc[1])))
                self.feature_table.setItem(i, 2, QTableWidgetItem(str(row.iloc[2])))
                diff_str = str(row.iloc[3])
                diff_item = QTableWidgetItem(diff_str)
                # 颜色标记
                if diff_str.endswith('%'):
                    try:
                        diff_val = float(diff_str.replace('%', ''))
                        if diff_val > 10:
                            diff_item.setForeground(QColor("#F44336"))
                        elif diff_val > 5:
                            diff_item.setForeground(QColor("#FF9800"))
                        else:
                            diff_item.setForeground(QColor("#4CAF50"))
                    except ValueError:
                        pass
                self.feature_table.setItem(i, 3, diff_item)

            QMessageBox.information(self, "成功", f"已加载 {len(df)} 条对比数据")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载失败:\n{e}")

    def _clear_compare(self):
        self.feature_table.setRowCount(0)
        self.csv_path_label.setText("未选择对比文件")
        self._current_csv_path = ""