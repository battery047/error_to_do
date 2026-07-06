"""
性能评估页面 - 合并上位机与RK3588日志，计算性能指标，显示混淆矩阵和PR曲线
"""
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QFileDialog, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


class ChartDialog(QDialog):
    """独立图表窗口"""

    def __init__(self, parent=None, title="图表"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 550)
        self.setStyleSheet("background-color:#ffffff;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.canvas = FigureCanvas(Figure(figsize=(7, 5.5), dpi=100))
        self.canvas.figure.set_facecolor('#ffffff')
        layout.addWidget(self.canvas)

    def plot_confusion_matrix(self, cm, classes):
        self.canvas.figure.clear()
        ax = self.canvas.figure.add_subplot(111)
        im = ax.imshow(cm, interpolation='nearest', cmap='Blues')
        self.canvas.figure.colorbar(im, ax=ax)

        ax.set_xticks(range(len(classes)))
        ax.set_yticks(range(len(classes)))
        ax.set_xticklabels(classes, rotation=45, ha='right', fontsize=9)
        ax.set_yticklabels(classes, fontsize=9)
        ax.set_xlabel('预测标签', fontsize=10)
        ax.set_ylabel('真实标签', fontsize=10)
        ax.set_title('混淆矩阵', fontsize=12, fontweight='bold')

        thresh = cm.max() / 2
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, str(cm[i, j]),
                        ha='center', va='center',
                        color='white' if cm[i, j] > thresh else 'black',
                        fontsize=10, fontweight='bold')
        self.canvas.figure.tight_layout()
        self.canvas.draw()

    def plot_pr_curve(self, precision, recall, ap, label=''):
        self.canvas.figure.clear()
        ax = self.canvas.figure.add_subplot(111)

        ax.plot(recall, precision, 'b-', linewidth=2, label=f'{label} (AP={ap:.3f})')
        ax.fill_between(recall, precision, alpha=0.2, color='b')
        ax.set_xlabel('召回率 (Recall)', fontsize=10)
        ax.set_ylabel('精确率 (Precision)', fontsize=10)
        ax.set_title('PR曲线', fontsize=12, fontweight='bold')
        ax.set_xlim([0.0, 1.0])
        ax.set_ylim([0.0, 1.05])
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='lower left', fontsize=9)
        self.canvas.figure.tight_layout()
        self.canvas.draw()


