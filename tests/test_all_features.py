"""
Ledger App - 完整功能测试套件
涵盖所有阶段功能的综合测试
日期：2026-01-12
"""

import sys
import os
import tempfile
import shutil
from datetime import date, datetime, timedelta
from typing import Dict, Any, List

# Add the 'src' directory to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, os.path.join(project_root, 'src'))

from ledger.db.database import Database
from ledger.models.transaction import Transaction
from ledger.models.category import Category
from ledger.models.account import Account
from ledger.services.statistics_service import StatisticsService
from ledger.settings import (
    format_money, format_money_from_float, 
    CURRENCY_SYMBOL, CURRENCY_CODE, DEFAULT_CATEGORIES
)
from ledger.ui.theme import COLOR_INCOME, COLOR_EXPENSE, get_text_color


class ComprehensiveTestSuite:
    """完整功能测试套件"""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.temp_dir = None
        self.db_path = None
        self.db = None
        self.stats_service = None
        
    def setup(self):
        """测试环境准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_ledger.db")
        self.db = Database(self.db_path)
        self.stats_service = StatisticsService(self.db)
        
        # 获取已初始化的分类和账户
        self.categories = {c.name: c for c in self.db.get_all_categories()}
        
        # 添加测试账户
        existing_acc = {a.name for a in self.db.get_all_accounts()}
        if "现金" not in existing_acc:
            self.db.add_account(Account(name="现金", type="cash"))
        if "银行卡" not in existing_acc:
            self.db.add_account(Account(name="银行卡", type="debit"))
        
        self.accounts = {a.name: a for a in self.db.get_all_accounts()}
        self.categories = {c.name: c for c in self.db.get_all_categories()}
        
    def teardown(self):
        """清理测试环境"""
        if self.db:
            self.db.close()
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
            
    def reset_db(self):
        """重置交易数据"""
        if self.db and self.db.conn:
            cursor = self.db.conn.cursor()
            cursor.execute("DELETE FROM transactions")
            self.db.conn.commit()
            
    def add_expense(self, amount_cents: int, date_str: str, category: str = "吃饭") -> int:
        """添加支出"""
        cat = self.categories.get(category)
        acc = self.accounts.get("现金")
        tx = Transaction(
            type="expense", amount_cents=amount_cents, date=date_str,
            category=category, account="现金", note="测试",
            category_id=cat.id if cat else None,
            account_id=acc.id if acc else None
        )
        return self.db.add_transaction(tx)
    
    def add_income(self, amount_cents: int, date_str: str, category: str = "工资") -> int:
        """添加收入"""
        cat = self.categories.get(category)
        acc = self.accounts.get("银行卡")
        tx = Transaction(
            type="income", amount_cents=amount_cents, date=date_str,
            category=category, account="银行卡", note="测试",
            category_id=cat.id if cat else None,
            account_id=acc.id if acc else None
        )
        return self.db.add_transaction(tx)
    
    def record_result(self, phase: str, test_id: str, name: str, passed: bool, 
                      details: str = "", severity: str = "Major"):
        """记录测试结果"""
        status = "PASS" if passed else "FAIL"
        self.results.append({
            "phase": phase,
            "id": test_id, 
            "name": name, 
            "status": status,
            "passed": passed, 
            "details": details, 
            "severity": severity
        })
        icon = "✅" if passed else "❌"
        print(f"    {icon} {test_id}: {name}")
        if not passed and details:
            print(f"        ⚠️ {details}")

    # ==========================================================
    # Phase 0: 基础功能
    # ==========================================================
    
    def test_phase0_database_init(self):
        """数据库初始化"""
        errors = []
        
        # 检查数据库连接
        if self.db.conn is None:
            errors.append("数据库连接失败")
        
        # 检查表存在
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ["transactions", "categories", "accounts", "schema_version"]
        for table in required_tables:
            if table not in tables:
                errors.append(f"缺少表: {table}")
        
        self.record_result("Phase0", "P0-001", "数据库初始化",
                          len(errors) == 0, "; ".join(errors), "Blocker")
    
    def test_phase0_transaction_crud(self):
        """交易CRUD操作"""
        self.reset_db()
        errors = []
        
        # Create
        tx_id = self.add_expense(1000, "2026-01-10", "吃饭")
        if tx_id is None or tx_id <= 0:
            errors.append("新增交易失败")
        
        # Read
        tx = self.db.get_transaction_by_id(tx_id)
        if tx is None:
            errors.append("读取交易失败")
        elif tx.amount_cents != 1000:
            errors.append(f"金额不正确: {tx.amount_cents}")
        
        # Update
        tx.amount_cents = 2000
        self.db.update_transaction(tx)
        tx_updated = self.db.get_transaction_by_id(tx_id)
        if tx_updated.amount_cents != 2000:
            errors.append("更新交易失败")
        
        # Delete
        self.db.delete_transaction(tx_id)
        tx_deleted = self.db.get_transaction_by_id(tx_id)
        if tx_deleted is not None:
            errors.append("删除交易失败")
        
        self.record_result("Phase0", "P0-002", "交易CRUD操作",
                          len(errors) == 0, "; ".join(errors), "Blocker")
    
    def test_phase0_data_persistence(self):
        """数据持久化"""
        self.reset_db()
        errors = []
        
        # 添加数据
        self.add_expense(5000, "2026-01-10")
        
        # 关闭并重新打开数据库
        self.db.close()
        self.db = Database(self.db_path)
        self.stats_service = StatisticsService(self.db)
        
        # 验证数据仍存在
        txs = self.db.get_all_transactions()
        if len(txs) != 1:
            errors.append(f"数据持久化失败，期望1条，实际{len(txs)}条")
        
        self.record_result("Phase0", "P0-003", "数据持久化",
                          len(errors) == 0, "; ".join(errors), "Blocker")

    # ==========================================================
    # Phase 1: 编辑删除、分类账户管理、Dashboard、统计
    # ==========================================================
    
    def test_phase1_category_crud(self):
        """分类CRUD"""
        errors = []
        
        # 检查默认分类已存在
        cats = self.db.get_all_categories()
        if len(cats) < 5:
            errors.append(f"默认分类不足，期望>=5，实际{len(cats)}")
        
        # 添加新分类
        try:
            new_cat = Category(name="测试分类_" + str(datetime.now().timestamp()), type="expense")
            cat_id = self.db.add_category(new_cat)
            if cat_id <= 0:
                errors.append("添加分类失败")
            
            # 删除
            self.db.delete_category(cat_id)
        except Exception as e:
            errors.append(f"分类操作异常: {e}")
        
        self.record_result("Phase1", "P1-001", "分类CRUD",
                          len(errors) == 0, "; ".join(errors), "Critical")
    
    def test_phase1_account_crud(self):
        """账户CRUD"""
        errors = []
        
        # 添加新账户
        try:
            new_acc = Account(name="测试账户_" + str(datetime.now().timestamp()), type="cash")
            acc_id = self.db.add_account(new_acc)
            if acc_id <= 0:
                errors.append("添加账户失败")
            
            # 删除
            self.db.delete_account(acc_id)
        except Exception as e:
            errors.append(f"账户操作异常: {e}")
        
        self.record_result("Phase1", "P1-002", "账户CRUD",
                          len(errors) == 0, "; ".join(errors), "Critical")
    
    def test_phase1_dashboard_summary(self):
        """Dashboard汇总"""
        self.reset_db()
        errors = []
        
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        
        self.add_expense(10000, today_str)  # $100
        self.add_income(50000, today_str)   # $500
        
        # 本月汇总
        summary = self.stats_service.get_current_month_summary()
        
        if summary.expense != 100.0:
            errors.append(f"本月支出应为100.0，实际{summary.expense}")
        if summary.income != 500.0:
            errors.append(f"本月收入应为500.0，实际{summary.income}")
        if summary.balance != 400.0:
            errors.append(f"本月结余应为400.0，实际{summary.balance}")
        
        self.record_result("Phase1", "P1-003", "Dashboard汇总",
                          len(errors) == 0, "; ".join(errors), "Blocker")
    
    def test_phase1_statistics_category_breakdown(self):
        """统计分类明细"""
        self.reset_db()
        errors = []
        
        self.add_expense(10000, "2026-01-05", "吃饭")
        self.add_expense(20000, "2026-01-05", "交通")
        self.add_expense(30000, "2026-01-05", "吃饭")  # 吃饭合计$400
        
        breakdown = self.stats_service.get_category_breakdown("2026-01-01", "2026-01-31", "expense")
        
        # 吃饭应为最多
        if not breakdown or breakdown[0]["category"] != "吃饭":
            errors.append("分类排序不正确")
        
        # 验证金额
        food_item = next((x for x in breakdown if x["category"] == "吃饭"), None)
        if food_item is None or food_item["amount"] != 400.0:
            errors.append(f"吃饭金额应为400.0")
        
        self.record_result("Phase1", "P1-004", "统计分类明细",
                          len(errors) == 0, "; ".join(errors), "Critical")

    # ==========================================================
    # Phase 1.2: 货币显示、主题适配、默认分类
    # ==========================================================
    
    def test_phase1_2_currency_format(self):
        """货币格式化"""
        errors = []
        
        # 检查货币符号
        if CURRENCY_SYMBOL != "$":
            errors.append(f"货币符号应为$，实际{CURRENCY_SYMBOL}")
        
        if CURRENCY_CODE != "USD":
            errors.append(f"货币代码应为USD，实际{CURRENCY_CODE}")
        
        # 测试格式化函数
        result1 = format_money(123456)  # 1234.56分 = $1,234.56
        if "$1,234.56" not in result1:
            errors.append(f"format_money(123456) 应包含 $1,234.56，实际{result1}")
        
        result2 = format_money_from_float(1234.56)
        if "$1,234.56" not in result2:
            errors.append(f"format_money_from_float(1234.56) 应包含 $1,234.56，实际{result2}")
        
        self.record_result("Phase1.2", "P1.2-001", "货币格式化",
                          len(errors) == 0, "; ".join(errors), "Blocker")
    
    def test_phase1_2_default_categories(self):
        """默认分类初始化"""
        errors = []
        
        # 检查DEFAULT_CATEGORIES配置
        if len(DEFAULT_CATEGORIES) < 5:
            errors.append(f"DEFAULT_CATEGORIES 应>=5，实际{len(DEFAULT_CATEGORIES)}")
        
        # 检查数据库中的分类
        cats = self.db.get_all_categories()
        cat_names = {c.name for c in cats}
        
        for cat_config in DEFAULT_CATEGORIES:
            if cat_config["name"] not in cat_names:
                errors.append(f"默认分类 {cat_config['name']} 未创建")
        
        self.record_result("Phase1.2", "P1.2-002", "默认分类初始化",
                          len(errors) == 0, "; ".join(errors), "Critical")
    
    def test_phase1_2_theme_colors(self):
        """主题颜色"""
        errors = []
        
        # 检查颜色定义
        if not COLOR_INCOME:
            errors.append("COLOR_INCOME 未定义")
        if not COLOR_EXPENSE:
            errors.append("COLOR_EXPENSE 未定义")
        if COLOR_INCOME == COLOR_EXPENSE:
            errors.append("收入和支出颜色不应相同")
        
        # 检查动态颜色函数
        try:
            color = get_text_color()
            if color is None:
                errors.append("get_text_color() 返回None")
        except Exception as e:
            errors.append(f"get_text_color() 异常: {e}")
        
        self.record_result("Phase1.2", "P1.2-003", "主题颜色",
                          len(errors) == 0, "; ".join(errors), "Major")

    # ==========================================================
    # Phase 1.x: 趋势图基础功能
    # ==========================================================
    
    def test_trend_basic_daily(self):
        """趋势图按日聚合"""
        self.reset_db()
        errors = []
        
        self.add_expense(1000, "2026-01-05")
        self.add_expense(2000, "2026-01-05")  # 同日合计$30
        self.add_expense(3000, "2026-01-10")
        
        result = self.stats_service.get_trend_data("2026-01-01", "2026-01-15")
        
        if result["granularity"] != "day":
            errors.append(f"粒度应为day，实际{result['granularity']}")
        
        if len(result["data"]) != 15:
            errors.append(f"应有15天，实际{len(result['data'])}天")
        
        data_map = {item["label"]: item for item in result["data"]}
        if data_map.get("2026-01-05", {}).get("expense") != 30.0:
            errors.append("01-05支出应为30.0")
        
        self.record_result("Phase1.x", "P1.x-001", "趋势图按日聚合",
                          len(errors) == 0, "; ".join(errors), "Blocker")
    
    def test_trend_basic_monthly(self):
        """趋势图按月聚合"""
        self.reset_db()
        errors = []
        
        self.add_expense(10000, "2025-11-15")
        self.add_expense(20000, "2025-12-10")
        self.add_expense(30000, "2026-01-05")
        
        result = self.stats_service.get_trend_data("2025-11-01", "2026-01-31")
        
        if result["granularity"] != "month":
            errors.append(f"粒度应为month，实际{result['granularity']}")
        
        if len(result["data"]) != 3:
            errors.append(f"应有3个月，实际{len(result['data'])}个")
        
        self.record_result("Phase1.x", "P1.x-002", "趋势图按月聚合",
                          len(errors) == 0, "; ".join(errors), "Blocker")
    
    def test_trend_continuity(self):
        """趋势图连续性"""
        self.reset_db()
        errors = []
        
        self.add_expense(1000, "2026-01-01")
        self.add_expense(2000, "2026-01-10")
        
        result = self.stats_service.get_trend_data("2026-01-01", "2026-01-10")
        
        # 检查所有日期都存在
        expected_dates = [(date(2026, 1, 1) + timedelta(days=i)).strftime("%Y-%m-%d") 
                         for i in range(10)]
        actual_dates = [item["label"] for item in result["data"]]
        
        if actual_dates != expected_dates:
            errors.append("日期不连续")
        
        # 检查中间日期为0
        for item in result["data"]:
            if item["label"] not in ["2026-01-01", "2026-01-10"]:
                if item["expense"] != 0.0:
                    errors.append(f"{item['label']} 应为0")
                    break
        
        self.record_result("Phase1.x", "P1.x-003", "趋势图连续性",
                          len(errors) == 0, "; ".join(errors), "Critical")

    # ==========================================================
    # Phase 1.x 增强: 趋势图高级交互
    # ==========================================================
    
    def test_trend_advanced_granularity(self):
        """高级趋势图粒度选择"""
        self.reset_db()
        errors = []
        
        self.add_expense(1000, "2026-01-05")
        self.add_expense(2000, "2026-01-12")
        self.add_income(5000, "2026-01-08")
        
        # 日粒度
        result_day = self.stats_service.get_trend_data_advanced("2026-01-01", "2026-01-15", "day")
        if result_day["granularity"] != "day":
            errors.append("日粒度失败")
        
        # 周粒度
        result_week = self.stats_service.get_trend_data_advanced("2026-01-01", "2026-01-31", "week")
        if result_week["granularity"] != "week":
            errors.append("周粒度失败")
        if not any("-W" in item["label"] for item in result_week["data"]):
            errors.append("周标签格式错误")
        
        # 月粒度
        result_month = self.stats_service.get_trend_data_advanced("2025-01-01", "2026-01-31", "month")
        if result_month["granularity"] != "month":
            errors.append("月粒度失败")
        
        # 年粒度
        result_year = self.stats_service.get_trend_data_advanced("2024-01-01", "2026-12-31", "year")
        if result_year["granularity"] != "year":
            errors.append("年粒度失败")
        
        self.record_result("Phase1.x+", "P1.x+-001", "高级趋势图粒度选择",
                          len(errors) == 0, "; ".join(errors), "Blocker")
    
    def test_trend_advanced_category_filter(self):
        """高级趋势图分类筛选"""
        self.reset_db()
        errors = []
        
        self.add_expense(1000, "2026-01-05", "吃饭")
        self.add_expense(2000, "2026-01-05", "交通")
        self.add_income(5000, "2026-01-05")
        
        # 筛选吃饭
        result = self.stats_service.get_trend_data_advanced("2026-01-01", "2026-01-10", "day", "吃饭")
        
        data_map = {item["label"]: item for item in result["data"]}
        
        # 支出应只有吃饭的$10
        if data_map.get("2026-01-05", {}).get("expense") != 10.0:
            errors.append(f"筛选吃饭后支出应为10.0，实际{data_map.get('2026-01-05', {}).get('expense')}")
        
        # 收入不受影响
        if data_map.get("2026-01-05", {}).get("income") != 50.0:
            errors.append("分类筛选不应影响收入")
        
        self.record_result("Phase1.x+", "P1.x+-002", "高级趋势图分类筛选",
                          len(errors) == 0, "; ".join(errors), "Critical")
    
    def test_trend_advanced_week_iso(self):
        """周粒度ISO规则"""
        self.reset_db()
        errors = []
        
        # 2026-01-05是周一，2026-01-11是周日 -> 同属W02
        self.add_expense(1000, "2026-01-05")  # W02
        self.add_expense(2000, "2026-01-07")  # W02
        self.add_expense(3000, "2026-01-12")  # W03 (周一)
        
        result = self.stats_service.get_trend_data_advanced("2026-01-01", "2026-01-18", "week")
        
        data_map = {item["label"]: item for item in result["data"]}
        
        # W02应聚合为$30
        w02_expense = data_map.get("2026-W02", {}).get("expense", 0)
        if w02_expense != 30.0:
            errors.append(f"W02支出应为30.0，实际{w02_expense}")
        
        # W03应为$30
        w03_expense = data_map.get("2026-W03", {}).get("expense", 0)
        if w03_expense != 30.0:
            errors.append(f"W03支出应为30.0，实际{w03_expense}")
        
        self.record_result("Phase1.x+", "P1.x+-003", "周粒度ISO规则",
                          len(errors) == 0, "; ".join(errors), "Critical")

    # ==========================================================
    # 综合测试
    # ==========================================================
    
    def test_data_consistency(self):
        """数据一致性"""
        self.reset_db()
        errors = []
        
        # 添加测试数据
        for i in range(1, 11):
            self.add_expense(i * 1000, f"2026-01-{i:02d}", "吃饭")
            if i % 3 == 0:
                self.add_income(i * 2000, f"2026-01-{i:02d}")
        
        start, end = "2026-01-01", "2026-01-31"
        
        # 从趋势图计算
        trend = self.stats_service.get_trend_data(start, end)
        trend_expense = sum(item["expense"] for item in trend["data"])
        trend_income = sum(item["income"] for item in trend["data"])
        
        # 从汇总API获取
        summary = self.stats_service.get_custom_period_summary(start, end)
        
        # 比较
        if abs(trend_expense - summary.expense) > 0.01:
            errors.append(f"支出不一致: 趋势={trend_expense}, 汇总={summary.expense}")
        
        if abs(trend_income - summary.income) > 0.01:
            errors.append(f"收入不一致: 趋势={trend_income}, 汇总={summary.income}")
        
        self.record_result("综合", "INT-001", "数据一致性",
                          len(errors) == 0, "; ".join(errors), "Blocker")
    
    def test_data_sync_after_changes(self):
        """数据变更同步"""
        self.reset_db()
        errors = []
        
        # 添加
        tx_id = self.add_expense(5000, "2026-01-05")
        result1 = self.stats_service.get_trend_data_advanced("2026-01-01", "2026-01-10", "day")
        data1 = {item["label"]: item for item in result1["data"]}
        
        if data1.get("2026-01-05", {}).get("expense") != 50.0:
            errors.append("新增后数据不正确")
        
        # 修改
        tx = self.db.get_transaction_by_id(tx_id)
        tx.amount_cents = 10000
        self.db.update_transaction(tx)
        
        result2 = self.stats_service.get_trend_data_advanced("2026-01-01", "2026-01-10", "day")
        data2 = {item["label"]: item for item in result2["data"]}
        
        if data2.get("2026-01-05", {}).get("expense") != 100.0:
            errors.append("修改后数据不正确")
        
        # 删除
        self.db.delete_transaction(tx_id)
        
        result3 = self.stats_service.get_trend_data_advanced("2026-01-01", "2026-01-10", "day")
        data3 = {item["label"]: item for item in result3["data"]}
        
        if data3.get("2026-01-05", {}).get("expense") != 0.0:
            errors.append("删除后数据不正确")
        
        self.record_result("综合", "INT-002", "数据变更同步",
                          len(errors) == 0, "; ".join(errors), "Major")

    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 70)
        print("🧪 Ledger App - 完整功能测试套件")
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        try:
            self.setup()
            
            print("\n📦 Phase 0: 基础功能")
            print("-" * 50)
            self.test_phase0_database_init()
            self.test_phase0_transaction_crud()
            self.test_phase0_data_persistence()
            
            # 重新设置（因为上面关闭了数据库）
            self.categories = {c.name: c for c in self.db.get_all_categories()}
            self.accounts = {a.name: a for a in self.db.get_all_accounts()}
            
            print("\n📦 Phase 1: 编辑删除、分类账户管理、Dashboard、统计")
            print("-" * 50)
            self.test_phase1_category_crud()
            self.test_phase1_account_crud()
            self.test_phase1_dashboard_summary()
            self.test_phase1_statistics_category_breakdown()
            
            print("\n📦 Phase 1.2: 货币显示、主题适配、默认分类")
            print("-" * 50)
            self.test_phase1_2_currency_format()
            self.test_phase1_2_default_categories()
            self.test_phase1_2_theme_colors()
            
            print("\n📦 Phase 1.x: 趋势图基础功能")
            print("-" * 50)
            self.test_trend_basic_daily()
            self.test_trend_basic_monthly()
            self.test_trend_continuity()
            
            print("\n📦 Phase 1.x+: 趋势图高级交互")
            print("-" * 50)
            self.test_trend_advanced_granularity()
            self.test_trend_advanced_category_filter()
            self.test_trend_advanced_week_iso()
            
            print("\n📦 综合测试")
            print("-" * 50)
            self.test_data_consistency()
            self.test_data_sync_after_changes()
            
        finally:
            self.teardown()
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        # 按阶段统计
        phase_stats = {}
        for r in self.results:
            phase = r["phase"]
            if phase not in phase_stats:
                phase_stats[phase] = {"total": 0, "passed": 0}
            phase_stats[phase]["total"] += 1
            if r["passed"]:
                phase_stats[phase]["passed"] += 1
        
        # 按严重级别统计失败
        failures_by_severity = {}
        for r in self.results:
            if not r["passed"]:
                sev = r["severity"]
                failures_by_severity[sev] = failures_by_severity.get(sev, 0) + 1
        
        print("\n" + "=" * 70)
        print("📊 测试结果汇总")
        print("=" * 70)
        print(f"\n总测试数: {total}")
        print(f"通过: {passed} ✅")
        print(f"失败: {failed} ❌")
        print(f"通过率: {passed/total*100:.1f}%")
        
        print("\n按阶段统计:")
        for phase, stats in phase_stats.items():
            rate = stats["passed"] / stats["total"] * 100
            status = "✅" if stats["passed"] == stats["total"] else "⚠️"
            print(f"  {status} {phase}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")
        
        if failures_by_severity:
            print("\n失败分布:")
            for sev, count in sorted(failures_by_severity.items()):
                print(f"  - {sev}: {count}")
        
        if failed > 0:
            print("\n❌ 失败用例:")
            for r in self.results:
                if not r["passed"]:
                    print(f"  [{r['severity']}] {r['id']}: {r['name']}")
                    if r["details"]:
                        print(f"    ⚠️ {r['details']}")
        
        # QA结论
        print("\n" + "=" * 70)
        print("🎯 QA 最终结论")
        print("=" * 70)
        
        blockers = failures_by_severity.get("Blocker", 0)
        criticals = failures_by_severity.get("Critical", 0)
        
        if blockers > 0:
            print("\n🚫 存在 Blocker 级别缺陷")
            print("   状态: 不可发布")
            qa_conclusion = "BLOCKED"
        elif criticals > 0:
            print("\n⚠️ 存在 Critical 级别缺陷")
            print("   状态: 有条件发布")
            qa_conclusion = "CONDITIONAL"
        elif failed > 0:
            print("\n⚠️ 存在 Major/Minor 级别缺陷")
            print("   状态: 可发布，建议后续修复")
            qa_conclusion = "PASS_WITH_ISSUES"
        else:
            print("\n✅ 所有测试通过！")
            print("   状态: 可发布")
            qa_conclusion = "PASS"
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total * 100,
            "phase_stats": phase_stats,
            "qa_conclusion": qa_conclusion,
            "results": self.results
        }


def main():
    suite = ComprehensiveTestSuite()
    report = suite.run_all_tests()
    
    # 保存测试报告
    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "TEST_REPORT_FINAL.md"
    )
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Ledger App - 完整功能测试报告\n\n")
        f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write("## 测试结果汇总\n\n")
        f.write(f"| 指标 | 结果 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| 总测试数 | {report['total']} |\n")
        f.write(f"| 通过 | {report['passed']} ✅ |\n")
        f.write(f"| 失败 | {report['failed']} ❌ |\n")
        f.write(f"| 通过率 | {report['pass_rate']:.1f}% |\n")
        f.write(f"| **QA结论** | **{report['qa_conclusion']}** |\n")
        
        f.write("\n---\n\n")
        f.write("## 按阶段统计\n\n")
        f.write("| 阶段 | 通过/总数 | 通过率 |\n")
        f.write("|------|-----------|--------|\n")
        for phase, stats in report["phase_stats"].items():
            rate = stats["passed"] / stats["total"] * 100
            status = "✅" if stats["passed"] == stats["total"] else "⚠️"
            f.write(f"| {status} {phase} | {stats['passed']}/{stats['total']} | {rate:.0f}% |\n")
        
        f.write("\n---\n\n")
        f.write("## 测试用例详情\n\n")
        f.write("| 阶段 | ID | 测试项 | 状态 | 严重级别 |\n")
        f.write("|------|-----|--------|------|----------|\n")
        for r in report["results"]:
            status = "✅ PASS" if r["passed"] else "❌ FAIL"
            f.write(f"| {r['phase']} | {r['id']} | {r['name']} | {status} | {r['severity']} |\n")
        
        f.write("\n---\n\n")
        f.write("## 功能覆盖\n\n")
        f.write("| 功能模块 | 状态 |\n")
        f.write("|----------|------|\n")
        f.write("| 数据库初始化 | ✅ |\n")
        f.write("| 交易CRUD | ✅ |\n")
        f.write("| 数据持久化 | ✅ |\n")
        f.write("| 分类管理 | ✅ |\n")
        f.write("| 账户管理 | ✅ |\n")
        f.write("| Dashboard汇总 | ✅ |\n")
        f.write("| 统计分类明细 | ✅ |\n")
        f.write("| 货币格式化 (USD) | ✅ |\n")
        f.write("| 默认分类初始化 | ✅ |\n")
        f.write("| 主题颜色适配 | ✅ |\n")
        f.write("| 趋势图按日聚合 | ✅ |\n")
        f.write("| 趋势图按月聚合 | ✅ |\n")
        f.write("| 趋势图连续性 | ✅ |\n")
        f.write("| 高级粒度选择 (日/周/月/年) | ✅ |\n")
        f.write("| 支出分类筛选 | ✅ |\n")
        f.write("| ISO周规则 | ✅ |\n")
        f.write("| 数据一致性 | ✅ |\n")
        f.write("| 数据变更同步 | ✅ |\n")
        
        f.write("\n---\n\n")
        f.write(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    print(f"\n📄 测试报告已保存至: {report_path}")
    
    return 0 if report["qa_conclusion"] in ["PASS", "PASS_WITH_ISSUES"] else 1


if __name__ == "__main__":
    sys.exit(main())

