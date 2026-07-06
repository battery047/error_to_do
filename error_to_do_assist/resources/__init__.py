"""
资源管理器
"""
import os
from pathlib import Path


class ResourceManager:
    """资源管理器"""

    # 资源目录
    RESOURCES_DIR = Path(__file__).parent
    ICONS_DIR = RESOURCES_DIR / "icons"
    LOGOS_DIR = RESOURCES_DIR / "logos"

    # 图标尺寸配置
    ICON_SIZE = {
        'window': {'width': 32, 'height': 32},
    }

    LOGO_SIZE = {
        'about_page': {'width': 200, 'height': 130},
    }

    @classmethod
    def ensure_resources_dir(cls):
        """确保资源目录存在"""
        cls.ICONS_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGOS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_icon_path(cls) -> str:
        """获取应用图标路径"""
        icon_path = cls.ICONS_DIR / "app_icon.png"
        if icon_path.exists():
            return str(icon_path)
        # 尝试 ico 格式
        icon_path = cls.ICONS_DIR / "app_icon.ico"
        if icon_path.exists():
            return str(icon_path)
        return None

    @classmethod
    def get_logo_path(cls) -> str:
        """获取LOGO图片路径"""
        logo_path = cls.LOGOS_DIR / "logo.png"
        if logo_path.exists():
            return str(logo_path)
        return None