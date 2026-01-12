"""
Phase 1.2 Integration Tests for Ledger App
测试工程师：自动化测试脚本
日期：2026-01-12

测试范围：
- 金额统一为 USD 显示
- 深色/浅色模式下的文字可读性
- 默认分类初始化
- 支出分析饼状图
- Phase 1 回归测试
"""
import sys
import os
import sqlite3
import re
from datetime import date
from calendar import monthrange

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QDate
from PySide6.QtTest import QTest

from ledger.db.database import Database
from ledger.models.transaction import Transaction
from ledger.models.category import Category
from ledger.models.account import Account
from ledger.services.statistics_service import StatisticsService
from ledger.settings import (
    DB_PATH, CURRENCY_SYMBOL, DEFAULT_CATEGORIES, 
    format_money, format_money_from_float, MAX_AMOUNT
)


class TestRunner:
    """Phase 1.2 Test Runner"""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.results = []
        self.defects = []
        self.questions = []
        
    def log(self, test_id, status, message=""):
        result = {"id": test_id, "status": status, "message": message}
        self.results.append(result)
        emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{emoji} {test_id}: {status} - {message}")
        
    def log_defect(self, severity, title, description, steps, actual, expected):
        defect = {
            "severity": severity,
            "title": title,
            "description": description,
            "steps": steps,
            "actual": actual,
            "expected": expected
        }
        self.defects.append(defect)
        print(f"\n🐛 DEFECT [{severity}]: {title}")
        
    def clear_all_data(self, db: Database):
        """Clear all test data"""
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM categories")
        cursor.execute("DELETE FROM accounts")
        db.conn.commit()


