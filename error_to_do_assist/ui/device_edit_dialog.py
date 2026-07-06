"""设备编辑对话框UI"""
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit,
    QSpinBox, QDialogButtonBox,
)


class DeviceEditDialog(QDialog):
    """设备编辑对话框"""

    def __init__(self, device_name="", channel="", group="", address="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑设备")
        self.setMinimumWidth(350)
        self._setup_ui(device_name, channel, group, address)

    def _setup_ui(self, name, channel, group, address):
        layout = QFormLayout(self)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("请输入设备名称")
        self.name_edit.setMinimumHeight(32)

        self.channel_edit = QSpinBox()
        self.channel_edit.setRange(0, 255)
        self.channel_edit.setValue(int(channel) if channel else 0)
        self.channel_edit.setMinimumHeight(32)

        self.group_edit = QSpinBox()
        self.group_edit.setRange(0, 255)
        self.group_edit.setValue(int(group) if group else 0)
        self.group_edit.setMinimumHeight(32)

        self.address_edit = QSpinBox()
        self.address_edit.setRange(0, 255)
        self.address_edit.setValue(int(address) if address else 0)
        self.address_edit.setMinimumHeight(32)

        layout.addRow("设备名称:", self.name_edit)
        layout.addRow("通信信道:", self.channel_edit)
        layout.addRow("本地组号:", self.group_edit)
        layout.addRow("本地地址:", self.address_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self) -> dict:
        """获取对话框数据"""
        return {
            'name': self.name_edit.text().strip(),
            'channel': str(self.channel_edit.value()),
            'group': str(self.group_edit.value()),
            'address': str(self.address_edit.value()),
        }