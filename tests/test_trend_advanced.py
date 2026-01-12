"""
Ledger App - 收支趋势图高级交互功能测试
Phase 1.x - Advanced Trend Chart Test Suite
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


class AdvancedTrendTestSuite:
    """趋势图高级交互功能测试套件"""
    
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
        
        # 添加测试分类
        test_categories = [
            ("吃饭", "expense"),
            ("交通", "expense"),
            ("购物", "expense"),
            ("工资", "income"),
            ("兼职", "income"),
        ]
        existing = {c.name for c in self.db.get_all_categories()}
        for name, cat_type in test_categories:
            if name not in existing:
                try:
                    self.db.add_category(Category(name=name, type=cat_type))
                except:
                    pass
        
        # 添加账户
        existing_acc = {a.name for a in self.db.get_all_accounts()}
        if "现金" not in existing_acc:
            self.db.add_account(Account(name="现金", type="cash"))
        
        self.categories = {c.name: c for c in self.db.get_all_categories()}
        self.accounts = {a.name: a for a in self.db.get_all_accounts()}
        
    def teardown(self):
        """清理测试环境"""
        if self.db:
            self.db.close()
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)
            
    def reset_db(self):
        """重置数据库"""
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
        acc = self.accounts.get("现金")
        tx = Transaction(
            type="income", amount_cents=amount_cents, date=date_str,
            category=category, account="现金", note="测试",
            category_id=cat.id if cat else None,
            account_id=acc.id if acc else None
        )
        return self.db.add_transaction(tx)
    
    def record_result(self, test_id: str, name: str, passed: bool, 
                      details: str = "", severity: str = "Major"):
        """记录测试结果"""
        status = "PASS" if passed else "FAIL"
        self.results.append({
            "id": test_id, "name": name, "status": status,
            "passed": passed, "details": details, "severity": severity
        })
        icon = "✅" if passed else "❌"
        print(f"  {icon} {test_id}: {name} - {status}")
        if details:
            print(f"      {details}")
    
    # ==========================================================
    # 5.1 时间粒度选择
    # ==========================================================
    
    def test_grain_001_daily(self):
        """TC-GRAIN-001: 日粒度（Day）"""
        self.reset_db()
        
        # 在多个具体日期新增交易
        self.add_expense(1000, "2026-01-05")  # $10
        self.add_expense(2000, "2026-01-05")  # $20 -> 同日合计$30
        self.add_expense(3000, "2026-01-10")  # $30
        self.add_income(5000, "2026-01-08")   # $50
        
        result = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-15", "day"
        )
        
        errors = []
        
        # 检查粒度
        if result["granularity"] != "day":
            errors.append(f"粒度应为 day，实际为 {result['granularity']}")
        
        # 检查连续性（应有15天）
        if len(result["data"]) != 15:
            errors.append(f"应有15天数据点，实际 {len(result['data'])} 个")
        
        # 检查聚合正确性
        data_map = {item["label"]: item for item in result["data"]}
        
        if data_map.get("2026-01-05", {}).get("expense") != 30.0:
            errors.append(f"01-05支出应为30.0，实际为 {data_map.get('2026-01-05', {}).get('expense')}")
        
        if data_map.get("2026-01-10", {}).get("expense") != 30.0:
            errors.append(f"01-10支出应为30.0，实际为 {data_map.get('2026-01-10', {}).get('expense')}")
        
        if data_map.get("2026-01-08", {}).get("income") != 50.0:
            errors.append(f"01-08收入应为50.0，实际为 {data_map.get('2026-01-08', {}).get('income')}")
        
        # 检查无交易日为0
        if data_map.get("2026-01-03", {}).get("expense", -1) != 0.0:
            errors.append(f"01-03无交易，支出应为0")
        
        self.record_result(
            "TC-GRAIN-001", "日粒度（Day）",
            len(errors) == 0,
            "; ".join(errors) if errors else "X轴为连续日期，每天值等于当日交易总和",
            "Blocker"
        )
    
    def test_grain_002_weekly(self):
        """TC-GRAIN-002: 周粒度（Week）- ISO周"""
        self.reset_db()
        
        # 2026-01-05 是周一，2026-01-11 是周日 -> 同一周 W02
        # 2026-01-12 是周一 -> W03
        self.add_expense(1000, "2026-01-05")  # W02
        self.add_expense(2000, "2026-01-07")  # W02 -> 同周合计$30
        self.add_expense(3000, "2026-01-12")  # W03
        
        result = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-18", "week"
        )
        
        errors = []
        
        if result["granularity"] != "week":
            errors.append(f"粒度应为 week，实际为 {result['granularity']}")
        
        data_map = {item["label"]: item for item in result["data"]}
        
        # 验证ISO周格式
        if not any("W" in item["label"] for item in result["data"]):
            errors.append("周标签格式应包含 W (如 2026-W02)")
        
        # W02 应聚合为 $30
        w02_data = data_map.get("2026-W02", {})
        if w02_data.get("expense") != 30.0:
            errors.append(f"W02支出应为30.0，实际为 {w02_data.get('expense')}")
        
        # W03 应为 $30
        w03_data = data_map.get("2026-W03", {})
        if w03_data.get("expense") != 30.0:
            errors.append(f"W03支出应为30.0，实际为 {w03_data.get('expense')}")
        
        self.record_result(
            "TC-GRAIN-002", "周粒度（Week）- ISO周",
            len(errors) == 0,
            "; ".join(errors) if errors else "聚合为同一周，周定义符合ISO（周一开始）",
            "Critical"
        )
    
    def test_grain_003_monthly(self):
        """TC-GRAIN-003: 月粒度（Month）"""
        self.reset_db()
        
        # 不同月份新增交易
        self.add_expense(10000, "2025-11-15")  # $100
        self.add_expense(20000, "2025-12-10")  # $200
        self.add_expense(30000, "2026-01-05")  # $300
        self.add_income(500000, "2025-12-25")  # $5000
        
        result = self.stats_service.get_trend_data_advanced(
            "2025-11-01", "2026-01-31", "month"
        )
        
        errors = []
        
        if result["granularity"] != "month":
            errors.append(f"粒度应为 month，实际为 {result['granularity']}")
        
        # 应有3个月
        if len(result["data"]) != 3:
            errors.append(f"应有3个月数据点，实际 {len(result['data'])} 个")
        
        data_map = {item["label"]: item for item in result["data"]}
        
        if data_map.get("2025-11", {}).get("expense") != 100.0:
            errors.append(f"2025-11支出应为100.0")
        
        if data_map.get("2025-12", {}).get("expense") != 200.0:
            errors.append(f"2025-12支出应为200.0")
        
        if data_map.get("2025-12", {}).get("income") != 5000.0:
            errors.append(f"2025-12收入应为5000.0")
        
        if data_map.get("2026-01", {}).get("expense") != 300.0:
            errors.append(f"2026-01支出应为300.0")
        
        self.record_result(
            "TC-GRAIN-003", "月粒度（Month）",
            len(errors) == 0,
            "; ".join(errors) if errors else "每月一个点，金额为当月汇总",
            "Blocker"
        )
    
    def test_grain_004_yearly(self):
        """TC-GRAIN-004: 年粒度（Year）"""
        self.reset_db()
        
        # 跨年新增交易
        self.add_expense(100000, "2025-06-15")  # $1000
        self.add_expense(200000, "2025-12-10")  # $2000 -> 2025合计$3000
        self.add_expense(50000, "2026-01-05")   # $500
        self.add_income(1000000, "2025-07-01")  # $10000
        
        result = self.stats_service.get_trend_data_advanced(
            "2025-01-01", "2026-12-31", "year"
        )
        
        errors = []
        
        if result["granularity"] != "year":
            errors.append(f"粒度应为 year，实际为 {result['granularity']}")
        
        # 应有2年
        if len(result["data"]) != 2:
            errors.append(f"应有2年数据点，实际 {len(result['data'])} 个")
        
        data_map = {item["label"]: item for item in result["data"]}
        
        if data_map.get("2025", {}).get("expense") != 3000.0:
            errors.append(f"2025支出应为3000.0，实际为 {data_map.get('2025', {}).get('expense')}")
        
        if data_map.get("2025", {}).get("income") != 10000.0:
            errors.append(f"2025收入应为10000.0")
        
        if data_map.get("2026", {}).get("expense") != 500.0:
            errors.append(f"2026支出应为500.0")
        
        self.record_result(
            "TC-GRAIN-004", "年粒度（Year）",
            len(errors) == 0,
            "; ".join(errors) if errors else "每年一个点，汇总正确",
            "Blocker"
        )
    
    # ==========================================================
    # 5.2 连续性与0值测试
    # ==========================================================
    
    def test_cont_001_zero_values(self):
        """TC-CONT-001: 无交易时间点显示为0"""
        self.reset_db()
        
        # 只在首尾有交易
        self.add_expense(1000, "2026-01-01")
        self.add_expense(2000, "2026-01-10")
        
        # 日粒度
        result_day = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-10", "day"
        )
        
        errors = []
        
        # 检查连续性
        if len(result_day["data"]) != 10:
            errors.append(f"日粒度应有10天，实际 {len(result_day['data'])} 个")
        
        # 检查中间日期为0
        for item in result_day["data"]:
            if item["label"] not in ["2026-01-01", "2026-01-10"]:
                if item["expense"] != 0.0:
                    errors.append(f"{item['label']} 无交易但支出不为0: {item['expense']}")
        
        # 月粒度也检查连续性
        self.reset_db()
        self.add_expense(1000, "2025-11-15")
        self.add_expense(2000, "2026-01-15")
        
        result_month = self.stats_service.get_trend_data_advanced(
            "2025-11-01", "2026-01-31", "month"
        )
        
        # 2025-12 应存在且为0
        data_map = {item["label"]: item for item in result_month["data"]}
        if "2025-12" not in data_map:
            errors.append("2025-12 应在数据中（即使为0）")
        elif data_map["2025-12"]["expense"] != 0.0:
            errors.append(f"2025-12 无交易但支出不为0")
        
        self.record_result(
            "TC-CONT-001", "无交易时间点显示为0",
            len(errors) == 0,
            "; ".join(errors) if errors else "X轴仍显示该时间点，数值为0，折线不断裂",
            "Critical"
        )
    
    # ==========================================================
    # 5.3 收入显示控制（服务层测试）
    # ==========================================================
    
    def test_income_001_default_show(self):
        """TC-INCOME-001: 默认显示收入（验证数据包含收入）"""
        self.reset_db()
        
        self.add_expense(1000, "2026-01-05")
        self.add_income(5000, "2026-01-05")
        
        result = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-10", "day"
        )
        
        errors = []
        
        # 数据中应包含 income 字段
        has_income = any(item.get("income", 0) > 0 for item in result["data"])
        if not has_income:
            errors.append("数据中应包含收入值")
        
        data_map = {item["label"]: item for item in result["data"]}
        if data_map.get("2026-01-05", {}).get("income") != 50.0:
            errors.append(f"01-05收入应为50.0")
        
        self.record_result(
            "TC-INCOME-001", "默认显示收入",
            len(errors) == 0,
            "; ".join(errors) if errors else "数据包含收入折线数据",
            "Major"
        )
    
    def test_income_002_003_toggle(self):
        """TC-INCOME-002/003: 收入显示切换（UI层逻辑，这里验证数据正确性）"""
        # 注：实际UI层的显示/隐藏由 TrendChartWidget.set_show_income 控制
        # 这里验证数据层始终返回完整数据，UI层控制显示
        
        self.reset_db()
        self.add_expense(1000, "2026-01-05")
        self.add_income(5000, "2026-01-05")
        
        result = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-10", "day"
        )
        
        errors = []
        
        # 数据应同时包含 income 和 expense
        data_map = {item["label"]: item for item in result["data"]}
        item = data_map.get("2026-01-05", {})
        
        if "income" not in item:
            errors.append("数据应包含 income 字段")
        if "expense" not in item:
            errors.append("数据应包含 expense 字段")
        
        self.record_result(
            "TC-INCOME-002/003", "收入显示切换（数据层验证）",
            len(errors) == 0,
            "; ".join(errors) if errors else "数据层返回完整收入支出数据，UI层控制显示",
            "Major"
        )
    
    # ==========================================================
    # 5.4 支出类别筛选
    # ==========================================================
    
    def test_cat_filter_001_all(self):
        """TC-CAT-FILTER-001: 默认全部支出"""
        self.reset_db()
        
        self.add_expense(1000, "2026-01-05", "吃饭")   # $10
        self.add_expense(2000, "2026-01-05", "交通")   # $20
        self.add_expense(3000, "2026-01-05", "购物")   # $30
        
        # 不传 category 或传 None
        result = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-10", "day", None
        )
        
        errors = []
        
        data_map = {item["label"]: item for item in result["data"]}
        total_expense = data_map.get("2026-01-05", {}).get("expense", 0)
        
        # 应为 10 + 20 + 30 = 60
        if total_expense != 60.0:
            errors.append(f"全部支出应为60.0，实际为 {total_expense}")
        
        self.record_result(
            "TC-CAT-FILTER-001", "默认全部支出",
            len(errors) == 0,
            "; ".join(errors) if errors else "支出趋势等于所有分类支出之和",
            "Blocker"
        )
    
    def test_cat_filter_002_single(self):
        """TC-CAT-FILTER-002: 单一分类筛选"""
        self.reset_db()
        
        self.add_expense(1000, "2026-01-05", "吃饭")   # $10
        self.add_expense(2000, "2026-01-05", "交通")   # $20
        self.add_expense(3000, "2026-01-07", "吃饭")   # $30
        self.add_income(5000, "2026-01-05")            # $50
        
        # 筛选 "吃饭" 分类
        result = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-10", "day", "吃饭"
        )
        
        errors = []
        
        data_map = {item["label"]: item for item in result["data"]}
        
        # 01-05 应只有 吃饭 的 $10
        if data_map.get("2026-01-05", {}).get("expense") != 10.0:
            errors.append(f"01-05筛选吃饭后支出应为10.0，实际为 {data_map.get('2026-01-05', {}).get('expense')}")
        
        # 01-07 应为 $30
        if data_map.get("2026-01-07", {}).get("expense") != 30.0:
            errors.append(f"01-07筛选吃饭后支出应为30.0")
        
        # 收入不受影响
        if data_map.get("2026-01-05", {}).get("income") != 50.0:
            errors.append(f"分类筛选不应影响收入，01-05收入应为50.0")
        
        self.record_result(
            "TC-CAT-FILTER-002", "单一分类筛选",
            len(errors) == 0,
            "; ".join(errors) if errors else "支出趋势仅包含该分类，收入不受影响",
            "Critical"
        )
    
    def test_cat_filter_003_no_data(self):
        """TC-CAT-FILTER-003: 分类无数据"""
        self.reset_db()
        
        self.add_expense(1000, "2026-01-05", "吃饭")
        self.add_income(5000, "2026-01-05")
        
        # 筛选 "购物" 分类（无数据）
        result = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-10", "day", "购物"
        )
        
        errors = []
        
        # X轴应连续
        if len(result["data"]) != 10:
            errors.append(f"应有10天数据点，实际 {len(result['data'])} 个")
        
        # 所有支出应为0
        for item in result["data"]:
            if item["expense"] != 0.0:
                errors.append(f"{item['label']} 支出应为0，实际为 {item['expense']}")
                break
        
        # 收入不受影响
        data_map = {item["label"]: item for item in result["data"]}
        if data_map.get("2026-01-05", {}).get("income") != 50.0:
            errors.append("收入应不受分类筛选影响")
        
        self.record_result(
            "TC-CAT-FILTER-003", "分类无数据",
            len(errors) == 0,
            "; ".join(errors) if errors else "X轴连续，支出值全部为0，不报错",
            "Critical"
        )
    
    # ==========================================================
    # 5.5 组合场景测试
    # ==========================================================
    
    def test_comb_001_multi_controls(self):
        """TC-COMB-001: 粒度 + 分类组合"""
        self.reset_db()
        
        # 添加跨月数据
        self.add_expense(1000, "2025-11-15", "吃饭")   # $10
        self.add_expense(2000, "2025-11-20", "交通")   # $20
        self.add_expense(3000, "2025-12-10", "吃饭")   # $30
        self.add_expense(4000, "2025-12-15", "购物")   # $40
        self.add_expense(5000, "2026-01-05", "吃饭")   # $50
        self.add_income(100000, "2025-12-25")          # $1000
        
        # 月粒度 + 吃饭分类
        result = self.stats_service.get_trend_data_advanced(
            "2025-11-01", "2026-01-31", "month", "吃饭"
        )
        
        errors = []
        
        if result["granularity"] != "month":
            errors.append(f"粒度应为 month")
        
        data_map = {item["label"]: item for item in result["data"]}
        
        # 2025-11 吃饭: $10
        if data_map.get("2025-11", {}).get("expense") != 10.0:
            errors.append(f"2025-11吃饭支出应为10.0，实际为 {data_map.get('2025-11', {}).get('expense')}")
        
        # 2025-12 吃饭: $30
        if data_map.get("2025-12", {}).get("expense") != 30.0:
            errors.append(f"2025-12吃饭支出应为30.0，实际为 {data_map.get('2025-12', {}).get('expense')}")
        
        # 2026-01 吃饭: $50
        if data_map.get("2026-01", {}).get("expense") != 50.0:
            errors.append(f"2026-01吃饭支出应为50.0，实际为 {data_map.get('2026-01', {}).get('expense')}")
        
        # 收入应不受影响
        if data_map.get("2025-12", {}).get("income") != 1000.0:
            errors.append(f"2025-12收入应为1000.0")
        
        self.record_result(
            "TC-COMB-001", "粒度 + 分类组合",
            len(errors) == 0,
            "; ".join(errors) if errors else "仅显示该分类的支出月趋势，数据正确",
            "Blocker"
        )
    
    def test_comb_002_rapid_switch(self):
        """TC-COMB-002: 快速切换（模拟）"""
        self.reset_db()
        
        self.add_expense(1000, "2026-01-05", "吃饭")
        self.add_expense(2000, "2026-01-10", "交通")
        self.add_income(5000, "2026-01-08")
        
        errors = []
        
        # 模拟快速切换：连续调用不同参数
        try:
            for _ in range(10):
                self.stats_service.get_trend_data_advanced("2026-01-01", "2026-01-15", "day", None)
                self.stats_service.get_trend_data_advanced("2026-01-01", "2026-01-15", "week", "吃饭")
                self.stats_service.get_trend_data_advanced("2025-01-01", "2026-01-15", "month", "交通")
                self.stats_service.get_trend_data_advanced("2025-01-01", "2026-12-31", "year", None)
        except Exception as e:
            errors.append(f"快速切换异常: {str(e)}")
        
        # 最终结果应正确
        result = self.stats_service.get_trend_data_advanced("2026-01-01", "2026-01-15", "day", None)
        if len(result["data"]) != 15:
            errors.append(f"最终结果应有15天数据")
        
        self.record_result(
            "TC-COMB-002", "快速切换",
            len(errors) == 0,
            "; ".join(errors) if errors else "无崩溃，趋势图始终与当前选择一致",
            "Major"
        )
    
    # ==========================================================
    # 5.6 数据变更同步
    # ==========================================================
    
    def test_sync_001_add(self):
        """TC-SYNC-001: 新增交易"""
        self.reset_db()
        
        result_before = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-10", "day"
        )
        before_map = {item["label"]: item for item in result_before["data"]}
        initial = before_map.get("2026-01-05", {}).get("expense", 0)
        
        # 新增
        self.add_expense(5000, "2026-01-05")
        
        result_after = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-10", "day"
        )
        after_map = {item["label"]: item for item in result_after["data"]}
        final = after_map.get("2026-01-05", {}).get("expense", 0)
        
        errors = []
        if final != initial + 50.0:
            errors.append(f"新增后支出应为 {initial + 50.0}，实际为 {final}")
        
        self.record_result(
            "TC-SYNC-001", "新增交易",
            len(errors) == 0,
            "; ".join(errors) if errors else "趋势图立即更新",
            "Major"
        )
    
    def test_sync_002_modify(self):
        """TC-SYNC-002: 修改交易"""
        self.reset_db()
        
        tx_id = self.add_expense(5000, "2026-01-05")
        
        result_before = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-10", "day"
        )
        
        # 修改金额
        tx = self.db.get_transaction_by_id(tx_id)
        tx.amount_cents = 10000
        self.db.update_transaction(tx)
        
        result_after = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-10", "day"
        )
        after_map = {item["label"]: item for item in result_after["data"]}
        
        errors = []
        if after_map.get("2026-01-05", {}).get("expense") != 100.0:
            errors.append(f"修改后支出应为100.0")
        
        self.record_result(
            "TC-SYNC-002", "修改交易",
            len(errors) == 0,
            "; ".join(errors) if errors else "对应时间点值更新",
            "Major"
        )
    
    def test_sync_003_delete(self):
        """TC-SYNC-003: 删除交易"""
        self.reset_db()
        
        tx_id = self.add_expense(5000, "2026-01-05")
        self.add_expense(3000, "2026-01-05")
        
        result_before = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-10", "day"
        )
        
        # 删除一笔
        self.db.delete_transaction(tx_id)
        
        result_after = self.stats_service.get_trend_data_advanced(
            "2026-01-01", "2026-01-10", "day"
        )
        after_map = {item["label"]: item for item in result_after["data"]}
        
        errors = []
        if after_map.get("2026-01-05", {}).get("expense") != 30.0:
            errors.append(f"删除后支出应为30.0")
        
        self.record_result(
            "TC-SYNC-003", "删除交易",
            len(errors) == 0,
            "; ".join(errors) if errors else "对应时间点减少或归零",
            "Major"
        )
    
    # ==========================================================
    # 5.7 主题可读性（代码检查）
    # ==========================================================
    
    def test_theme_001_002(self):
        """TC-THEME-001/002: 深色/浅色模式可读性（代码检查）"""
        # 验证代码中使用了动态主题色
        from ledger.ui.theme import COLOR_INCOME, COLOR_EXPENSE, get_text_color
        
        errors = []
        
        # 检查颜色定义
        if COLOR_INCOME == COLOR_EXPENSE:
            errors.append("收入和支出颜色不应相同")
        
        # 检查动态文字颜色函数存在
        try:
            color = get_text_color()
            if color is None:
                errors.append("get_text_color() 应返回有效颜色")
        except Exception as e:
            errors.append(f"get_text_color() 异常: {e}")
        
        self.record_result(
            "TC-THEME-001/002", "深色/浅色模式可读性（代码检查）",
            len(errors) == 0,
            "; ".join(errors) if errors else f"收入色:{COLOR_INCOME}, 支出色:{COLOR_EXPENSE}, 使用动态文字色",
            "Major"
        )
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 70)
        print("Ledger App - 收支趋势图高级交互功能测试")
        print("Phase 1.x - Advanced Trend Chart Test Suite")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        try:
            self.setup()
            
            print("\n📊 5.1 时间粒度选择")
            print("-" * 50)
            self.test_grain_001_daily()
            self.test_grain_002_weekly()
            self.test_grain_003_monthly()
            self.test_grain_004_yearly()
            
            print("\n📊 5.2 连续性与0值测试")
            print("-" * 50)
            self.test_cont_001_zero_values()
            
            print("\n📊 5.3 收入显示控制")
            print("-" * 50)
            self.test_income_001_default_show()
            self.test_income_002_003_toggle()
            
            print("\n📊 5.4 支出类别筛选")
            print("-" * 50)
            self.test_cat_filter_001_all()
            self.test_cat_filter_002_single()
            self.test_cat_filter_003_no_data()
            
            print("\n📊 5.5 组合场景测试")
            print("-" * 50)
            self.test_comb_001_multi_controls()
            self.test_comb_002_rapid_switch()
            
            print("\n📊 5.6 数据变更同步")
            print("-" * 50)
            self.test_sync_001_add()
            self.test_sync_002_modify()
            self.test_sync_003_delete()
            
            print("\n📊 5.7 主题可读性")
            print("-" * 50)
            self.test_theme_001_002()
            
        finally:
            self.teardown()
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        failures_by_severity = {}
        for r in self.results:
            if not r["passed"]:
                sev = r["severity"]
                failures_by_severity[sev] = failures_by_severity.get(sev, 0) + 1
        
        print("\n" + "=" * 70)
        print("测试结果汇总")
        print("=" * 70)
        print(f"总测试数: {total}")
        print(f"通过: {passed} ✅")
        print(f"失败: {failed} ❌")
        print(f"通过率: {passed/total*100:.1f}%")
        
        if failures_by_severity:
            print("\n失败分布:")
            for sev, count in failures_by_severity.items():
                print(f"  - {sev}: {count}")
        
        if failed > 0:
            print("\n❌ 失败用例详情:")
            print("-" * 50)
            for r in self.results:
                if not r["passed"]:
                    print(f"  [{r['severity']}] {r['id']}: {r['name']}")
                    print(f"    详情: {r['details']}")
        
        print("\n" + "=" * 70)
        print("QA 结论")
        print("=" * 70)
        
        blockers = failures_by_severity.get("Blocker", 0)
        criticals = failures_by_severity.get("Critical", 0)
        
        if blockers > 0:
            print("🚫 存在 Blocker 级别缺陷，功能不可用")
            qa_conclusion = "BLOCKED"
        elif criticals > 0:
            print("⚠️ 存在 Critical 级别缺陷，功能部分受影响")
            qa_conclusion = "CONDITIONAL"
        elif failed > 0:
            print("⚠️ 存在 Major/Minor 级别缺陷")
            qa_conclusion = "PASS_WITH_ISSUES"
        else:
            print("✅ 所有测试通过")
            print("   趋势图增强功能：可信 + 连续 + 可控")
            qa_conclusion = "PASS"
        
        print("\n确认结论:")
        print("  - 周粒度符合 ISO 规则（周一开始）: " + ("✅" if not any(r["id"] == "TC-GRAIN-002" and not r["passed"] for r in self.results) else "❌"))
        print("  - 连续性满足预期: " + ("✅" if not any(r["id"] == "TC-CONT-001" and not r["passed"] for r in self.results) else "❌"))
        print("  - 组合交互稳定: " + ("✅" if not any("COMB" in r["id"] and not r["passed"] for r in self.results) else "❌"))
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total * 100,
            "qa_conclusion": qa_conclusion,
            "results": self.results
        }


def main():
    suite = AdvancedTrendTestSuite()
    report = suite.run_all_tests()
    
    # 保存测试报告
    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "TEST_REPORT_TREND_ADVANCED.md"
    )
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Ledger App - 收支趋势图高级交互功能测试报告\n\n")
        f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**测试版本**: Phase 1.x（趋势图增强）\n\n")
        f.write("---\n\n")
        f.write("## 测试结果汇总\n\n")
        f.write(f"| 指标 | 结果 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| 总测试数 | {report['total']} |\n")
        f.write(f"| 通过 | {report['passed']} ✅ |\n")
        f.write(f"| 失败 | {report['failed']} ❌ |\n")
        f.write(f"| 通过率 | {report['pass_rate']:.1f}% |\n")
        f.write(f"| QA结论 | **{report['qa_conclusion']}** |\n")
        f.write("\n---\n\n")
        f.write("## 测试用例详情\n\n")
        f.write("| ID | 测试项 | 状态 | 严重级别 | 详情 |\n")
        f.write("|-----|--------|------|----------|------|\n")
        for r in report["results"]:
            status = "✅ PASS" if r["passed"] else "❌ FAIL"
            details = r["details"][:60] + "..." if len(r["details"]) > 60 else r["details"]
            f.write(f"| {r['id']} | {r['name']} | {status} | {r['severity']} | {details} |\n")
        
        f.write("\n---\n\n")
        f.write("## QA 确认结论\n\n")
        f.write("| 确认项 | 结果 |\n")
        f.write("|--------|------|\n")
        f.write(f"| 周粒度符合 ISO 规则 | {'✅' if not any(r['id'] == 'TC-GRAIN-002' and not r['passed'] for r in report['results']) else '❌'} |\n")
        f.write(f"| 连续性满足预期 | {'✅' if not any(r['id'] == 'TC-CONT-001' and not r['passed'] for r in report['results']) else '❌'} |\n")
        f.write(f"| 组合交互稳定 | {'✅' if not any('COMB' in r['id'] and not r['passed'] for r in report['results']) else '❌'} |\n")
        
        f.write("\n---\n\n")
        f.write("## 手动验证项\n\n")
        f.write("以下测试项需要手动验证：\n\n")
        f.write("### TC-THEME-001: 浅色模式可读性\n")
        f.write("- [ ] 折线、坐标、图例、控件清晰\n\n")
        f.write("### TC-THEME-002: 深色模式可读性\n")
        f.write("- [ ] 折线与背景对比明显\n")
        f.write("- [ ] 控件文字清晰\n\n")
        f.write("---\n\n")
        f.write(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    print(f"\n📄 测试报告已保存至: {report_path}")
    
    return 0 if report["qa_conclusion"] in ["PASS", "PASS_WITH_ISSUES"] else 1


if __name__ == "__main__":
    sys.exit(main())