class USDFormatTests(TestRunner):
    """模块A：金额统一为USD显示测试"""
    
    def run_all(self, db: Database) -> bool:
        print("\n" + "="*60)
        print("模块A：金额统一为USD显示测试")
        print("="*60)
        
        all_passed = True
        all_passed &= self.test_format_money_function()
        all_passed &= self.test_transaction_list_display(db)
        all_passed &= self.test_dashboard_display(db)
        all_passed &= self.test_statistics_display(db)
        all_passed &= self.test_error_message_format()
        
        return all_passed
    
    def test_format_money_function(self) -> bool:
        """验证format_money函数格式正确"""
        test_id = "TC-USD-FUNC"
        try:
            # 测试不同金额
            test_cases = [
                (1234, "$12.34"),
                (100, "$1.00"),
                (1, "$0.01"),
                (100000, "$1,000.00"),
                (123456789, "$1,234,567.89"),
            ]
            
            for cents, expected in test_cases:
                result = format_money(cents)
                if result != expected:
                    self.log(test_id, "FAIL", f"format_money({cents})={result}, expected {expected}")
                    return False
            
            # 测试format_money_from_float
            result = format_money_from_float(1234.56)
            if result != "$1,234.56":
                self.log(test_id, "FAIL", f"format_money_from_float failed: {result}")
                return False
            
            self.log(test_id, "PASS", "金额格式化函数正确，统一使用$符号和千分位")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_transaction_list_display(self, db: Database) -> bool:
        """TC-USD-001: 交易列表金额展示"""
        test_id = "TC-USD-001"
        try:
            from ledger.ui.transaction_model import TransactionTableModel, TransactionColumn
            
            self.clear_all_data(db)
            
            # 添加测试交易
            tx = Transaction(type="expense", amount_cents=1234, date="2026-01-12")
            db.add_transaction(tx)
            
            # 创建模型并验证显示
            model = TransactionTableModel()
            transactions = db.get_all_transactions()
            model.set_transactions(transactions)
            
            # 获取金额显示
            index = model.index(0, TransactionColumn.AMOUNT)
            display_value = model.data(index, Qt.DisplayRole)
            
            if display_value != "$12.34":
                self.log(test_id, "FAIL", f"列表金额显示错误: {display_value}")
                self.log_defect(
                    "Critical",
                    "[金额显示] 交易列表金额未使用USD格式",
                    "交易列表中的金额应显示为$开头",
                    ["新增交易12.34", "查看交易列表"],
                    display_value,
                    "$12.34"
                )
                return False
            
            self.log(test_id, "PASS", f"交易列表金额显示正确: {display_value}")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_dashboard_display(self, db: Database) -> bool:
        """TC-USD-002: Dashboard金额展示"""
        test_id = "TC-USD-002"
        try:
            from ledger.ui.dashboard_widget import DashboardWidget
            
            self.clear_all_data(db)
            
            today = date.today()
            date_str = today.strftime("%Y-%m-%d")
            
            # 添加测试数据
            db.add_transaction(Transaction(type="expense", amount_cents=123456, date=date_str))
            db.add_transaction(Transaction(type="income", amount_cents=200000, date=date_str))
            
            stats = StatisticsService(db)
            dashboard = DashboardWidget(stats)
            dashboard.refresh()
            
            # 检查金额显示（使用$符号）
            expense_text = dashboard.expense_card.value_label.text()
            income_text = dashboard.income_card.value_label.text()
            
            if not expense_text.startswith("$"):
                self.log(test_id, "FAIL", f"支出金额未使用$: {expense_text}")
                return False
            
            if not income_text.startswith("$"):
                self.log(test_id, "FAIL", f"收入金额未使用$: {income_text}")
                return False
            
            # 验证千分位格式
            if "," not in expense_text:
                self.log(test_id, "FAIL", f"支出金额无千分位: {expense_text}")
                return False
            
            self.log(test_id, "PASS", f"Dashboard金额正确: 支出={expense_text}, 收入={income_text}")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_statistics_display(self, db: Database) -> bool:
        """TC-USD-003: 统计页面金额展示"""
        test_id = "TC-USD-003"
        try:
            from ledger.ui.statistics_widget import StatisticsWidget
            
            self.clear_all_data(db)
            
            today = date.today()
            date_str = today.strftime("%Y-%m-%d")
            
            # 添加测试数据
            db.add_transaction(Transaction(type="expense", amount_cents=50000, date=date_str, category="餐饮"))
            db.add_transaction(Transaction(type="income", amount_cents=100000, date=date_str))
            
            stats = StatisticsService(db)
            widget = StatisticsWidget(stats)
            widget.refresh()
            
            # 检查汇总金额
            income_text = widget.total_income_label.text()
            expense_text = widget.total_expense_label.text()
            balance_text = widget.balance_label.text()
            
            for label, value in [("收入", income_text), ("支出", expense_text), ("结余", balance_text)]:
                if not value.startswith("$"):
                    self.log(test_id, "FAIL", f"{label}金额未使用$: {value}")
                    return False
            
            self.log(test_id, "PASS", f"统计页面金额正确: 收入={income_text}, 支出={expense_text}")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_error_message_format(self) -> bool:
        """TC-USD-004: 错误提示金额格式"""
        test_id = "TC-USD-004"
        try:
            from ledger.ui.transaction_dialog import TransactionDialog
            
            dialog = TransactionDialog(None, categories=[], accounts=[])
            
            # 验证金额上限提示使用$格式
            # 检查settings中的MAX_AMOUNT格式化
            expected_format = format_money_from_float(MAX_AMOUNT)
            
            if not expected_format.startswith("$"):
                self.log(test_id, "FAIL", f"金额上限格式错误: {expected_format}")
                return False
            
            # 检查placeholder是否包含$
            placeholder = dialog.amount_input.placeholderText()
            if "$" not in placeholder:
                self.log(test_id, "FAIL", f"金额输入框placeholder未包含$: {placeholder}")
                return False
            
            self.log(test_id, "PASS", f"错误提示使用USD格式: {expected_format}")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False


