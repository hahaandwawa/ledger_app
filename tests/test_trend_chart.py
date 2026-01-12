"""
Ledger App - 收支趋势图功能测试
Phase 1.x - Trend Chart Test Suite
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
from ledger.ui.theme import COLOR_INCOME, COLOR_EXPENSE, CHART_COLORS


class TrendChartTestSuite:
    """趋势图功能测试套件"""
    
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
        
        # 检查是否已有默认分类（V3迁移已创建）
        existing_categories = {c.name for c in self.db.get_all_categories()}
        
        # 只添加缺失的分类
        test_categories = [
            ("餐饮", "expense"),
            ("交通", "expense"),
            ("工资", "income"),
        ]
        for name, cat_type in test_categories:
            if name not in existing_categories:
                self.db.add_category(Category(name=name, type=cat_type))
        
        # 添加账户（如不存在）
        existing_accounts = {a.name for a in self.db.get_all_accounts()}
        if "现金" not in existing_accounts:
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
        """重置数据库（清除所有交易）"""
        if self.db and self.db.conn:
            cursor = self.db.conn.cursor()
            cursor.execute("DELETE FROM transactions")
            self.db.conn.commit()
            
    def add_expense(self, amount_cents: int, date_str: str, category: str = "餐饮") -> int:
        """添加支出"""
        cat = self.categories.get(category)
        acc = self.accounts.get("现金")
        tx = Transaction(
            type="expense",
            amount_cents=amount_cents,
            date=date_str,
            category=category,
            account="现金",
            note="测试",
            category_id=cat.id if cat else None,
            account_id=acc.id if acc else None
        )
        return self.db.add_transaction(tx)
    
    def add_income(self, amount_cents: int, date_str: str, category: str = "工资") -> int:
        """添加收入"""
        cat = self.categories.get(category)
        acc = self.accounts.get("现金")
        tx = Transaction(
            type="income",
            amount_cents=amount_cents,
            date=date_str,
            category=category,
            account="现金",
            note="测试",
            category_id=cat.id if cat else None,
            account_id=acc.id if acc else None
        )
        return self.db.add_transaction(tx)
    
    def record_result(self, test_id: str, name: str, passed: bool, 
                      details: str = "", severity: str = "Major"):
        """记录测试结果"""
        status = "PASS" if passed else "FAIL"
        self.results.append({
            "id": test_id,
            "name": name,
            "status": status,
            "passed": passed,
            "details": details,
            "severity": severity
        })
        icon = "✅" if passed else "❌"
        print(f"  {icon} {test_id}: {name} - {status}")
        if details:
            print(f"      {details}")
    
    # ==========================================================
    # 5.1 基础正确性测试
    # ==========================================================
    
    def test_trend_001_daily_expense_aggregation(self):
        """TC-TREND-001: 本月按天聚合（支出）"""
        self.reset_db()
        today = date.today()
        
        # 在本月不同日期新增多笔支出
        day1 = today.replace(day=1).strftime("%Y-%m-%d")
        day5 = today.replace(day=5).strftime("%Y-%m-%d")
        day10 = today.replace(day=10).strftime("%Y-%m-%d")
        
        self.add_expense(1000, day1)  # $10.00
        self.add_expense(2000, day1)  # $20.00 -> 同一天合计$30.00
        self.add_expense(3000, day5)  # $30.00
        self.add_expense(5000, day10) # $50.00
        
        # 获取本月趋势数据
        start, end = self.stats_service.get_month_range(today.year, today.month)
        trend_result = self.stats_service.get_trend_data(start, end)
        
        # 验证结果
        errors = []
        
        # 检查粒度
        if trend_result["granularity"] != "day":
            errors.append(f"粒度应为 day，实际为 {trend_result['granularity']}")
        
        # 转换为字典便于查找
        data_map = {item["label"]: item for item in trend_result["data"]}
        
        # 检查各日支出
        if day1 in data_map:
            if data_map[day1]["expense"] != 30.0:  # 1000 + 2000 = 3000 cents = $30.00
                errors.append(f"{day1} 支出应为 30.0，实际为 {data_map[day1]['expense']}")
        else:
            errors.append(f"{day1} 未在趋势数据中")
            
        if day5 in data_map:
            if data_map[day5]["expense"] != 30.0:
                errors.append(f"{day5} 支出应为 30.0，实际为 {data_map[day5]['expense']}")
        else:
            errors.append(f"{day5} 未在趋势数据中")
            
        if day10 in data_map:
            if data_map[day10]["expense"] != 50.0:
                errors.append(f"{day10} 支出应为 50.0，实际为 {data_map[day10]['expense']}")
        else:
            errors.append(f"{day10} 未在趋势数据中")
        
        # 检查X轴是否连续（检查数据点数量）
        expected_days = (date.fromisoformat(end) - date.fromisoformat(start)).days + 1
        actual_days = len(trend_result["data"])
        if actual_days != expected_days:
            errors.append(f"X轴应有 {expected_days} 天，实际有 {actual_days} 天")
        
        # 检查无交易日期是否为0
        day2 = today.replace(day=2).strftime("%Y-%m-%d")
        if day2 in data_map:
            if data_map[day2]["expense"] != 0.0:
                errors.append(f"无交易日 {day2} 支出应为 0，实际为 {data_map[day2]['expense']}")
        
        self.record_result(
            "TC-TREND-001", 
            "本月按天聚合（支出）",
            len(errors) == 0,
            "; ".join(errors) if errors else "支出聚合正确，X轴连续，无交易日显示0",
            "Blocker"
        )
    
    def test_trend_002_daily_income_aggregation(self):
        """TC-TREND-002: 本月按天聚合（收入）"""
        self.reset_db()
        today = date.today()
        
        # 在本月不同日期新增多笔收入
        day1 = today.replace(day=1).strftime("%Y-%m-%d")
        day5 = today.replace(day=5).strftime("%Y-%m-%d")
        
        self.add_income(500000, day1)  # $5000.00 工资
        self.add_income(100000, day5)  # $1000.00 奖金
        
        # 同时添加一笔支出来检验两条线区分
        self.add_expense(2000, day1)  # $20.00
        
        # 获取本月趋势数据
        start, end = self.stats_service.get_month_range(today.year, today.month)
        trend_result = self.stats_service.get_trend_data(start, end)
        
        errors = []
        data_map = {item["label"]: item for item in trend_result["data"]}
        
        # 检查收入数据
        if day1 in data_map:
            if data_map[day1]["income"] != 5000.0:
                errors.append(f"{day1} 收入应为 5000.0，实际为 {data_map[day1]['income']}")
            if data_map[day1]["expense"] != 20.0:
                errors.append(f"{day1} 支出应为 20.0，实际为 {data_map[day1]['expense']}")
        else:
            errors.append(f"{day1} 未在趋势数据中")
            
        if day5 in data_map:
            if data_map[day5]["income"] != 1000.0:
                errors.append(f"{day5} 收入应为 1000.0，实际为 {data_map[day5]['income']}")
        else:
            errors.append(f"{day5} 未在趋势数据中")
        
        self.record_result(
            "TC-TREND-002",
            "本月按天聚合（收入）",
            len(errors) == 0,
            "; ".join(errors) if errors else "收入趋势与明细一致，与支出线区分",
            "Blocker"
        )
    
    # ==========================================================
    # 5.2 跨区间与粒度切换
    # ==========================================================
    
    def test_trend_003_yearly_monthly_aggregation(self):
        """TC-TREND-003: 本年按月聚合"""
        self.reset_db()
        today = date.today()
        
        # 在不同月份新增支出与收入
        jan_date = f"{today.year}-01-15"
        mar_date = f"{today.year}-03-10"
        
        # 一月份
        self.add_expense(10000, jan_date)  # $100
        self.add_expense(5000, jan_date)   # $50 -> 合计 $150
        self.add_income(200000, jan_date)  # $2000
        
        # 三月份
        self.add_expense(30000, mar_date)  # $300
        self.add_income(100000, mar_date)  # $1000
        
        # 获取本年趋势数据
        start, end = self.stats_service.get_year_range(today.year)
        trend_result = self.stats_service.get_trend_data(start, end)
        
        errors = []
        
        # 检查粒度应为 month
        if trend_result["granularity"] != "month":
            errors.append(f"粒度应为 month，实际为 {trend_result['granularity']}")
        
        data_map = {item["label"]: item for item in trend_result["data"]}
        
        # 检查一月份数据
        jan_key = f"{today.year}-01"
        if jan_key in data_map:
            if data_map[jan_key]["expense"] != 150.0:
                errors.append(f"1月支出应为 150.0，实际为 {data_map[jan_key]['expense']}")
            if data_map[jan_key]["income"] != 2000.0:
                errors.append(f"1月收入应为 2000.0，实际为 {data_map[jan_key]['income']}")
        else:
            errors.append(f"{jan_key} 未在趋势数据中")
        
        # 检查三月份数据
        mar_key = f"{today.year}-03"
        if mar_key in data_map:
            if data_map[mar_key]["expense"] != 300.0:
                errors.append(f"3月支出应为 300.0，实际为 {data_map[mar_key]['expense']}")
            if data_map[mar_key]["income"] != 1000.0:
                errors.append(f"3月收入应为 1000.0，实际为 {data_map[mar_key]['income']}")
        else:
            errors.append(f"{mar_key} 未在趋势数据中")
        
        # 检查二月份（无交易）应为0
        feb_key = f"{today.year}-02"
        if feb_key in data_map:
            if data_map[feb_key]["expense"] != 0.0:
                errors.append(f"2月支出应为 0，实际为 {data_map[feb_key]['expense']}")
            if data_map[feb_key]["income"] != 0.0:
                errors.append(f"2月收入应为 0，实际为 {data_map[feb_key]['income']}")
        else:
            errors.append(f"{feb_key} 未在趋势数据中（应显示为0）")
        
        # 检查月份数量（1-12月）
        if len(trend_result["data"]) != 12:
            errors.append(f"全年应有12个月，实际有 {len(trend_result['data'])} 个")
        
        self.record_result(
            "TC-TREND-003",
            "本年按月聚合",
            len(errors) == 0,
            "; ".join(errors) if errors else "按月聚合正确，X轴为YYYY-MM，无交易月显示0",
            "Blocker"
        )
    
    def test_trend_004_granularity_auto_switch(self):
        """TC-TREND-004: 自定义区间粒度切换"""
        self.reset_db()
        today = date.today()
        
        # 添加一些测试数据
        self.add_expense(5000, today.strftime("%Y-%m-%d"))
        
        errors = []
        
        # 测试1: 10天区间 -> 应按天显示
        start_10d = (today - timedelta(days=9)).strftime("%Y-%m-%d")
        end_10d = today.strftime("%Y-%m-%d")
        result_10d = self.stats_service.get_trend_data(start_10d, end_10d)
        
        if result_10d["granularity"] != "day":
            errors.append(f"10天区间粒度应为 day，实际为 {result_10d['granularity']}")
        if len(result_10d["data"]) != 10:
            errors.append(f"10天区间应有10个数据点，实际有 {len(result_10d['data'])} 个")
        
        # 测试2: 31天区间（临界值）-> 应按天显示
        start_31d = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end_31d = today.strftime("%Y-%m-%d")
        result_31d = self.stats_service.get_trend_data(start_31d, end_31d)
        
        if result_31d["granularity"] != "day":
            errors.append(f"31天区间粒度应为 day，实际为 {result_31d['granularity']}")
        
        # 测试3: 3个月区间 -> 应按月显示
        start_3m = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        end_3m = today.strftime("%Y-%m-%d")
        result_3m = self.stats_service.get_trend_data(start_3m, end_3m)
        
        if result_3m["granularity"] != "month":
            errors.append(f"3个月区间粒度应为 month，实际为 {result_3m['granularity']}")
        
        self.record_result(
            "TC-TREND-004",
            "自定义区间粒度切换",
            len(errors) == 0,
            "; ".join(errors) if errors else "粒度自动切换正确：≤31天按天，>31天按月",
            "Blocker"
        )
    
    # ==========================================================
    # 5.3 边界与连续性测试
    # ==========================================================
    
    def test_trend_005_boundary_dates(self):
        """TC-TREND-005: 边界日期包含性"""
        self.reset_db()
        
        # 使用固定日期范围
        start_date = "2026-01-05"
        end_date = "2026-01-15"
        
        # 在起始日和结束日各新增一笔交易
        self.add_expense(1000, start_date)  # $10 起始日
        self.add_expense(2000, end_date)    # $20 结束日
        
        trend_result = self.stats_service.get_trend_data(start_date, end_date)
        
        errors = []
        data_map = {item["label"]: item for item in trend_result["data"]}
        
        # 验证起始日包含
        if start_date not in data_map:
            errors.append(f"起始日 {start_date} 未包含在趋势数据中")
        elif data_map[start_date]["expense"] != 10.0:
            errors.append(f"起始日支出应为 10.0，实际为 {data_map[start_date]['expense']}")
        
        # 验证结束日包含
        if end_date not in data_map:
            errors.append(f"结束日 {end_date} 未包含在趋势数据中")
        elif data_map[end_date]["expense"] != 20.0:
            errors.append(f"结束日支出应为 20.0，实际为 {data_map[end_date]['expense']}")
        
        # 验证天数正确（01-05 到 01-15 = 11天）
        if len(trend_result["data"]) != 11:
            errors.append(f"应有11天，实际有 {len(trend_result['data'])} 天")
        
        self.record_result(
            "TC-TREND-005",
            "边界日期包含性",
            len(errors) == 0,
            "; ".join(errors) if errors else "起始日与结束日均正确包含",
            "Critical"
        )
    
    def test_trend_006_continuity(self):
        """TC-TREND-006: 连续性测试"""
        self.reset_db()
        
        # 使用10天区间，只在第1天和第10天有交易
        start_date = "2026-01-01"
        end_date = "2026-01-10"
        
        self.add_expense(1000, start_date)
        self.add_expense(2000, end_date)
        
        trend_result = self.stats_service.get_trend_data(start_date, end_date)
        
        errors = []
        
        # 检查连续性：所有日期都应存在
        expected_dates = []
        current = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        while current <= end:
            expected_dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        actual_labels = [item["label"] for item in trend_result["data"]]
        
        if actual_labels != expected_dates:
            missing = set(expected_dates) - set(actual_labels)
            extra = set(actual_labels) - set(expected_dates)
            if missing:
                errors.append(f"缺失日期: {missing}")
            if extra:
                errors.append(f"多余日期: {extra}")
        
        # 检查中间无交易日期的值为0
        for item in trend_result["data"]:
            if item["label"] not in [start_date, end_date]:
                if item["expense"] != 0.0:
                    errors.append(f"{item['label']} 无交易但支出不为0: {item['expense']}")
                if item["income"] != 0.0:
                    errors.append(f"{item['label']} 无交易但收入不为0: {item['income']}")
        
        self.record_result(
            "TC-TREND-006",
            "连续性测试",
            len(errors) == 0,
            "; ".join(errors) if errors else "X轴连续，无交易日期显示为0，折线连续",
            "Critical"
        )
    
    # ==========================================================
    # 5.4 数据变更同步测试
    # ==========================================================
    
    def test_trend_007_add_refresh(self):
        """TC-TREND-007: 新增交易后刷新"""
        self.reset_db()
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        
        start, end = self.stats_service.get_month_range(today.year, today.month)
        
        # 初始状态
        result_before = self.stats_service.get_trend_data(start, end)
        before_map = {item["label"]: item for item in result_before["data"]}
        initial_expense = before_map.get(today_str, {}).get("expense", 0)
        
        # 新增一笔交易
        self.add_expense(5000, today_str)  # $50
        
        # 再次获取数据（模拟刷新）
        result_after = self.stats_service.get_trend_data(start, end)
        after_map = {item["label"]: item for item in result_after["data"]}
        new_expense = after_map.get(today_str, {}).get("expense", 0)
        
        errors = []
        expected = initial_expense + 50.0
        if new_expense != expected:
            errors.append(f"新增后支出应为 {expected}，实际为 {new_expense}")
        
        self.record_result(
            "TC-TREND-007",
            "新增交易后刷新",
            len(errors) == 0,
            "; ".join(errors) if errors else f"新增交易后数据正确更新: {initial_expense} -> {new_expense}",
            "Major"
        )
    
    def test_trend_008_modify_refresh(self):
        """TC-TREND-008: 修改交易后刷新"""
        self.reset_db()
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        yesterday_str = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # 添加初始交易
        tx_id = self.add_expense(5000, today_str)  # $50
        
        start, end = self.stats_service.get_month_range(today.year, today.month)
        
        # 修改金额
        tx = self.db.get_transaction_by_id(tx_id)
        tx.amount_cents = 10000  # 改为 $100
        self.db.update_transaction(tx)
        
        result_after = self.stats_service.get_trend_data(start, end)
        after_map = {item["label"]: item for item in result_after["data"]}
        
        errors = []
        if after_map.get(today_str, {}).get("expense") != 100.0:
            errors.append(f"修改金额后支出应为 100.0，实际为 {after_map.get(today_str, {}).get('expense')}")
        
        # 修改日期
        tx.date = yesterday_str
        self.db.update_transaction(tx)
        
        result_after2 = self.stats_service.get_trend_data(start, end)
        after_map2 = {item["label"]: item for item in result_after2["data"]}
        
        if after_map2.get(today_str, {}).get("expense", 0) != 0.0:
            errors.append(f"修改日期后原日期支出应为 0，实际为 {after_map2.get(today_str, {}).get('expense')}")
        if after_map2.get(yesterday_str, {}).get("expense") != 100.0:
            errors.append(f"修改日期后新日期支出应为 100.0，实际为 {after_map2.get(yesterday_str, {}).get('expense')}")
        
        self.record_result(
            "TC-TREND-008",
            "修改交易后刷新",
            len(errors) == 0,
            "; ".join(errors) if errors else "修改金额和日期后趋势图正确更新",
            "Major"
        )
    
    def test_trend_009_delete_refresh(self):
        """TC-TREND-009: 删除交易后刷新"""
        self.reset_db()
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        
        # 添加两笔交易
        tx_id1 = self.add_expense(3000, today_str)  # $30
        tx_id2 = self.add_expense(2000, today_str)  # $20
        
        start, end = self.stats_service.get_month_range(today.year, today.month)
        
        # 验证初始状态
        result_before = self.stats_service.get_trend_data(start, end)
        before_map = {item["label"]: item for item in result_before["data"]}
        
        errors = []
        if before_map.get(today_str, {}).get("expense") != 50.0:
            errors.append(f"初始支出应为 50.0")
        
        # 删除一笔
        self.db.delete_transaction(tx_id1)
        
        result_after = self.stats_service.get_trend_data(start, end)
        after_map = {item["label"]: item for item in result_after["data"]}
        
        if after_map.get(today_str, {}).get("expense") != 20.0:
            errors.append(f"删除后支出应为 20.0，实际为 {after_map.get(today_str, {}).get('expense')}")
        
        # 删除最后一笔
        self.db.delete_transaction(tx_id2)
        
        result_final = self.stats_service.get_trend_data(start, end)
        final_map = {item["label"]: item for item in result_final["data"]}
        
        if final_map.get(today_str, {}).get("expense") != 0.0:
            errors.append(f"全部删除后支出应为 0，实际为 {final_map.get(today_str, {}).get('expense')}")
        
        self.record_result(
            "TC-TREND-009",
            "删除交易后刷新",
            len(errors) == 0,
            "; ".join(errors) if errors else "删除后趋势图正确更新，全删后显示0",
            "Major"
        )
    
    # ==========================================================
    # 5.5 空数据场景
    # ==========================================================
    
    def test_trend_010_empty_data(self):
        """TC-TREND-010: 无收支数据"""
        self.reset_db()
        
        # 选择一个完全无交易的区间（过去的某段时间）
        start_date = "2020-01-01"
        end_date = "2020-01-10"
        
        errors = []
        
        try:
            trend_result = self.stats_service.get_trend_data(start_date, end_date)
            
            # 检查返回的数据结构
            if "data" not in trend_result:
                errors.append("返回结果缺少 data 字段")
            elif "granularity" not in trend_result:
                errors.append("返回结果缺少 granularity 字段")
            else:
                # 数据应存在但都为0
                all_zero = all(
                    item["income"] == 0 and item["expense"] == 0 
                    for item in trend_result["data"]
                )
                if not all_zero:
                    errors.append("空区间但存在非零数据")
                    
                # 日期应连续
                if len(trend_result["data"]) != 10:
                    errors.append(f"应有10天数据点，实际有 {len(trend_result['data'])} 个")
                    
        except Exception as e:
            errors.append(f"空数据场景异常: {str(e)}")
        
        self.record_result(
            "TC-TREND-010",
            "无收支数据",
            len(errors) == 0,
            "; ".join(errors) if errors else "空数据场景处理正常，不崩溃，返回全0数据",
            "Critical"
        )
    
    # ==========================================================
    # 5.6 深色/浅色模式可读性（UI检查，需手动验证）
    # ==========================================================
    
    def test_trend_011_012_theme_readability(self):
        """TC-TREND-011/012: 深色/浅色模式可读性（代码检查）"""
        errors = []
        warnings = []
        
        # 检查颜色常量定义
        if COLOR_INCOME == COLOR_EXPENSE:
            errors.append("收入和支出颜色相同，无法区分")
        
        # 检查颜色对比度（简单检查）
        income_color = COLOR_INCOME.lstrip('#')
        expense_color = COLOR_EXPENSE.lstrip('#')
        
        # 绿色检查（收入）
        income_r = int(income_color[0:2], 16)
        income_g = int(income_color[2:4], 16)
        income_b = int(income_color[4:6], 16)
        
        # 红色检查（支出）
        expense_r = int(expense_color[0:2], 16)
        expense_g = int(expense_color[2:4], 16)
        expense_b = int(expense_color[4:6], 16)
        
        # 检查是否足够鲜艳（至少一个通道>100）
        if max(income_r, income_g, income_b) < 100:
            warnings.append(f"收入颜色 {COLOR_INCOME} 可能在深色背景下不够明显")
        
        if max(expense_r, expense_g, expense_b) < 100:
            warnings.append(f"支出颜色 {COLOR_EXPENSE} 可能在深色背景下不够明显")
        
        # 检查图表颜色是否有足够数量
        if len(CHART_COLORS) < 10:
            warnings.append(f"图表颜色仅 {len(CHART_COLORS)} 种，可能不够区分多分类")
        
        details = []
        details.append(f"收入色: {COLOR_INCOME}, 支出色: {COLOR_EXPENSE}")
        details.append(f"图表颜色数: {len(CHART_COLORS)}")
        if warnings:
            details.extend([f"警告: {w}" for w in warnings])
        details.append("注意: 完整可读性需手动切换系统主题验证")
        
        self.record_result(
            "TC-TREND-011/012",
            "深色/浅色模式可读性（代码检查）",
            len(errors) == 0,
            "; ".join(details),
            "Major"
        )
    
    # ==========================================================
    # 额外验证：趋势图与明细/统计一致性
    # ==========================================================
    
    def test_trend_consistency_with_summary(self):
        """额外测试：趋势图与统计汇总一致性"""
        self.reset_db()
        today = date.today()
        
        # 添加本月交易
        for i in range(1, 11):
            day_str = today.replace(day=min(i, 28)).strftime("%Y-%m-%d")
            self.add_expense(i * 1000, day_str)  # $10, $20, ..., $100
            if i % 3 == 0:
                self.add_income(i * 2000, day_str)
        
        start, end = self.stats_service.get_month_range(today.year, today.month)
        
        # 从趋势图计算总额
        trend_result = self.stats_service.get_trend_data(start, end)
        trend_total_expense = sum(item["expense"] for item in trend_result["data"])
        trend_total_income = sum(item["income"] for item in trend_result["data"])
        
        # 从汇总API获取总额
        summary = self.stats_service.get_custom_period_summary(start, end)
        
        errors = []
        
        # 比较支出
        if abs(trend_total_expense - summary.expense) > 0.01:
            errors.append(f"支出不一致: 趋势图={trend_total_expense}, 汇总={summary.expense}")
        
        # 比较收入
        if abs(trend_total_income - summary.income) > 0.01:
            errors.append(f"收入不一致: 趋势图={trend_total_income}, 汇总={summary.income}")
        
        self.record_result(
            "TC-TREND-EXTRA-001",
            "趋势图与统计汇总一致性",
            len(errors) == 0,
            "; ".join(errors) if errors else f"一致: 支出=${trend_total_expense:.2f}, 收入=${trend_total_income:.2f}",
            "Blocker"
        )
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 70)
        print("Ledger App - 收支趋势图功能测试")
        print("Phase 1.x - Trend Chart Test Suite")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        try:
            self.setup()
            
            print("\n📊 5.1 基础正确性测试")
            print("-" * 50)
            self.test_trend_001_daily_expense_aggregation()
            self.test_trend_002_daily_income_aggregation()
            
            print("\n📊 5.2 跨区间与粒度切换")
            print("-" * 50)
            self.test_trend_003_yearly_monthly_aggregation()
            self.test_trend_004_granularity_auto_switch()
            
            print("\n📊 5.3 边界与连续性测试")
            print("-" * 50)
            self.test_trend_005_boundary_dates()
            self.test_trend_006_continuity()
            
            print("\n📊 5.4 数据变更同步测试")
            print("-" * 50)
            self.test_trend_007_add_refresh()
            self.test_trend_008_modify_refresh()
            self.test_trend_009_delete_refresh()
            
            print("\n📊 5.5 空数据场景")
            print("-" * 50)
            self.test_trend_010_empty_data()
            
            print("\n📊 5.6 可读性与一致性检查")
            print("-" * 50)
            self.test_trend_011_012_theme_readability()
            self.test_trend_consistency_with_summary()
            
        finally:
            self.teardown()
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        
        # 按严重级别统计失败
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
        
        # 输出失败详情
        if failed > 0:
            print("\n❌ 失败用例详情:")
            print("-" * 50)
            for r in self.results:
                if not r["passed"]:
                    print(f"  [{r['severity']}] {r['id']}: {r['name']}")
                    print(f"    详情: {r['details']}")
        
        # QA结论
        print("\n" + "=" * 70)
        print("QA 结论")
        print("=" * 70)
        
        blockers = failures_by_severity.get("Blocker", 0)
        criticals = failures_by_severity.get("Critical", 0)
        
        if blockers > 0:
            print("🚫 存在 Blocker 级别缺陷，趋势图功能不可用")
            print("   建议: 修复后重新测试")
            qa_conclusion = "BLOCKED"
        elif criticals > 0:
            print("⚠️ 存在 Critical 级别缺陷，趋势图功能部分受影响")
            print("   建议: 评估风险后决定是否发布")
            qa_conclusion = "CONDITIONAL"
        elif failed > 0:
            print("⚠️ 存在 Major/Minor 级别缺陷")
            print("   建议: 可进入下一阶段，但应计划修复")
            qa_conclusion = "PASS_WITH_ISSUES"
        else:
            print("✅ 所有测试通过")
            print("   趋势图功能：可信、连续、可读")
            print("   建议: 可进入下一阶段")
            qa_conclusion = "PASS"
        
        print("\n注意事项:")
        print("  - TC-TREND-011/012 深色/浅色模式可读性需手动验证")
        print("  - 建议在实际应用中切换系统主题进行视觉检查")
        
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total * 100,
            "qa_conclusion": qa_conclusion,
            "results": self.results
        }


def main():
    suite = TrendChartTestSuite()
    report = suite.run_all_tests()
    
    # 保存测试报告
    report_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "TEST_REPORT_TREND_CHART.md"
    )
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Ledger App - 收支趋势图功能测试报告\n\n")
        f.write(f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**测试版本**: Phase 1.x\n\n")
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
            details = r["details"][:80] + "..." if len(r["details"]) > 80 else r["details"]
            f.write(f"| {r['id']} | {r['name']} | {status} | {r['severity']} | {details} |\n")
        
        f.write("\n---\n\n")
        f.write("## QA 建议\n\n")
        
        if report["qa_conclusion"] == "PASS":
            f.write("✅ **趋势图功能测试全部通过**\n\n")
            f.write("功能表现：\n")
            f.write("- 数据聚合：按天/按月聚合正确\n")
            f.write("- 时间连续性：无断点，无交易日期显示为0\n")
            f.write("- 粒度切换：≤31天按天，>31天按月，自动切换\n")
            f.write("- 数据同步：新增/修改/删除后正确刷新\n")
            f.write("- 与统计页一致性：趋势图总额与汇总一致\n\n")
            f.write("**建议**: 可进入下一阶段开发\n")
        else:
            f.write("⚠️ **存在待修复问题**\n\n")
            for r in report["results"]:
                if not r["passed"]:
                    f.write(f"- **{r['id']}** [{r['severity']}]: {r['details']}\n")
        
        f.write("\n---\n\n")
        f.write("## 手动验证项\n\n")
        f.write("以下测试项需要手动验证：\n\n")
        f.write("### TC-TREND-011: 浅色模式可读性\n")
        f.write("- [ ] 折线、坐标轴、文字清晰\n")
        f.write("- [ ] 无颜色冲突\n")
        f.write("- [ ] 收入线（绿）与支出线（红）区分明显\n\n")
        f.write("### TC-TREND-012: 深色模式可读性\n")
        f.write("- [ ] 折线与背景对比明显\n")
        f.write("- [ ] 坐标刻度、图例、标题可读\n")
        f.write("- [ ] 不出现黑线黑底或白线白底\n\n")
        f.write("---\n\n")
        f.write("*报告生成时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "*\n")
    
    print(f"\n📄 测试报告已保存至: {report_path}")
    
    return 0 if report["qa_conclusion"] in ["PASS", "PASS_WITH_ISSUES"] else 1


if __name__ == "__main__":
    sys.exit(main())

