"""统计分析页面组件模块"""
from datetime import date
from typing import List, Dict, Any, Tuple, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QDateEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QGridLayout,
    QCheckBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QDate, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

from ledger.services.statistics_service import StatisticsService, GranularityType
from ledger.settings import format_money_from_float
from ledger.ui.theme import (
    COLOR_INCOME, COLOR_EXPENSE, CHART_COLORS,
    get_text_color, get_text_color_str, get_balance_color
)


class PieChartWidget(QWidget):
    """饼状图组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._title = ""
        self._total = 0
        self.setMinimumHeight(280)
    
    def set_data(self, data: List[Dict[str, Any]], title: str = "") -> None:
        """设置数据，过滤掉金额为0的项"""
        self._data = [item for item in data if item.get("amount", 0) > 0][:10]
        self._title = title
        self._total = sum(item.get("amount", 0) for item in self._data)
        self.update()
    
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        text_color = get_text_color()
        
        # 无数据提示
        if not self._data or self._total == 0:
            painter.setPen(text_color)
            painter.drawText(self.rect(), Qt.AlignCenter, "该时间段没有支出记录")
            return
        
        # 布局参数
        margin = 20
        legend_width = 180
        chart_area_width = self.width() - legend_width - margin * 3
        chart_size = min(chart_area_width, self.height() - margin * 2 - 30)
        
        if chart_size < 50:
            return
        
        # 饼图中心和半径
        center_x = margin + chart_size / 2
        center_y = margin + 25 + chart_size / 2
        radius = chart_size / 2 - 10
        
        # 绘制标题
        if self._title:
            painter.setPen(text_color)
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(margin, 20, self._title)
            font.setBold(False)
            painter.setFont(font)
        
        # 绘制饼图扇区
        start_angle = 90 * 16  # 从顶部开始（Qt使用1/16度）
        rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        for i, item in enumerate(self._data):
            amount = item.get("amount", 0)
            percentage = (amount / self._total) if self._total > 0 else 0
            span_angle = int(percentage * 360 * 16)
            
            # 扇区颜色
            color = QColor(CHART_COLORS[i % len(CHART_COLORS)])
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color.darker(110), 1))
            
            painter.drawPie(rect, start_angle, -span_angle)
            start_angle -= span_angle
        
        # 绘制图例（右侧）
        legend_x = self.width() - legend_width - margin
        legend_y = margin + 30
        line_height = 24
        
        painter.setPen(text_color)
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        
        for i, item in enumerate(self._data):
            y = legend_y + i * line_height
            if y > self.height() - margin:
                break
            
            # 色块
            color = QColor(CHART_COLORS[i % len(CHART_COLORS)])
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawRect(int(legend_x), int(y), 12, 12)
            
            # 标签文本
            painter.setPen(text_color)
            category = item.get("category", "")[:8]
            amount = item.get("amount", 0)
            percentage = item.get("percentage", 0)
            
            label = f"{category}"
            painter.drawText(int(legend_x + 18), int(y + 11), label)
            
            # 金额和百分比（第二行或右侧）
            detail = f"{format_money_from_float(amount)} ({percentage:.1f}%)"
            painter.drawText(int(legend_x + 18), int(y + 11 + 12), detail)


class TrendChartWidget(QWidget):
    """收支趋势折线图组件
    
    特性：
    - 支持按天/周/月/年四种粒度
    - X轴显示时间标签
    - Y轴显示金额（USD）
    - 两条折线：支出（红）和收入（绿）
    - 通过分类筛选控制各线显示内容
    - 自动适配深色/浅色主题
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: List[Dict[str, Any]] = []
        self._granularity: str = "day"  # "day", "week", "month", "year"
        self.setMinimumHeight(250)
        self.setMinimumWidth(300)  # 确保有足够的宽度绘制图表
    
    def set_data(
        self,
        data: List[Dict[str, Any]],
        granularity: str = "day"
    ) -> None:
        """
        设置趋势数据
        
        Args:
            data: [{"label": str, "income": float, "expense": float}, ...]
            granularity: "day", "week", "month", "year"
        """
        self._data = data
        self._granularity = granularity
        self.update()
    
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        text_color = get_text_color()
        
        # 检查是否有数据
        if not self._data:
            painter.setPen(text_color)
            painter.drawText(self.rect(), Qt.AlignCenter, "该时间段没有收支记录")
            return
        
        # 检查是否所有数据都为0
        total_income = sum(item.get("income", 0) for item in self._data)
        total_expense = sum(item.get("expense", 0) for item in self._data)
        if total_expense == 0 and total_income == 0:
            painter.setPen(text_color)
            painter.drawText(self.rect(), Qt.AlignCenter, "该时间段没有收支记录\n（或所有分类均未选中）")
            return
        
        # 布局参数
        margin_left = 70  # 留空间给Y轴标签
        margin_right = 20
        margin_top = 30
        margin_bottom = 50  # 留空间给X轴标签和图例
        
        chart_width = self.width() - margin_left - margin_right
        chart_height = self.height() - margin_top - margin_bottom
        
        if chart_width <= 0 or chart_height <= 0:
            return
        
        # 计算Y轴最大值
        max_expense = max((item.get("expense", 0) for item in self._data), default=0)
        max_income = max((item.get("income", 0) for item in self._data), default=0)
        max_value = max(max_expense, max_income, 1)
        
        # 添加10%余量
        max_value = max_value * 1.1
        
        # 计算点位置
        num_points = len(self._data)
        step_x = chart_width / (num_points - 1) if num_points > 1 else chart_width
        
        expense_points = []
        income_points = []
        
        for i, item in enumerate(self._data):
            x = margin_left + i * step_x
            expense_val = item.get("expense", 0)
            income_val = item.get("income", 0)
            expense_y = margin_top + chart_height - (expense_val / max_value * chart_height) if max_value > 0 else margin_top + chart_height
            income_y = margin_top + chart_height - (income_val / max_value * chart_height) if max_value > 0 else margin_top + chart_height
            expense_points.append((x, expense_y))
            income_points.append((x, income_y))
        
        # 绘制Y轴网格线和标签
        self._draw_y_axis(painter, text_color, margin_left, margin_top, chart_height, max_value)
        
        # 绘制X轴标签
        self._draw_x_axis(painter, text_color, margin_left, margin_top, chart_height, step_x)
        
        # 绘制折线和数据点（只有有数据时才绘制）
        if total_expense > 0:
            self._draw_line_with_points(painter, expense_points, COLOR_EXPENSE)
        if total_income > 0:
            self._draw_line_with_points(painter, income_points, COLOR_INCOME)
        
        # 绘制图例
        self._draw_legend(painter, text_color, total_income > 0, total_expense > 0)
    
    def _draw_line_with_points(self, painter: QPainter, points: List[Tuple[float, float]], color: str) -> None:
        """绘制折线和数据点"""
        if len(points) < 2:
            return
        
        line_color = QColor(color)
        painter.setPen(QPen(line_color, 2))
        
        # 绘制折线
        for i in range(len(points) - 1):
            painter.drawLine(
                int(points[i][0]), int(points[i][1]),
                int(points[i + 1][0]), int(points[i + 1][1])
            )
        
        # 绘制数据点
        painter.setBrush(QBrush(line_color))
        for x, y in points:
            painter.drawEllipse(int(x - 3), int(y - 3), 6, 6)
    
    def _draw_y_axis(self, painter: QPainter, text_color: QColor, 
                     margin_left: int, margin_top: int, chart_height: int, max_value: float) -> None:
        """绘制Y轴标签和网格线"""
        painter.setPen(QPen(text_color, 1))
        
        # 绘制5条网格线
        num_lines = 5
        for i in range(num_lines + 1):
            y = margin_top + chart_height - (i / num_lines * chart_height)
            value = max_value * i / num_lines
            
            # 网格线（浅色）
            grid_color = QColor(text_color)
            grid_color.setAlpha(30)
            painter.setPen(QPen(grid_color, 1, Qt.DashLine))
            painter.drawLine(margin_left, int(y), self.width() - 20, int(y))
            
            # Y轴标签（使用整数金额）
            painter.setPen(text_color)
            label = format_money_from_float(value).split('.')[0]  # 只显示整数部分
            painter.drawText(5, int(y + 4), label)
    
    def _draw_x_axis(self, painter: QPainter, text_color: QColor,
                     margin_left: int, margin_top: int, chart_height: int, step_x: float) -> None:
        """绘制X轴标签"""
        painter.setPen(text_color)
        
        num_points = len(self._data)
        if num_points == 0:
            return
        
        # 根据数据点数量决定标签显示间隔
        if num_points <= 7:
            label_interval = 1
        elif num_points <= 15:
            label_interval = 2
        elif num_points <= 31:
            label_interval = 5
        else:
            label_interval = max(1, num_points // 6)
        
        y_pos = margin_top + chart_height + 15
        
        for i, item in enumerate(self._data):
            if i % label_interval == 0 or i == num_points - 1:
                x = margin_left + i * step_x
                label = item.get("label", "")
                
                # 根据粒度简化标签显示
                if self._granularity == "day":
                    # 显示 MM-DD
                    if len(label) >= 10:
                        label = label[5:10]  # YYYY-MM-DD -> MM-DD
                elif self._granularity == "week":
                    # 已经是 YYYY-WXX 格式，显示 WXX
                    if label.startswith("20") and "-W" in label:
                        label = label.split("-")[1]  # YYYY-WXX -> WXX
                elif self._granularity == "month":
                    # 显示 YYYY-MM 或简化为 MM
                    if len(label) >= 7:
                        label = label[2:7]  # YYYY-MM -> YY-MM
                elif self._granularity == "year":
                    # 直接显示 YYYY
                    pass
                
                # 旋转绘制以避免重叠
                painter.save()
                painter.translate(x, y_pos)
                painter.rotate(-45)
                painter.drawText(0, 0, label)
                painter.restore()
    
    def _draw_legend(self, painter: QPainter, text_color: QColor, 
                     has_income: bool = True, has_expense: bool = True) -> None:
        """绘制图例"""
        legend_y = self.height() - 15
        legend_x = self.width() - 150
        
        offset = 0
        
        # 支出图例（仅在有支出数据时绘制）
        if has_expense:
            painter.setPen(QPen(QColor(COLOR_EXPENSE), 2))
            painter.drawLine(legend_x + offset, legend_y, legend_x + offset + 20, legend_y)
            painter.setPen(text_color)
            painter.drawText(legend_x + offset + 25, legend_y + 4, "支出")
            offset += 70
        
        # 收入图例（仅在有收入数据时绘制）
        if has_income:
            painter.setPen(QPen(QColor(COLOR_INCOME), 2))
            painter.drawLine(legend_x + offset, legend_y, legend_x + offset + 20, legend_y)
            painter.setPen(text_color)
            painter.drawText(legend_x + offset + 25, legend_y + 4, "收入")


class StatisticsWidget(QWidget):
    """统计分析页面"""
    
    def __init__(self, stats_service: StatisticsService, parent=None):
        super().__init__(parent)
        self.stats_service = stats_service
        self._init_ui()
        # 初始加载数据
        self.refresh()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 标题
        self.title_label = QLabel("📈 统计分析")
        self._update_title_style()
        layout.addWidget(self.title_label)
        
        # 时间范围选择
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("时间范围:"))
        
        self.period_combo = QComboBox()
        self.period_combo.addItem("本月", "current_month")
        self.period_combo.addItem("过去三个月", "last_3_months")
        self.period_combo.addItem("过去半年", "last_6_months")
        self.period_combo.addItem("过去一年", "last_12_months")
        self.period_combo.addItem("本年", "current_year")
        self.period_combo.addItem("自定义", "custom")
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)
        filter_layout.addWidget(self.period_combo)
        
        filter_layout.addWidget(QLabel("从:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setEnabled(False)
        filter_layout.addWidget(self.start_date)
        
        filter_layout.addWidget(QLabel("到:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setEnabled(False)
        filter_layout.addWidget(self.end_date)
        
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh)
        filter_layout.addWidget(refresh_btn)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # 汇总区域
        summary_group = QGroupBox("收支汇总")
        summary_layout = QGridLayout(summary_group)
        
        self.total_income_label = QLabel("$0.00")
        self.total_income_label.setStyleSheet(f"font-size: 18px; color: {COLOR_INCOME}; font-weight: bold;")
        summary_layout.addWidget(QLabel("总收入:"), 0, 0)
        summary_layout.addWidget(self.total_income_label, 0, 1)
        
        self.total_expense_label = QLabel("$0.00")
        self.total_expense_label.setStyleSheet(f"font-size: 18px; color: {COLOR_EXPENSE}; font-weight: bold;")
        summary_layout.addWidget(QLabel("总支出:"), 0, 2)
        summary_layout.addWidget(self.total_expense_label, 0, 3)
        
        self.balance_label = QLabel("$0.00")
        self.balance_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        summary_layout.addWidget(QLabel("净结余:"), 0, 4)
        summary_layout.addWidget(self.balance_label, 0, 5)
        
        layout.addWidget(summary_group)
        
        # 图表区域
        charts_layout = QHBoxLayout()
        
        # 分类统计（饼图）
        category_group = QGroupBox("支出分类")
        category_layout = QVBoxLayout(category_group)
        self.category_chart = PieChartWidget()
        category_layout.addWidget(self.category_chart)
        
        self.category_table = QTableWidget()
        self.category_table.setColumnCount(3)
        self.category_table.setHorizontalHeaderLabels(["分类", "金额", "占比"])
        self.category_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.category_table.setMaximumHeight(150)
        category_layout.addWidget(self.category_table)
        
        charts_layout.addWidget(category_group, 1)  # stretch factor = 1
        
        # 趋势图
        trend_group = QGroupBox("收支趋势")
        trend_layout = QVBoxLayout(trend_group)
        
        # 趋势图控制区 - 第一行：粒度选择
        trend_controls_row1 = QHBoxLayout()
        
        # 时间粒度选择器
        trend_controls_row1.addWidget(QLabel("粒度:"))
        self.granularity_combo = QComboBox()
        self.granularity_combo.addItem("日", "day")
        self.granularity_combo.addItem("周", "week")
        self.granularity_combo.addItem("月", "month")
        self.granularity_combo.addItem("年", "year")
        self.granularity_combo.setCurrentIndex(0)  # 默认：日
        self.granularity_combo.currentIndexChanged.connect(self._refresh_trend_chart)
        trend_controls_row1.addWidget(self.granularity_combo)
        
        trend_controls_row1.addStretch()
        trend_layout.addLayout(trend_controls_row1)
        
        # 趋势图控制区 - 第二行：分类筛选勾选框
        category_filter_layout = QHBoxLayout()
        
        # 支出分类筛选
        expense_filter_group = QGroupBox("支出分类筛选")
        expense_filter_layout = QVBoxLayout(expense_filter_group)
        expense_filter_layout.setSpacing(2)
        expense_filter_layout.setContentsMargins(5, 5, 5, 5)
        
        # 支出分类勾选框容器
        self.expense_checkboxes_widget = QWidget()
        self.expense_checkboxes_layout = QHBoxLayout(self.expense_checkboxes_widget)
        self.expense_checkboxes_layout.setSpacing(8)
        self.expense_checkboxes_layout.setContentsMargins(0, 0, 0, 0)
        self.expense_category_checkboxes: Dict[str, QCheckBox] = {}
        
        # 添加滚动区域支持多分类
        expense_scroll = QScrollArea()
        expense_scroll.setWidgetResizable(True)
        expense_scroll.setWidget(self.expense_checkboxes_widget)
        expense_scroll.setMaximumHeight(50)
        expense_scroll.setFrameShape(QFrame.NoFrame)
        expense_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        expense_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        expense_filter_layout.addWidget(expense_scroll)
        
        category_filter_layout.addWidget(expense_filter_group, 1)
        
        # 收入分类筛选
        income_filter_group = QGroupBox("收入分类筛选")
        income_filter_layout = QVBoxLayout(income_filter_group)
        income_filter_layout.setSpacing(2)
        income_filter_layout.setContentsMargins(5, 5, 5, 5)
        
        # 收入分类勾选框容器
        self.income_checkboxes_widget = QWidget()
        self.income_checkboxes_layout = QHBoxLayout(self.income_checkboxes_widget)
        self.income_checkboxes_layout.setSpacing(8)
        self.income_checkboxes_layout.setContentsMargins(0, 0, 0, 0)
        self.income_category_checkboxes: Dict[str, QCheckBox] = {}
        
        # 添加滚动区域支持多分类
        income_scroll = QScrollArea()
        income_scroll.setWidgetResizable(True)
        income_scroll.setWidget(self.income_checkboxes_widget)
        income_scroll.setMaximumHeight(50)
        income_scroll.setFrameShape(QFrame.NoFrame)
        income_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        income_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        income_filter_layout.addWidget(income_scroll)
        
        category_filter_layout.addWidget(income_filter_group, 1)
        
        trend_layout.addLayout(category_filter_layout)
        
        # 趋势图
        self.trend_chart = TrendChartWidget()
        trend_layout.addWidget(self.trend_chart)
        
        charts_layout.addWidget(trend_group, 1)  # stretch factor = 1，确保平分空间
        
        layout.addLayout(charts_layout)
    
    def _update_title_style(self) -> None:
        color = get_text_color_str()
        self.title_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")
    
    def _on_period_changed(self) -> None:
        """时间范围选择变化"""
        is_custom = self.period_combo.currentData() == "custom"
        self.start_date.setEnabled(is_custom)
        self.end_date.setEnabled(is_custom)
    
    def _get_date_range(self) -> Tuple[str, str]:
        """获取当前选择的日期范围"""
        period = self.period_combo.currentData()
        today = date.today()
        
        if period == "current_month":
            return self.stats_service.get_month_range(today.year, today.month)
        elif period == "last_3_months":
            return self.stats_service.get_last_3_months_range()
        elif period == "last_6_months":
            return self.stats_service.get_last_6_months_range()
        elif period == "last_12_months":
            return self.stats_service.get_last_12_months_range()
        elif period == "current_year":
            return self.stats_service.get_year_range(today.year)
        else:  # custom
            return (
                self.start_date.date().toString("yyyy-MM-dd"),
                self.end_date.date().toString("yyyy-MM-dd")
            )
    
    def refresh(self) -> None:
        """刷新统计数据"""
        self._update_title_style()
        start, end = self._get_date_range()
        
        # 汇总数据
        summary = self.stats_service.get_custom_period_summary(start, end)
        self.total_income_label.setText(format_money_from_float(summary.income))
        self.total_expense_label.setText(format_money_from_float(summary.expense))
        
        balance = summary.balance
        self.balance_label.setText(format_money_from_float(balance))
        self.balance_label.setStyleSheet(f"font-size: 18px; color: {get_balance_color(balance)}; font-weight: bold;")
        
        # 分类明细
        category_data = self.stats_service.get_category_breakdown(start, end, "expense")
        self.category_chart.set_data(category_data, "支出分类")
        
        # 更新分类表格
        self.category_table.setRowCount(len(category_data))
        for i, item in enumerate(category_data):
            self.category_table.setItem(i, 0, QTableWidgetItem(item["category"]))
            self.category_table.setItem(i, 1, QTableWidgetItem(format_money_from_float(item['amount'])))
            self.category_table.setItem(i, 2, QTableWidgetItem(f"{item['percentage']:.1f}%"))
        
        # 更新分类筛选勾选框
        self._update_category_filters()
        
        # 刷新趋势图
        self._refresh_trend_chart()

    def _update_category_filters(self) -> None:
        """更新收入和支出分类筛选勾选框"""
        start, end = self._get_date_range()
        
        # 获取当前时间范围内实际有数据的分类
        expense_categories = self.stats_service.get_expense_categories(start, end)
        income_categories = self.stats_service.get_income_categories(start, end)
        
        # 更新支出分类勾选框
        self._update_checkboxes(
            expense_categories,
            self.expense_category_checkboxes,
            self.expense_checkboxes_layout,
            "expense"
        )
        
        # 更新收入分类勾选框
        self._update_checkboxes(
            income_categories,
            self.income_category_checkboxes,
            self.income_checkboxes_layout,
            "income"
        )
    
    def _update_checkboxes(
        self,
        categories: List[str],
        checkbox_dict: Dict[str, QCheckBox],
        layout: QHBoxLayout,
        category_type: str
    ) -> None:
        """更新指定类型的分类勾选框"""
        # 保存当前选中状态（只保存真正的 QCheckBox，跳过占位符）
        current_checked = {}
        for name, widget in checkbox_dict.items():
            if isinstance(widget, QCheckBox):
                current_checked[name] = widget.isChecked()
        
        # 清除现有控件（勾选框和占位符）
        for widget in list(checkbox_dict.values()):
            if hasattr(widget, 'blockSignals'):
                widget.blockSignals(True)
            layout.removeWidget(widget)
            widget.deleteLater()
        checkbox_dict.clear()
        
        # 清除布局中的弹性空间
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 如果没有分类，显示提示
        if not categories:
            placeholder = QLabel("（无数据）")
            placeholder.setStyleSheet("color: gray; font-style: italic;")
            layout.addWidget(placeholder)
            # 保存引用以便后续清除（使用特殊key，不会被当作分类处理）
            checkbox_dict["__placeholder__"] = placeholder  # type: ignore
            return
        
        # 创建新的勾选框
        for category_name in categories:
            checkbox = QCheckBox(category_name)
            # 恢复之前的选中状态，新分类默认选中
            checkbox.setChecked(current_checked.get(category_name, True))
            checkbox.stateChanged.connect(self._refresh_trend_chart)
            layout.addWidget(checkbox)
            checkbox_dict[category_name] = checkbox
        
        # 添加弹性空间
        layout.addStretch()

    def _refresh_trend_chart(self) -> None:
        """刷新趋势图（响应控件变化）"""
        start, end = self._get_date_range()
        
        # 获取当前控件状态
        granularity: GranularityType = self.granularity_combo.currentData() or "day"
        
        # 获取选中的收入分类
        income_categories = self._get_selected_categories(self.income_category_checkboxes)
        
        # 获取选中的支出分类
        expense_categories = self._get_selected_categories(self.expense_category_checkboxes)
        
        # 获取趋势数据
        trend_result = self.stats_service.get_trend_data_advanced(
            start, end, granularity,
            category=None,  # 不使用旧的单分类参数
            income_categories=income_categories,
            expense_categories=expense_categories
        )
        
        # 更新趋势图
        self.trend_chart.set_data(
            trend_result["data"],
            trend_result["granularity"]
        )
    
    def _get_selected_categories(self, checkbox_dict: Dict[str, QCheckBox]) -> Optional[List[str]]:
        """获取选中的分类列表
        
        Returns:
            选中的分类名称列表，如果没有勾选框则返回None（表示全部）
        """
        # 过滤掉占位符
        checkboxes = {k: v for k, v in checkbox_dict.items() 
                      if k != "__placeholder__" and isinstance(v, QCheckBox)}
        
        if not checkboxes:
            # 没有勾选框（无数据），返回空列表（不计算）
            return []
        
        # 返回选中的分类
        return [name for name, cb in checkboxes.items() if cb.isChecked()]