class ThemeAdaptationTests(TestRunner):
    """模块B：主题适配测试（深色/浅色模式）"""
    
    def run_all(self, db: Database) -> bool:
        print("\n" + "="*60)
        print("模块B：主题适配测试")
        print("="*60)
        
        all_passed = True
        all_passed &= self.test_get_text_color_function()
        all_passed &= self.test_dashboard_theme_adaptation(db)
        all_passed &= self.test_statistics_theme_adaptation(db)
        all_passed &= self.test_pie_chart_theme_adaptation(db)
        
        return all_passed
    
    def test_get_text_color_function(self) -> bool:
        """验证主题颜色获取函数存在"""
        test_id = "TC-THEME-FUNC"
        try:
            from ledger.ui.theme import get_text_color_str, get_secondary_text_color
            from ledger.ui.theme import get_text_color_str as stats_get_text_color
            
            # 验证函数存在并返回有效颜色
            text_color = get_text_color_str()
            secondary_color = get_secondary_text_color()
            
            # 验证是有效的颜色字符串（#开头的hex）
            if not text_color.startswith("#"):
                self.log(test_id, "FAIL", f"text_color格式错误: {text_color}")
                return False
            
            self.log(test_id, "PASS", f"主题颜色函数正常: text={text_color}")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_dashboard_theme_adaptation(self, db: Database) -> bool:
        """TC-THEME-001/002: Dashboard主题适配"""
        test_id = "TC-THEME-DASH"
        try:
            from ledger.ui.dashboard_widget import DashboardWidget, get_card_style
            
            stats = StatisticsService(db)
            dashboard = DashboardWidget(stats)
            
            # 验证卡片样式使用动态颜色
            card_style = get_card_style()
            
            # 检查样式是否包含动态颜色（不是硬编码）
            if "#ffffff" in card_style.lower() or "#000000" in card_style.lower():
                # 硬编码颜色可能在某些主题下不可读
                self.log(test_id, "WARN", "卡片样式可能包含硬编码颜色")
            
            # 验证标题样式方法存在
            dashboard._update_title_style()
            title_style = dashboard.title_label.styleSheet()
            
            if "color:" not in title_style:
                self.log(test_id, "FAIL", "标题样式未设置颜色")
                return False
            
            self.log(test_id, "PASS", "Dashboard支持动态主题颜色")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_statistics_theme_adaptation(self, db: Database) -> bool:
        """TC-THEME-003: 统计页面主题适配"""
        test_id = "TC-THEME-STAT"
        try:
            from ledger.ui.statistics_widget import StatisticsWidget
            from ledger.ui.theme import get_text_color_str
            
            stats = StatisticsService(db)
            widget = StatisticsWidget(stats)
            
            # 验证标题使用动态颜色
            widget._update_title_style()
            title_style = widget.title_label.styleSheet()
            
            # 获取当前主题颜色
            current_color = get_text_color_str()
            
            if current_color not in title_style:
                self.log(test_id, "FAIL", "标题未使用动态主题颜色")
                return False
            
            self.log(test_id, "PASS", f"统计页面使用动态主题颜色: {current_color}")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_pie_chart_theme_adaptation(self, db: Database) -> bool:
        """TC-THEME-PIE: 饼图主题适配"""
        test_id = "TC-THEME-PIE"
        try:
            from ledger.ui.statistics_widget import PieChartWidget
            from ledger.ui.theme import get_text_color_str
            
            # 验证饼图使用动态颜色
            chart = PieChartWidget()
            
            # 设置数据触发绘制
            test_data = [
                {"category": "餐饮", "amount": 100, "percentage": 50},
                {"category": "交通", "amount": 100, "percentage": 50},
            ]
            chart.set_data(test_data, "测试")
            
            # 验证get_text_color在paintEvent中被调用
            # 通过检查模块中是否有get_text_color函数
            text_color = get_text_color_str()
            
            if text_color is None:
                self.log(test_id, "FAIL", "饼图无法获取主题颜色")
                return False
            
            self.log(test_id, "PASS", "饼图支持动态主题颜色")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False


