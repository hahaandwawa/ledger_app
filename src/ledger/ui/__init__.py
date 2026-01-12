"""用户界面模块"""
from ledger.ui.main_window import MainWindow
from ledger.ui.transaction_dialog import TransactionDialog
from ledger.ui.transaction_model import TransactionTableModel
from ledger.ui.dashboard_widget import DashboardWidget, SummaryCard
from ledger.ui.statistics_widget import StatisticsWidget, PieChartWidget, TrendChartWidget
from ledger.ui.management_dialogs import (
    SettingsDialog, CategoryManagementWidget, AccountManagementWidget
)
from ledger.ui.theme import (
    COLOR_INCOME, COLOR_EXPENSE, CHART_COLORS,
    get_text_color, get_text_color_str, get_secondary_text_color,
    get_card_style, get_balance_color
)

__all__ = [
    # 窗口和组件
    "MainWindow",
    "TransactionDialog",
    "TransactionTableModel",
    "DashboardWidget",
    "SummaryCard",
    "StatisticsWidget",
    "PieChartWidget",
    "TrendChartWidget",
    "SettingsDialog",
    "CategoryManagementWidget",
    "AccountManagementWidget",
    # 主题常量和函数
    "COLOR_INCOME",
    "COLOR_EXPENSE", 
    "CHART_COLORS",
    "get_text_color",
    "get_text_color_str",
    "get_secondary_text_color",
    "get_card_style",
    "get_balance_color",
]
