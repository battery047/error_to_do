"""
常量定义 - 无循环导入
"""
from pathlib import Path

# ==================== 项目目录 ====================
BASE_DIR = Path(__file__).parent.parent
SETTINGS_DIR = BASE_DIR / "settings"
SETTINGS_FILE = SETTINGS_DIR / "settings.ini"
DEVICES_DIR = BASE_DIR / "devices_list"
DEVICES_FILE = DEVICES_DIR / "devices.json"
LOGS_DIR = BASE_DIR / "logs"
STORAGE_DIR = BASE_DIR / "storage"

# ==================== 应用信息 ====================
APP_NAME = "两电平电力电子设备故障识别与定位"
APP_VERSION = "1.0.0"
APP_ID = "error_to_do.monitor.app.1.0"

# ==================== 串口默认配置 ====================
DEFAULT_SERIAL = {
    "port": "COM3",
    "baudrate": 115200,
    "bytesize": 8,
    "stopbits": 1,
    "parity": "N",
    "timeout": 0.1,
}

# ==================== 通信协议 ====================
PACKET_HEADER = b'\xAA\x55'
PACKET_FOOTER = b'\x55\xAA'

SAMPLES_PER_PACKET = 100
SEND_INTERVAL_MS = 10

# DSP命令
CMD_START_SEND = b'\x01'
CMD_STOP_SEND = b'\x02'
CMD_REQUEST_RESULT = b'\x03'
CMD_RESET = b'\x04'
CMD_ACK = b'\x06'
CMD_NACK = b'\x15'
CMD_DATA_LENGTH = b'\x10'
CMD_WAVEFORM_DATA = b'\x11'

RSP_FEATURE_DATA = b'\x21'
RSP_STATUS_MSG = b'\x22'

# ==================== 特征名称 ====================
FEATURE_NAMES = [
    "T1_能量", "T2_LZ复杂度", "T3_均值", "T4_均方根", "T5_标准差",
    "T6_偏度", "T7_峭度", "T8_波形因子", "T9_裕度因子",
    "T10_脉冲因子", "T11_峰值因子", "T12_峭度因子",
    "T13_中心频率", "T14_均方频率", "T15_均方根频率",
    "T16_频率方差", "T17_频率标准差",
]

FEATURE_SHORT_NAMES = [
    "能量", "复杂度", "均值", "均方根", "标准差",
    "偏度", "峭度", "波形因子", "裕度因子",
    "脉冲因子", "峰值因子", "峭度因子",
    "中心频率", "均方频率", "均方根频率",
    "频率方差", "频率标准差",
]

# ==================== 确保目录存在 ====================
for _dir in [SETTINGS_DIR, DEVICES_DIR, LOGS_DIR, STORAGE_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)