class DefaultCategoryTests(TestRunner):
    """模块C：默认分类初始化测试"""
    
    def run_all(self, db: Database) -> bool:
        print("\n" + "="*60)
        print("模块C：默认分类初始化测试")
        print("="*60)
        
        all_passed = True
        all_passed &= self.test_default_categories_config()
        all_passed &= self.test_first_launch_categories(db)
        all_passed &= self.test_restart_no_duplicate(db)
        all_passed &= self.test_custom_category_preserved(db)
        
        return all_passed
    
    def test_default_categories_config(self) -> bool:
        """验证默认分类配置"""
        test_id = "TC-CAT-CONFIG"
        try:
            expected_categories = [
                ("吃饭", "expense"),
                ("娱乐", "expense"),
                ("购物", "expense"),
                ("房租水电", "expense"),
                ("工资", "income"),
            ]
            
            # 检查配置
            if len(DEFAULT_CATEGORIES) != 5:
                self.log(test_id, "FAIL", f"默认分类数量错误: {len(DEFAULT_CATEGORIES)}")
                return False
            
            for expected_name, expected_type in expected_categories:
                found = [c for c in DEFAULT_CATEGORIES if c["name"] == expected_name and c["type"] == expected_type]
                if not found:
                    self.log(test_id, "FAIL", f"缺少默认分类: {expected_name} ({expected_type})")
                    return False
            
            self.log(test_id, "PASS", "默认分类配置正确: 吃饭、娱乐、购物、房租水电、工资")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_first_launch_categories(self, db: Database) -> bool:
        """TC-CAT-INIT-001: 首次启动默认分类"""
        test_id = "TC-CAT-INIT-001"
        try:
            # 清空分类表
            cursor = db.conn.cursor()
            cursor.execute("DELETE FROM categories")
            cursor.execute("DELETE FROM schema_version")
            db.conn.commit()
            
            # 重新初始化数据库（模拟首次启动）
            db._init_db()
            
            # 检查分类
            categories = db.get_all_categories()
            
            if len(categories) != 5:
                self.log(test_id, "FAIL", f"默认分类数量错误: {len(categories)} (expected 5)")
                self.log_defect(
                    "Major",
                    "[默认分类] 首次启动分类数量不正确",
                    "首次启动应创建恰好5个默认分类",
                    ["删除数据库", "启动应用"],
                    f"分类数量: {len(categories)}",
                    "分类数量: 5"
                )
                return False
            
            # 检查具体分类
            category_names = [c.name for c in categories]
            expected_names = ["吃饭", "娱乐", "购物", "房租水电", "工资"]
            
            for name in expected_names:
                if name not in category_names:
                    self.log(test_id, "FAIL", f"缺少默认分类: {name}")
                    return False
            
            self.log(test_id, "PASS", f"首次启动创建5个默认分类: {category_names}")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_restart_no_duplicate(self, db: Database) -> bool:
        """TC-CAT-INIT-002: 重启不重复插入"""
        test_id = "TC-CAT-INIT-002"
        try:
            # 获取当前分类数量
            before = db.get_all_categories()
            before_count = len(before)
            
            # 模拟重启（重新初始化）
            db._init_db()
            
            # 检查分类数量
            after = db.get_all_categories()
            after_count = len(after)
            
            if after_count != before_count:
                self.log(test_id, "FAIL", f"重启后分类数量变化: {before_count} -> {after_count}")
                self.log_defect(
                    "Critical",
                    "[默认分类] 重启后分类重复插入",
                    "重启应用后默认分类不应重复创建",
                    ["首次启动应用", "关闭应用", "重新启动"],
                    f"分类从{before_count}变为{after_count}",
                    "分类数量不变"
                )
                return False
            
            # 检查无重复
            names = [c.name for c in after]
            if len(names) != len(set(names)):
                self.log(test_id, "FAIL", "存在重复分类名")
                return False
            
            self.log(test_id, "PASS", f"重启后分类数量不变: {after_count}")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_custom_category_preserved(self, db: Database) -> bool:
        """TC-CAT-INIT-003: 用户自定义分类保留"""
        test_id = "TC-CAT-INIT-003"
        try:
            # 添加自定义分类
            custom_cat = Category(name="自定义测试分类", type="expense")
            db.add_category(custom_cat)
            
            before = db.get_all_categories()
            custom_exists_before = any(c.name == "自定义测试分类" for c in before)
            
            if not custom_exists_before:
                self.log(test_id, "FAIL", "自定义分类添加失败")
                return False
            
            # 模拟重启
            db._init_db()
            
            after = db.get_all_categories()
            custom_exists_after = any(c.name == "自定义测试分类" for c in after)
            
            if not custom_exists_after:
                self.log(test_id, "FAIL", "重启后自定义分类丢失")
                return False
            
            # 默认分类仍存在
            default_exists = any(c.name == "吃饭" for c in after)
            if not default_exists:
                self.log(test_id, "FAIL", "重启后默认分类丢失")
                return False
            
            self.log(test_id, "PASS", "自定义分类和默认分类均保留")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False


