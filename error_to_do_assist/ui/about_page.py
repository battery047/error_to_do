"""关于页面UI"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.constants import APP_NAME, APP_VERSION


class AboutPage(QWidget):
    """关于页面"""

    def __init__(self):
        super().__init__()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(10)

        layout.addSpacing(30)

        # 标题
        title = QLabel(APP_NAME)
        title.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1a237e;")
        layout.addWidget(title)
        layout.addSpacing(10)

        # 版本
        version = QLabel(f"版本: {APP_VERSION}")
        version.setFont(QFont("Microsoft YaHei", 12))
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #757575;")
        layout.addWidget(version)
        layout.addSpacing(5)

        # 描述
        desc = QLabel("两电平电力电子设备故障识别与定位")
        desc.setFont(QFont("Microsoft YaHei", 10))
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        layout.addSpacing(30)

        # 分隔线
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #bdbdbd;")
        line.setMaximumWidth(400)
        layout.addWidget(line)
        layout.addSpacing(20)

        # 功能说明
        functions = [
            "CSV波形数据导入与显示",
            "串口分包发送到DSP TMS320F28335",
            "DSP在线提取17种时频域特征",
            "接收DSP特征值并本地对比验证",
            "RK3588 CNN推理与故障分类",
            "批量测试与性能指标评估",
            "SSH/SFTP文件传输",
        ]
        for func in functions:
            label = QLabel(f"  - {func}")
            label.setFont(QFont("Microsoft YaHei", 10))
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)

        layout.addSpacing(20)

        # 团队
        team_label = QLabel("Team: 慢慢尝试")
        team_label.setFont(QFont("Microsoft YaHei", 10))
        team_label.setAlignment(Qt.AlignCenter)
        team_label.setStyleSheet("color: #1a237e; font-weight: bold;")
        layout.addWidget(team_label)
        layout.addSpacing(5)

        # 作者
        author_label = QLabel("Author: batterymain")
        author_label.setFont(QFont("Microsoft YaHei", 10))
        author_label.setAlignment(Qt.AlignCenter)
        author_label.setStyleSheet("color: #1a237e; font-weight: bold;")
        layout.addWidget(author_label)
        layout.addSpacing(5)

        copyright_label = QLabel("(c) 2026 All Rights Reserved")
        copyright_label.setFont(QFont("Microsoft YaHei", 9))
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("color: #757575;")
        layout.addWidget(copyright_label)

        layout.addStretch()