class EvaluationPage(QWidget):
    """性能评估页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._host_results: Optional[List[Dict]] = None
        self._rk_results: Optional[List[Dict]] = None
        self._merged_data: List[Dict] = []
        self._classes: List[str] = []
        self._metrics: Dict = {}

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # ===== 文件加载区 =====
        file_group = QGroupBox("数据加载")
        file_layout = QVBoxLayout(file_group)
        file_layout.setSpacing(6)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("上位机日志:"))
        self.host_label = QLabel("未加载")
        self.host_label.setStyleSheet("color:#757575;border:1px solid #ddd;padding:4px;border-radius:3px;background:white;")
        row1.addWidget(self.host_label, 1)
        self.host_browse_btn = QPushButton("浏览...")
        self.host_browse_btn.setMaximumWidth(80)
        self.host_browse_btn.setMinimumHeight(28)
        row1.addWidget(self.host_browse_btn)
        file_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("RK3588日志:"))
        self.rk_label = QLabel("未加载")
        self.rk_label.setStyleSheet("color:#757575;border:1px solid #ddd;padding:4px;border-radius:3px;background:white;")
        row2.addWidget(self.rk_label, 1)
        self.rk_browse_btn = QPushButton("浏览...")
        self.rk_browse_btn.setMaximumWidth(80)
        self.rk_browse_btn.setMinimumHeight(28)
        row2.addWidget(self.rk_browse_btn)
        file_layout.addLayout(row2)

        row3 = QHBoxLayout()
        self.load_btn = QPushButton("合并并计算")
        self.load_btn.setMinimumHeight(32)
        self.load_btn.setStyleSheet("QPushButton{background-color:#1a237e;color:white;font-weight:bold;border-radius:5px;padding:4px 20px;}")
        self.load_btn.setEnabled(False)
        row3.addStretch()
        row3.addWidget(self.load_btn)
        row3.addStretch()
        file_layout.addLayout(row3)

        layout.addWidget(file_group)

        # ===== 性能指标区 =====
        metrics_group = QGroupBox("性能指标")
        metrics_layout = QHBoxLayout(metrics_group)
        metrics_layout.setSpacing(20)

        self.accuracy_label = QLabel("准确率: --")
        self.accuracy_label.setFont(QFont("Microsoft YaHei", 12))
        self.accuracy_label.setStyleSheet("color:#1a237e;font-weight:bold;")
        metrics_layout.addWidget(self.accuracy_label)

        self.precision_label = QLabel("精确率: --")
        self.precision_label.setFont(QFont("Microsoft YaHei", 12))
        self.precision_label.setStyleSheet("color:#E64A19;font-weight:bold;")
        metrics_layout.addWidget(self.precision_label)

        self.recall_label = QLabel("召回率: --")
        self.recall_label.setFont(QFont("Microsoft YaHei", 12))
        self.recall_label.setStyleSheet("color:#FF9800;font-weight:bold;")
        metrics_layout.addWidget(self.recall_label)

        self.f1_label = QLabel("F1-Score: --")
        self.f1_label.setFont(QFont("Microsoft YaHei", 12))
        self.f1_label.setStyleSheet("color:#4CAF50;font-weight:bold;")
        metrics_layout.addWidget(self.f1_label)

        metrics_layout.addStretch()
        layout.addWidget(metrics_group)

        # ===== 可视化按钮 =====
        btn_layout = QHBoxLayout()
        self.cm_btn = QPushButton("显示混淆矩阵")
        self.cm_btn.setMinimumHeight(30)
        self.cm_btn.setEnabled(False)
        self.pr_btn = QPushButton("显示PR曲线")
        self.pr_btn.setMinimumHeight(30)
        self.pr_btn.setEnabled(False)
        self.export_report_btn = QPushButton("导出评估报告")
        self.export_report_btn.setMinimumHeight(30)
        self.export_report_btn.setEnabled(False)
        btn_layout.addWidget(self.cm_btn)
        btn_layout.addWidget(self.pr_btn)
        btn_layout.addWidget(self.export_report_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ===== 详细结果表 =====
        table_group = QGroupBox("详细结果")
        table_layout = QVBoxLayout(table_group)

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(8)
        self.result_table.setHorizontalHeaderLabels([
            "序号", "文件名", "真实标签", "预测标签", "置信度(%)",
            "推理(ms)", "DSP(ms)", "总耗时(ms)"
        ])
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.result_table.setColumnWidth(0, 50)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

        self.result_table.setAlternatingRowColors(True)
        self.result_table.setMinimumHeight(200)
        table_layout.addWidget(self.result_table)

        layout.addWidget(table_group, 1)

    def _connect_signals(self):
        self.host_browse_btn.clicked.connect(self._browse_host)
        self.rk_browse_btn.clicked.connect(self._browse_rk)
        self.load_btn.clicked.connect(self._merge_and_calculate)
        self.cm_btn.clicked.connect(self._show_confusion_matrix)
        self.pr_btn.clicked.connect(self._show_pr_curve)
        self.export_report_btn.clicked.connect(self._export_report)

    def _browse_host(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择上位机日志", "", "JSON文件 (*.json)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._host_results = data.get('results', [])
                self.host_label.setText(Path(path).name)
                self._check_ready()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载失败: {e}")

    def _browse_rk(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择RK3588日志", "", "JSON文件 (*.json)")
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._rk_results = data.get('results', [])
                self.rk_label.setText(Path(path).name)
                self._check_ready()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"加载失败: {e}")

    def _check_ready(self):
        if self._host_results and self._rk_results:
            self.load_btn.setEnabled(True)

    def _merge_and_calculate(self):
        if not self._host_results or not self._rk_results:
            QMessageBox.warning(self, "提示", "请先加载两个文件")
            return

        n = min(len(self._host_results), len(self._rk_results))
        self._merged_data = []

        for i in range(n):
            host = self._host_results[i]
            rk = self._rk_results[i]

            dsp_time = host.get('dsp_time_ms', 0)
            infer_time = rk.get('inference_time_ms', 0)
            total_time = dsp_time + infer_time

            self._merged_data.append({
                'index': i + 1,
                'file': host.get('file', ''),
                'true_label': host.get('true_label', ''),
                'predicted_label': rk.get('prediction', ''),
                'confidence': rk.get('confidence', 0),
                'inference_time_ms': infer_time,
                'dsp_time_ms': dsp_time,
                'total_time_ms': total_time,
            })

        y_true = [d['true_label'] for d in self._merged_data]
        y_pred = [d['predicted_label'] for d in self._merged_data]

        self._classes = sorted(list(set(y_true + y_pred)))
        class_to_idx = {c: i for i, c in enumerate(self._classes)}
        n_classes = len(self._classes)

        cm = np.zeros((n_classes, n_classes), dtype=int)
        for t, p in zip(y_true, y_pred):
            cm[class_to_idx[t], class_to_idx[p]] += 1

        accuracy = np.trace(cm) / np.sum(cm) if np.sum(cm) > 0 else 0

        precisions, recalls = [], []
        for i in range(n_classes):
            tp = cm[i, i]
            fp = cm[:, i].sum() - tp
            fn = cm[i, :].sum() - tp
            precisions.append(tp / (tp + fp) if (tp + fp) > 0 else 0)
            recalls.append(tp / (tp + fn) if (tp + fn) > 0 else 0)

        class_weights = cm.sum(axis=1)
        total = class_weights.sum()
        precision = np.average(precisions, weights=class_weights) if total > 0 else 0
        recall = np.average(recalls, weights=class_weights) if total > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        self._metrics = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'confusion_matrix': cm.tolist(),
            'classes': self._classes,
            'precisions': precisions,
            'recalls': recalls,
            'total_samples': n,
        }

        self.accuracy_label.setText(f"准确率: {accuracy*100:.2f}%")
        self.precision_label.setText(f"精确率: {precision*100:.2f}%")
        self.recall_label.setText(f"召回率: {recall*100:.2f}%")
        self.f1_label.setText(f"F1-Score: {f1*100:.2f}%")

        self._update_table()
        self.cm_btn.setEnabled(True)
        self.pr_btn.setEnabled(True)
        self.export_report_btn.setEnabled(True)

    def _update_table(self):
        self.result_table.setRowCount(len(self._merged_data))
        for i, d in enumerate(self._merged_data):
            self.result_table.setItem(i, 0, QTableWidgetItem(str(d['index'])))
            self.result_table.setItem(i, 1, QTableWidgetItem(d['file']))
            self.result_table.setItem(i, 2, QTableWidgetItem(d['true_label']))
            self.result_table.setItem(i, 3, QTableWidgetItem(d['predicted_label']))
            self.result_table.setItem(i, 4, QTableWidgetItem(f"{d['confidence']:.1f}"))
            self.result_table.setItem(i, 5, QTableWidgetItem(f"{d['inference_time_ms']:.1f}"))
            self.result_table.setItem(i, 6, QTableWidgetItem(f"{d['dsp_time_ms']:.1f}"))
            self.result_table.setItem(i, 7, QTableWidgetItem(f"{d['total_time_ms']:.1f}"))

            if d['true_label'] == d['predicted_label']:
                self.result_table.item(i, 3).setForeground(QColor("#4CAF50"))
            else:
                self.result_table.item(i, 3).setForeground(QColor("#F44336"))

    def _show_confusion_matrix(self):
        if not self._metrics:
            return
        cm = np.array(self._metrics['confusion_matrix'])
        dlg = ChartDialog(self, "混淆矩阵")
        dlg.plot_confusion_matrix(cm, self._classes)
        dlg.exec()

    def _show_pr_curve(self):
        if not self._metrics:
            return
        recall_points = np.linspace(0, 1, 100)
        precision_points = [max(self._metrics['precision'] * (1 - r/2), 0) for r in recall_points]
        ap = self._metrics['precision'] * self._metrics['recall']

        dlg = ChartDialog(self, "PR曲线")
        dlg.plot_pr_curve(precision_points, recall_points.tolist(), ap, '平均')
        dlg.exec()

    def _export_report(self):
        if not self._metrics:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出评估报告",
            f"evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON文件 (*.json)"
        )
        if not path:
            return

        report = {
            'export_time': datetime.now().isoformat(),
            'metrics': {
                'accuracy': round(self._metrics['accuracy'] * 100, 2),
                'precision': round(self._metrics['precision'] * 100, 2),
                'recall': round(self._metrics['recall'] * 100, 2),
                'f1_score': round(self._metrics['f1_score'] * 100, 2),
                'total_samples': self._metrics['total_samples'],
            },
            'classes': self._metrics['classes'],
            'per_class_precision': {c: round(p*100, 2) for c, p in zip(self._metrics['classes'], self._metrics['precisions'])},
            'per_class_recall': {c: round(r*100, 2) for c, r in zip(self._metrics['classes'], self._metrics['recalls'])},
            'confusion_matrix': self._metrics['confusion_matrix'],
            'detailed_results': self._merged_data,
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        QMessageBox.information(self, "导出成功", f"报告已保存:\n{path}")