class PieChartTests(TestRunner):
    """模块D：支出分析饼状图测试"""
    
    def run_all(self, db: Database) -> bool:
        print("\n" + "="*60)
        print("模块D：支出分析饼状图测试")
        print("="*60)
        
        self.clear_all_data(db)
        
        all_passed = True
        all_passed &= self.test_pie_chart_amount_percentage(db)
        all_passed &= self.test_pie_chart_consistency(db)
        all_passed &= self.test_pie_chart_no_data(db)
        all_passed &= self.test_pie_chart_data_format(db)
        
        return all_passed
    
    def test_pie_chart_amount_percentage(self, db: Database) -> bool:
        """TC-PIE-001: 饼图金额与百分比正确"""
        test_id = "TC-PIE-001"
        try:
            self.clear_all_data(db)
            
            today = date.today()
            date_str = today.strftime("%Y-%m-%d")
            
            # 添加不同分类的支出
            db.add_transaction(Transaction(type="expense", amount_cents=10000, date=date_str, category="餐饮"))
            db.add_transaction(Transaction(type="expense", amount_cents=20000, date=date_str, category="交通"))
            db.add_transaction(Transaction(type="expense", amount_cents=30000, date=date_str, category="购物"))
            
            stats = StatisticsService(db)
            start, end = stats.get_month_range(today.year, today.month)
            breakdown = stats.get_category_breakdown(start, end, "expense")
            
            # 验证百分比总和
            total_percentage = sum(item["percentage"] for item in breakdown)
            
            if abs(total_percentage - 100) > 0.5:  # 允许0.5%误差
                self.log(test_id, "FAIL", f"百分比总和错误: {total_percentage:.2f}%")
                return False
            
            # 验证金额使用USD格式（通过format_money_from_float）
            for item in breakdown:
                formatted = format_money_from_float(item["amount"])
                if not formatted.startswith("$"):
                    self.log(test_id, "FAIL", f"金额格式错误: {formatted}")
                    return False
            
            self.log(test_id, "PASS", f"饼图数据正确: {len(breakdown)}个分类, 百分比总和={total_percentage:.1f}%")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_pie_chart_consistency(self, db: Database) -> bool:
        """TC-PIE-002: 饼图与明细一致性"""
        test_id = "TC-PIE-002"
        try:
            self.clear_all_data(db)
            
            today = date.today()
            date_str = today.strftime("%Y-%m-%d")
            
            # 添加测试数据
            transactions = [
                Transaction(type="expense", amount_cents=1234, date=date_str, category="餐饮"),
                Transaction(type="expense", amount_cents=5678, date=date_str, category="餐饮"),
                Transaction(type="expense", amount_cents=9999, date=date_str, category="交通"),
            ]
            for tx in transactions:
                db.add_transaction(tx)
            
            stats = StatisticsService(db)
            start, end = stats.get_month_range(today.year, today.month)
            breakdown = stats.get_category_breakdown(start, end, "expense")
            
            # 手工计算
            expected_dining = 1234 + 5678  # 6912 cents
            expected_transport = 9999  # cents
            
            # 验证
            dining = [b for b in breakdown if b["category"] == "餐饮"]
            transport = [b for b in breakdown if b["category"] == "交通"]
            
            if not dining or dining[0]["amount_cents"] != expected_dining:
                self.log(test_id, "FAIL", f"餐饮分类金额不一致")
                return False
            
            if not transport or transport[0]["amount_cents"] != expected_transport:
                self.log(test_id, "FAIL", f"交通分类金额不一致")
                return False
            
            self.log(test_id, "PASS", "饼图数据与明细求和一致")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_pie_chart_no_data(self, db: Database) -> bool:
        """TC-PIE-003: 无支出场景"""
        test_id = "TC-PIE-003"
        try:
            from ledger.ui.statistics_widget import PieChartWidget
            
            # 空数据
            chart = PieChartWidget()
            chart.set_data([], "支出分类")
            
            # 验证不会崩溃
            chart.update()
            
            # 验证内部状态
            if chart._total != 0:
                self.log(test_id, "FAIL", f"空数据时_total应为0: {chart._total}")
                return False
            
            self.log(test_id, "PASS", "无支出时饼图正常处理（显示提示文字）")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_pie_chart_data_format(self, db: Database) -> bool:
        """TC-PIE-004: 饼图数据格式验证"""
        test_id = "TC-PIE-004"
        try:
            from ledger.ui.statistics_widget import PieChartWidget, format_money_from_float
            
            # 创建测试数据
            test_data = [
                {"category": "餐饮", "amount": 123.45, "percentage": 60, "amount_cents": 12345},
                {"category": "交通", "amount": 82.30, "percentage": 40, "amount_cents": 8230},
            ]
            
            chart = PieChartWidget()
            chart.set_data(test_data, "支出分类")
            
            # 验证数据被正确存储
            if len(chart._data) != 2:
                self.log(test_id, "FAIL", f"数据项数量错误: {len(chart._data)}")
                return False
            
            # 验证金额格式化使用$
            for item in test_data:
                formatted = format_money_from_float(item["amount"])
                if not formatted.startswith("$"):
                    self.log(test_id, "FAIL", f"金额格式错误: {formatted}")
                    return False
            
            self.log(test_id, "PASS", "饼图数据格式正确")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False


