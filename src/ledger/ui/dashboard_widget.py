"""首页总览组件模块"""
from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)

from ledger.services.statistics_service import StatisticsService
from ledger.settings import format_money_from_float
from ledger.ui.theme import (
    COLOR_INCOME, COLOR_EXPENSE,
    get_text_color_str, get_secondary_text_color, get_card_style, get_balance_color
)


class SummaryCard(QFrame):
    """数据卡片组件"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self._update_card_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # 标题
        self.title_label = QLabel(title)
        self._update_title_style()
        layout.addWidget(self.title_label)
        
        # 主数值
        self.value_label = QLabel("$0.00")
        self._update_value_style()
        layout.addWidget(self.value_label)
        
        # 副信息
        self.sub_label = QLabel("")
        self._update_sub_style()
        layout.addWidget(self.sub_label)
    
    def _update_card_style(self) -> None:
        self.setStyleSheet(get_card_style())
    
    def _update_title_style(self) -> None:
        color = get_secondary_text_color()
        self.title_label.setStyleSheet(f"color: {color}; font-size: 13px;")
    
    def _update_value_style(self, color: str = None) -> None:
        if color is None:
            color = get_text_color_str()
        self.value_label.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
    
    def _update_sub_style(self, color: str = None) -> None:
        if color is None:
            color = get_secondary_text_color()
        self.sub_label.setStyleSheet(f"color: {color}; font-size: 12px;")
    
    def set_value(self, value: float, color: str = None) -> None:
        """设置主数值"""
        self.value_label.setText(format_money_from_float(value))
        self._update_value_style(color)
    
    def set_sub_text(self, text: str, color: str = None) -> None:
        """设置副信息"""
        self.sub_label.setText(text)
        self._update_sub_style(color)


class DashboardWidget(QWidget):
    """首页总览组件"""
    
    def __init__(self, stats_service: StatisticsService, parent=None):
        super().__init__(parent)
        self.stats_service = stats_service
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # 标题
        today = date.today()
        self.title_label = QLabel(f"📊 {today.year}年{today.month}月 财务概览")
        self._update_title_style()
        layout.addWidget(self.title_label)
        
        # 本月卡片区域
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(16)
        
        # 本月支出卡片
        self.expense_card = SummaryCard("本月支出")
        cards_layout.addWidget(self.expense_card)
        
        # 本月收入卡片
        self.income_card = SummaryCard("本月收入")
        cards_layout.addWidget(self.income_card)
        
        # 本月结余卡片
        self.balance_card = SummaryCard("本月结余")
        cards_layout.addWidget(self.balance_card)
        
        layout.addLayout(cards_layout)
        
        # 本年汇总区域
        year_layout = QHBoxLayout()
        year_layout.setSpacing(16)
        
        self.year_expense_card = SummaryCard("本年累计支出")
        year_layout.addWidget(self.year_expense_card)
        
        self.year_income_card = SummaryCard("本年累计收入")
        year_layout.addWidget(self.year_income_card)
        
        layout.addLayout(year_layout)
        
        # 弹性空间
        layout.addStretch()
    
    def _update_title_style(self) -> None:
        color = get_text_color_str()
        self.title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")
    
    def refresh(self) -> None:
        """刷新Dashboard数据"""
        # 更新标题日期
        today = date.today()
        self.title_label.setText(f"📊 {today.year}年{today.month}月 财务概览")
        self._update_title_style()
        
        # 本月数据
        current_month = self.stats_service.get_current_month_summary()
        self.expense_card.set_value(current_month.expense, COLOR_EXPENSE)
        self.income_card.set_value(current_month.income, COLOR_INCOME)
        
        balance = current_month.balance
        self.balance_card.set_value(balance, get_balance_color(balance))
        
        # 环比变化
        mom_change = self.stats_service.get_month_over_month_change()
        expense_change = mom_change["expense_change"]
        if expense_change != 0:
            arrow = "↑" if expense_change > 0 else "↓"
            change_color = COLOR_EXPENSE if expense_change > 0 else COLOR_INCOME
            self.expense_card.set_sub_text(
                f"较上月 {arrow} {format_money_from_float(abs(expense_change))}",
                change_color
            )
        else:
            self.expense_card.set_sub_text("与上月持平")
        
        income_change = mom_change["income_change"]
        if income_change != 0:
            arrow = "↑" if income_change > 0 else "↓"
            change_color = COLOR_INCOME if income_change > 0 else COLOR_EXPENSE
            self.income_card.set_sub_text(
                f"较上月 {arrow} {format_money_from_float(abs(income_change))}",
                change_color
            )
        else:
            self.income_card.set_sub_text("与上月持平")
        
        # 本年数据
        current_year = self.stats_service.get_current_year_summary()
        self.year_expense_card.set_value(current_year.expense, COLOR_EXPENSE)
        self.year_income_card.set_value(current_year.income, COLOR_INCOME)
