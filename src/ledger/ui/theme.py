"""UI 主题工具模块 - 提供主题适配的颜色和样式"""
from typing import Final

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor


# 语义颜色常量（收入绿色、支出红色）
COLOR_INCOME: Final = "#2e7d32"
COLOR_EXPENSE: Final = "#c62828"

# 饼图/图表配色方案
CHART_COLORS: Final = [
    "#4CAF50", "#2196F3", "#FF9800", "#E91E63", "#9C27B0",
    "#00BCD4", "#8BC34A", "#FFEB3B", "#795548", "#607D8B",
    "#F44336", "#3F51B5", "#009688", "#FFC107", "#673AB7"
]


def get_text_color() -> QColor:
    """根据系统主题获取文字颜色"""
    palette = QApplication.palette()
    return palette.color(QPalette.WindowText)


def get_text_color_str() -> str:
    """获取文字颜色字符串"""
    return get_text_color().name()


def get_secondary_text_color() -> str:
    """获取次要文字颜色（透明度较低）"""
    palette = QApplication.palette()
    text_color = palette.color(QPalette.WindowText)
    text_color.setAlpha(180)
    return text_color.name()


def get_card_style() -> str:
    """获取卡片样式（适配系统主题）"""
    palette = QApplication.palette()
    bg_color = palette.color(QPalette.Base)
    border_color = palette.color(QPalette.Mid)
    return f"""
        SummaryCard {{
            background-color: {bg_color.name()};
            border: 1px solid {border_color.name()};
            border-radius: 8px;
            padding: 12px;
        }}
    """


def get_balance_color(balance: float) -> str:
    """根据余额正负返回对应颜色"""
    return COLOR_INCOME if balance >= 0 else COLOR_EXPENSE