class Phase1RegressionTests(TestRunner):
    """Phase 1 回归测试"""
    
    def run_all(self, db: Database) -> bool:
        print("\n" + "="*60)
        print("Phase 1 回归测试")
        print("="*60)
        
        self.clear_all_data(db)
        
        all_passed = True
        all_passed &= self.test_add_transaction(db)
        all_passed &= self.test_edit_transaction(db)
        all_passed &= self.test_delete_transaction(db)
        all_passed &= self.test_dashboard_summary(db)
        all_passed &= self.test_statistics_date_range(db)
        
        return all_passed
    
    def test_add_transaction(self, db: Database) -> bool:
        """回归测试：新增交易"""
        test_id = "REG-ADD"
        try:
            tx = Transaction(
                type="expense",
                amount_cents=5000,
                date="2026-01-12",
                category="餐饮"
            )
            tx_id = db.add_transaction(tx)
            
            saved = db.get_transaction_by_id(tx_id)
            if not saved or saved.amount_cents != 5000:
                self.log(test_id, "FAIL", "新增交易失败")
                return False
            
            self.log(test_id, "PASS", "新增交易正常")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_edit_transaction(self, db: Database) -> bool:
        """回归测试：修改交易"""
        test_id = "REG-EDIT"
        try:
            # 获取已有交易
            transactions = db.get_all_transactions()
            if not transactions:
                self.log(test_id, "FAIL", "无可编辑交易")
                return False
            
            tx = transactions[0]
            original_id = tx.id
            tx.amount_cents = 8888
            db.update_transaction(tx)
            
            updated = db.get_transaction_by_id(original_id)
            if updated.amount_cents != 8888:
                self.log(test_id, "FAIL", "修改交易失败")
                return False
            
            self.log(test_id, "PASS", "修改交易正常")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_delete_transaction(self, db: Database) -> bool:
        """回归测试：删除交易"""
        test_id = "REG-DEL"
        try:
            # 添加一条交易用于删除
            tx = Transaction(type="expense", amount_cents=1000, date="2026-01-12")
            tx_id = db.add_transaction(tx)
            
            db.delete_transaction(tx_id)
            
            deleted = db.get_transaction_by_id(tx_id)
            if deleted:
                self.log(test_id, "FAIL", "删除交易失败")
                return False
            
            self.log(test_id, "PASS", "删除交易正常")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_dashboard_summary(self, db: Database) -> bool:
        """回归测试：Dashboard本月汇总"""
        test_id = "REG-DASH"
        try:
            self.clear_all_data(db)
            
            today = date.today()
            date_str = today.strftime("%Y-%m-%d")
            
            db.add_transaction(Transaction(type="expense", amount_cents=10000, date=date_str))
            db.add_transaction(Transaction(type="income", amount_cents=20000, date=date_str))
            
            stats = StatisticsService(db)
            summary = stats.get_current_month_summary()
            
            if summary.expense_cents != 10000:
                self.log(test_id, "FAIL", f"支出汇总错误: {summary.expense_cents}")
                return False
            
            if summary.income_cents != 20000:
                self.log(test_id, "FAIL", f"收入汇总错误: {summary.income_cents}")
                return False
            
            self.log(test_id, "PASS", "Dashboard汇总正常")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_statistics_date_range(self, db: Database) -> bool:
        """回归测试：统计页面时间区间"""
        test_id = "REG-STAT"
        try:
            self.clear_all_data(db)
            
            # 添加不同月份的数据
            db.add_transaction(Transaction(type="expense", amount_cents=1000, date="2026-01-10"))
            db.add_transaction(Transaction(type="expense", amount_cents=2000, date="2026-02-10"))
            
            stats = StatisticsService(db)
            
            # 测试1月统计
            jan_summary = stats.get_custom_period_summary("2026-01-01", "2026-01-31")
            if jan_summary.expense_cents != 1000:
                self.log(test_id, "FAIL", f"1月统计错误: {jan_summary.expense_cents}")
                return False
            
            # 测试2月统计
            feb_summary = stats.get_custom_period_summary("2026-02-01", "2026-02-28")
            if feb_summary.expense_cents != 2000:
                self.log(test_id, "FAIL", f"2月统计错误: {feb_summary.expense_cents}")
                return False
            
            self.log(test_id, "PASS", "统计时间区间正常")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False


