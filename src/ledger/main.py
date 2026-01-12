"""
Ledger App 主入口
"""
import sys
from pathlib import Path

# 将 src 目录添加到 Python 路径（仅在直接运行时需要）
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ledger.ui.main_window import MainWindow

# 资源目录路径
RESOURCES_DIR = Path(__file__).resolve().parent / "resources"


def main() -> int:
    """应用程序主入口"""
    app = QApplication(sys.argv)
    
    # 设置应用图标
    icon_path = RESOURCES_DIR / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