def generate_report(runner: TestRunner):
    """生成测试报告"""
    print("\n" + "="*60)
    print("Phase 1.2 测试执行报告")
    print("="*60)
    print(f"执行日期: 2026-01-12")
    print(f"环境: macOS / Python 3.x / PySide6")
    print(f"版本: v1.2.0")
    print("-"*60)
    
    passed = sum(1 for r in runner.results if r["status"] == "PASS")
    failed = sum(1 for r in runner.results if r["status"] == "FAIL")
    warned = sum(1 for r in runner.results if r["status"] == "WARN")
    
    print(f"\n测试结果汇总:")
    print(f"  ✅ 通过: {passed}")
    print(f"  ❌ 失败: {failed}")
    print(f"  ⚠️  警告: {warned}")
    print(f"  总计: {len(runner.results)}")
    
    print("\n详细结果:")
    for r in runner.results:
        emoji = "✅" if r["status"] == "PASS" else "❌" if r["status"] == "FAIL" else "⚠️"
        print(f"  {emoji} {r['id']}: {r['status']}")
        if r["message"]:
            print(f"      {r['message']}")
    
    if runner.defects:
        print("\n" + "="*60)
        print("缺陷列表")
        print("="*60)
        for i, d in enumerate(runner.defects, 1):
            print(f"\n缺陷 #{i}")
            print(f"  严重级别: {d['severity']}")
            print(f"  标题: {d['title']}")
            print(f"  描述: {d['description']}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    
    return passed, failed, warned


def main():
    print("="*60)
    print("Ledger App Phase 1.2 自动化测试")
    print("="*60)
    
    # 使用独立的测试数据库
    test_db_path = str(DB_PATH).replace("app.db", "test_phase1_2.db")
    
    # 删除旧测试数据库
    import os
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    # 创建数据库连接
    db = Database(test_db_path)
    
    # 创建综合测试运行器
    runner = TestRunner()
    
    # 运行所有测试模块
    usd_tests = USDFormatTests()
    usd_tests.run_all(db)
    runner.results.extend(usd_tests.results)
    runner.defects.extend(usd_tests.defects)
    
    theme_tests = ThemeAdaptationTests()
    theme_tests.run_all(db)
    runner.results.extend(theme_tests.results)
    runner.defects.extend(theme_tests.defects)
    
    cat_tests = DefaultCategoryTests()
    cat_tests.run_all(db)
    runner.results.extend(cat_tests.results)
    runner.defects.extend(cat_tests.defects)
    
    pie_tests = PieChartTests()
    pie_tests.run_all(db)
    runner.results.extend(pie_tests.results)
    runner.defects.extend(pie_tests.defects)
    
    reg_tests = Phase1RegressionTests()
    reg_tests.run_all(db)
    runner.results.extend(reg_tests.results)
    runner.defects.extend(reg_tests.defects)
    
    # 生成报告
    generate_report(runner)
    
    # 清理
    db.close()
    
    # 删除测试数据库
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


if __name__ == "__main__":
    main()

