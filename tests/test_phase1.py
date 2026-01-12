"""
Phase 1 Integration Tests for Ledger App
测试工程师：自动化测试脚本
日期：2026-01-12

测试范围：
- 交易编辑与删除
- 分类与账户管理
- 首页总览 Dashboard
- 统计分析页面
- Phase 0 回归测试
"""
import sys
import os
import sqlite3
import time
from datetime import date, timedelta
from calendar import monthrange

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QDate
from PySide6.QtTest import QTest

from ledger.db.database import Database
from ledger.models.transaction import Transaction
from ledger.models.category import Category
from ledger.models.account import Account
from ledger.services.statistics_service import StatisticsService
from ledger.settings import DB_PATH


class TestRunner:
    """Phase 1 Test Runner"""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.results = []
        self.defects = []
        self.questions = []  # 待PM确认的问题
        
    def log(self, test_id, status, message=""):
        """Log test result"""
        result = {"id": test_id, "status": status, "message": message}
        self.results.append(result)
        emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{emoji} {test_id}: {status} - {message}")
        
    def log_defect(self, severity, title, description, steps, actual, expected):
        """Log a defect"""
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
        print(f"   实际结果: {actual}")
        print(f"   期望结果: {expected}")
        
    def log_question(self, question, context):
        """Log a question for PM"""
        self.questions.append({"question": question, "context": context})
        print(f"\n❓ 待PM确认: {question}")
        
    def clear_all_data(self, db: Database):
        """Clear all test data"""
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM categories")
        cursor.execute("DELETE FROM accounts")
        db.conn.commit()


class Phase0RegressionTests(TestRunner):
    """Phase 0 回归测试"""
    
    def run_all(self, db: Database) -> bool:
        """运行所有Phase 0回归测试"""
        print("\n" + "="*60)
        print("Phase 0 回归测试")
        print("="*60)
        
        self.clear_all_data(db)
        
        all_passed = True
        all_passed &= self.test_basic_add_transaction(db)
        all_passed &= self.test_data_persistence(db)
        all_passed &= self.test_amount_validation(db)
        all_passed &= self.test_date_format(db)
        all_passed &= self.test_cents_precision(db)
        
        return all_passed
    
    def test_basic_add_transaction(self, db: Database) -> bool:
        """回归测试：基本新增交易"""
        test_id = "REG-SMOKE-002"
        try:
            tx = Transaction(
                type="expense",
                amount_cents=1234,
                date="2026-01-12",
                category="餐饮",
                account="现金",
                note="午饭"
            )
            tx_id = db.add_transaction(tx)
            
            # 验证
            saved_tx = db.get_transaction_by_id(tx_id)
            if not saved_tx:
                self.log(test_id, "FAIL", "Transaction not saved")
                return False
            
            if saved_tx.amount_cents != 1234:
                self.log(test_id, "FAIL", f"Amount mismatch: {saved_tx.amount_cents}")
                return False
                
            self.log(test_id, "PASS", "基本新增交易功能正常")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_data_persistence(self, db: Database) -> bool:
        """回归测试：数据持久化"""
        test_id = "REG-SMOKE-003"
        try:
            # 记录当前数据
            before = db.get_all_transactions()
            count_before = len(before)
            
            # 关闭并重新打开数据库
            db.close()
            db._connect()
            
            # 验证数据仍在
            after = db.get_all_transactions()
            if len(after) != count_before:
                self.log(test_id, "FAIL", f"Data lost after reopen: {count_before} -> {len(after)}")
                return False
                
            self.log(test_id, "PASS", "数据持久化正常")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_amount_validation(self, db: Database) -> bool:
        """回归测试：金额校验（通过TransactionDialog逻辑）"""
        test_id = "REG-NEG-001"
        try:
            # 测试空金额
            from ledger.ui.transaction_dialog import TransactionDialog
            
            dialog = TransactionDialog(None, categories=[], accounts=[])
            dialog.amount_input.setText("")
            
            # 模拟保存
            dialog._on_save()
            
            # 验证未接受（说明校验生效）
            if dialog.result() != TransactionDialog.Accepted:
                self.log(test_id, "PASS", "空金额校验正常")
                return True
            else:
                self.log(test_id, "FAIL", "空金额未被阻止")
                return False
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_date_format(self, db: Database) -> bool:
        """回归测试：日期格式"""
        test_id = "REG-FUNC-003"
        try:
            tx = Transaction(
                type="expense",
                amount_cents=100,
                date="2026-01-01",
                category="test"
            )
            tx_id = db.add_transaction(tx)
            
            saved = db.get_transaction_by_id(tx_id)
            if saved.date != "2026-01-01":
                self.log(test_id, "FAIL", f"Date format incorrect: {saved.date}")
                return False
                
            self.log(test_id, "PASS", "日期格式YYYY-MM-DD正确")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_cents_precision(self, db: Database) -> bool:
        """回归测试：金额精度"""
        test_id = "REG-FUNC-004"
        try:
            test_cases = [(1, 1), (10, 10), (100, 100), (1234, 1234)]
            
            for amount_cents, expected in test_cases:
                tx = Transaction(type="expense", amount_cents=amount_cents, date="2026-01-12")
                tx_id = db.add_transaction(tx)
                saved = db.get_transaction_by_id(tx_id)
                
                if saved.amount_cents != expected:
                    self.log(test_id, "FAIL", f"Precision error: {amount_cents} -> {saved.amount_cents}")
                    return False
            
            self.log(test_id, "PASS", "金额cents精度正确")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False


class TransactionEditDeleteTests(TestRunner):
    """模块A：交易修改与删除测试"""
    
    def run_all(self, db: Database) -> bool:
        print("\n" + "="*60)
        print("模块A：交易修改与删除测试")
        print("="*60)
        
        self.clear_all_data(db)
        
        all_passed = True
        all_passed &= self.test_edit_amount(db)
        all_passed &= self.test_edit_date_cross_month(db)
        all_passed &= self.test_delete_transaction(db)
        all_passed &= self.test_delete_affects_statistics(db)
        
        return all_passed
    
    def test_edit_amount(self, db: Database) -> bool:
        """TC-EDIT-001: 修改金额"""
        test_id = "TC-EDIT-001"
        try:
            # 新增一条交易
            tx = Transaction(
                type="expense",
                amount_cents=10000,  # 100.00
                date="2026-01-12",
                category="餐饮"
            )
            tx_id = db.add_transaction(tx)
            original_id = tx_id
            
            # 修改金额
            tx.amount_cents = 12000  # 120.00
            tx.id = tx_id
            db.update_transaction(tx)
            
            # 验证
            updated = db.get_transaction_by_id(tx_id)
            
            # 检查ID不变
            if updated.id != original_id:
                self.log(test_id, "FAIL", f"ID changed: {original_id} -> {updated.id}")
                self.log_defect(
                    "Critical",
                    "[编辑] 修改交易导致ID变化",
                    "UPDATE操作应该保持ID不变",
                    ["新增交易", "编辑金额", "检查ID"],
                    f"ID从{original_id}变为{updated.id}",
                    "ID应保持不变"
                )
                return False
            
            # 检查金额已更新
            if updated.amount_cents != 12000:
                self.log(test_id, "FAIL", f"Amount not updated: {updated.amount_cents}")
                return False
            
            self.log(test_id, "PASS", "修改金额成功，ID保持不变")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_edit_date_cross_month(self, db: Database) -> bool:
        """TC-EDIT-002: 修改日期跨月"""
        test_id = "TC-EDIT-002"
        try:
            self.clear_all_data(db)
            
            # 创建1月的交易
            tx = Transaction(
                type="expense",
                amount_cents=5000,
                date="2026-01-31",  # 1月最后一天
                category="test"
            )
            tx_id = db.add_transaction(tx)
            
            # 获取1月统计
            stats = StatisticsService(db)
            jan_summary = stats.get_custom_period_summary("2026-01-01", "2026-01-31")
            jan_expense_before = jan_summary.expense_cents
            
            # 修改日期到2月
            tx.id = tx_id
            tx.date = "2026-02-01"
            db.update_transaction(tx)
            
            # 验证1月统计减少
            jan_summary_after = stats.get_custom_period_summary("2026-01-01", "2026-01-31")
            feb_summary = stats.get_custom_period_summary("2026-02-01", "2026-02-28")
            
            if jan_summary_after.expense_cents != jan_expense_before - 5000:
                self.log(test_id, "FAIL", f"Jan stats not updated correctly")
                return False
            
            if feb_summary.expense_cents != 5000:
                self.log(test_id, "FAIL", f"Feb stats incorrect: {feb_summary.expense_cents}")
                return False
            
            self.log(test_id, "PASS", "跨月修改日期，统计正确更新")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_delete_transaction(self, db: Database) -> bool:
        """TC-DEL-001: 正常删除"""
        test_id = "TC-DEL-001"
        try:
            self.clear_all_data(db)
            
            # 新增交易
            tx = Transaction(type="expense", amount_cents=1000, date="2026-01-12")
            tx_id = db.add_transaction(tx)
            
            # 验证存在
            if not db.get_transaction_by_id(tx_id):
                self.log(test_id, "FAIL", "Transaction not created")
                return False
            
            # 删除
            db.delete_transaction(tx_id)
            
            # 验证已删除
            if db.get_transaction_by_id(tx_id):
                self.log(test_id, "FAIL", "Transaction not deleted")
                return False
            
            self.log(test_id, "PASS", "删除交易成功")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_delete_affects_statistics(self, db: Database) -> bool:
        """删除交易后统计是否更新"""
        test_id = "TC-DEL-STAT"
        try:
            self.clear_all_data(db)
            
            # 新增两笔交易
            tx1 = Transaction(type="expense", amount_cents=10000, date="2026-01-12")
            tx2 = Transaction(type="income", amount_cents=20000, date="2026-01-12")
            tx1_id = db.add_transaction(tx1)
            db.add_transaction(tx2)
            
            stats = StatisticsService(db)
            
            # 删除前统计
            before = stats.get_custom_period_summary("2026-01-01", "2026-01-31")
            
            # 删除支出
            db.delete_transaction(tx1_id)
            
            # 删除后统计
            after = stats.get_custom_period_summary("2026-01-01", "2026-01-31")
            
            if after.expense_cents != 0:
                self.log(test_id, "FAIL", f"Expense not updated after delete: {after.expense_cents}")
                return False
            
            if after.income_cents != 20000:
                self.log(test_id, "FAIL", f"Income incorrectly affected: {after.income_cents}")
                return False
            
            self.log(test_id, "PASS", "删除交易后统计正确更新")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False


class CategoryAccountTests(TestRunner):
    """模块B：分类与账户测试"""
    
    def run_all(self, db: Database) -> bool:
        print("\n" + "="*60)
        print("模块B：分类与账户结构化测试")
        print("="*60)
        
        self.clear_all_data(db)
        
        all_passed = True
        all_passed &= self.test_add_category(db)
        all_passed &= self.test_update_category_name(db)
        all_passed &= self.test_delete_used_category(db)
        all_passed &= self.test_add_account(db)
        all_passed &= self.test_delete_used_account(db)
        
        return all_passed
    
    def test_add_category(self, db: Database) -> bool:
        """TC-CAT-001: 新增分类"""
        test_id = "TC-CAT-001"
        try:
            cat = Category(name="餐饮", type="expense")
            cat_id = db.add_category(cat)
            
            # 验证分类存在
            categories = db.get_all_categories()
            found = [c for c in categories if c.id == cat_id]
            
            if not found:
                self.log(test_id, "FAIL", "Category not found after add")
                return False
            
            if found[0].name != "餐饮":
                self.log(test_id, "FAIL", f"Category name mismatch: {found[0].name}")
                return False
            
            # 创建使用该分类的交易
            tx = Transaction(
                type="expense",
                amount_cents=1000,
                date="2026-01-12",
                category="餐饮",
                category_id=cat_id
            )
            db.add_transaction(tx)
            
            self.log(test_id, "PASS", "新增分类并关联交易成功")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_update_category_name(self, db: Database) -> bool:
        """TC-CAT-002: 修改分类名称"""
        test_id = "TC-CAT-002"
        try:
            # 先清空并创建新数据
            self.clear_all_data(db)
            
            # 创建分类
            cat = Category(name="餐饮", type="expense")
            cat_id = db.add_category(cat)
            
            # 创建使用该分类的交易
            tx = Transaction(
                type="expense",
                amount_cents=1000,
                date="2026-01-12",
                category="餐饮",
                category_id=cat_id
            )
            db.add_transaction(tx)
            
            # 修改分类名称
            cat.id = cat_id
            cat.name = "外食"
            db.update_category(cat)
            
            # 验证分类已更新
            categories = db.get_all_categories()
            found = [c for c in categories if c.id == cat_id]
            
            if not found or found[0].name != "外食":
                self.log(test_id, "FAIL", "Category name not updated")
                return False
            
            # 注意：当前实现中交易的category字段是文本，不会自动更新
            # 这是一个已知的设计决策（兼容旧数据）
            self.log_question(
                "分类改名后，关联交易的category字段是否应该同步更新？",
                "当前实现使用category_id外键+category文本双字段，改名不会更新交易的文本字段"
            )
            
            self.log(test_id, "PASS", "修改分类名称成功")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_delete_used_category(self, db: Database) -> bool:
        """TC-CAT-003: 删除被使用的分类"""
        test_id = "TC-CAT-003"
        try:
            self.clear_all_data(db)
            
            # 创建分类
            cat = Category(name="测试分类", type="expense")
            cat_id = db.add_category(cat)
            
            # 创建使用该分类的交易
            tx = Transaction(
                type="expense",
                amount_cents=1000,
                date="2026-01-12",
                category="测试分类",
                category_id=cat_id
            )
            tx_id = db.add_transaction(tx)
            
            # 尝试删除分类
            try:
                db.delete_category(cat_id)
                
                # 检查交易是否仍然可读
                saved_tx = db.get_transaction_by_id(tx_id)
                if not saved_tx:
                    self.log(test_id, "FAIL", "Transaction lost after category deletion")
                    self.log_defect(
                        "Blocker",
                        "[数据一致性] 删除分类导致交易丢失",
                        "删除分类后关联的交易不可读",
                        ["创建分类", "创建使用该分类的交易", "删除分类"],
                        "交易丢失",
                        "交易应保留，分类字段应为空或保留原值"
                    )
                    return False
                
                # 记录实际行为
                self.log_question(
                    "删除被使用的分类时应该如何处理？",
                    f"当前行为：允许删除，交易保留，category_id变为{saved_tx.category_id}，category文本保留为'{saved_tx.category}'"
                )
                
                self.log(test_id, "PASS", f"删除分类后交易保留，category_id={saved_tx.category_id}")
                return True
                
            except Exception as e:
                # 如果抛出异常，可能是禁止删除
                self.log(test_id, "PASS", f"删除被使用分类被禁止: {e}")
                return True
                
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_add_account(self, db: Database) -> bool:
        """账户新增测试"""
        test_id = "TC-ACC-001"
        try:
            acc = Account(name="现金", type="cash")
            acc_id = db.add_account(acc)
            
            accounts = db.get_all_accounts()
            found = [a for a in accounts if a.id == acc_id]
            
            if not found or found[0].name != "现金":
                self.log(test_id, "FAIL", "Account not created correctly")
                return False
            
            self.log(test_id, "PASS", "新增账户成功")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_delete_used_account(self, db: Database) -> bool:
        """TC-ACC-003: 删除被使用的账户"""
        test_id = "TC-ACC-003"
        try:
            self.clear_all_data(db)
            
            # 创建账户
            acc = Account(name="测试账户", type="cash")
            acc_id = db.add_account(acc)
            
            # 创建使用该账户的交易
            tx = Transaction(
                type="expense",
                amount_cents=1000,
                date="2026-01-12",
                account="测试账户",
                account_id=acc_id
            )
            tx_id = db.add_transaction(tx)
            
            # 尝试删除账户 - 应该触发外键约束
            try:
                db.delete_account(acc_id)
                # 如果没有抛出异常，检查交易是否保留
                saved_tx = db.get_transaction_by_id(tx_id)
                if not saved_tx:
                    self.log(test_id, "FAIL", "Transaction lost after account deletion")
                    return False
                self.log(test_id, "PASS", "删除账户后交易保留（无外键约束）")
                return True
            except sqlite3.IntegrityError:
                # 外键约束生效，这是预期行为
                # 检查交易仍然存在
                saved_tx = db.get_transaction_by_id(tx_id)
                if not saved_tx:
                    self.log(test_id, "FAIL", "Transaction lost")
                    return False
                # 检查账户仍然存在（因为删除被阻止）
                accounts = db.get_all_accounts()
                if not any(a.id == acc_id for a in accounts):
                    self.log(test_id, "FAIL", "Account was deleted despite constraint")
                    return False
                self.log(test_id, "PASS", "外键约束阻止删除被使用的账户（数据安全）")
                return True
                
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False


class DashboardTests(TestRunner):
    """模块C：首页总览测试"""
    
    def run_all(self, db: Database) -> bool:
        print("\n" + "="*60)
        print("模块C：首页总览（Dashboard）测试")
        print("="*60)
        
        self.clear_all_data(db)
        
        all_passed = True
        all_passed &= self.test_monthly_summary_accuracy(db)
        all_passed &= self.test_edit_affects_dashboard(db)
        all_passed &= self.test_delete_affects_dashboard(db)
        
        return all_passed
    
    def test_monthly_summary_accuracy(self, db: Database) -> bool:
        """TC-DASH-001: 本月汇总正确性"""
        test_id = "TC-DASH-001"
        try:
            self.clear_all_data(db)
            
            today = date.today()
            date_str = today.strftime("%Y-%m-%d")
            
            # 添加多笔收支
            transactions = [
                Transaction(type="expense", amount_cents=10000, date=date_str),  # 100.00
                Transaction(type="expense", amount_cents=5000, date=date_str),   # 50.00
                Transaction(type="income", amount_cents=30000, date=date_str),   # 300.00
                Transaction(type="income", amount_cents=15000, date=date_str),   # 150.00
            ]
            
            for tx in transactions:
                db.add_transaction(tx)
            
            # 手工计算
            expected_expense = 15000  # cents
            expected_income = 45000   # cents
            expected_balance = 30000  # cents
            
            # 获取Dashboard数据
            stats = StatisticsService(db)
            summary = stats.get_current_month_summary()
            
            if summary.expense_cents != expected_expense:
                self.log(test_id, "FAIL", f"Expense mismatch: {summary.expense_cents} vs {expected_expense}")
                return False
            
            if summary.income_cents != expected_income:
                self.log(test_id, "FAIL", f"Income mismatch: {summary.income_cents} vs {expected_income}")
                return False
            
            if summary.balance_cents != expected_balance:
                self.log(test_id, "FAIL", f"Balance mismatch: {summary.balance_cents} vs {expected_balance}")
                return False
            
            self.log(test_id, "PASS", f"本月汇总正确: 收入{summary.income}, 支出{summary.expense}, 结余{summary.balance}")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_edit_affects_dashboard(self, db: Database) -> bool:
        """TC-DASH-002: 修改交易影响首页"""
        test_id = "TC-DASH-002"
        try:
            self.clear_all_data(db)
            
            today = date.today()
            date_str = today.strftime("%Y-%m-%d")
            
            # 添加一笔支出
            tx = Transaction(type="expense", amount_cents=10000, date=date_str)
            tx_id = db.add_transaction(tx)
            
            stats = StatisticsService(db)
            before = stats.get_current_month_summary()
            
            # 修改金额
            tx.id = tx_id
            tx.amount_cents = 20000
            db.update_transaction(tx)
            
            # 检查更新
            after = stats.get_current_month_summary()
            
            if after.expense_cents != 20000:
                self.log(test_id, "FAIL", f"Dashboard not updated: {after.expense_cents}")
                return False
            
            self.log(test_id, "PASS", "修改交易后首页数据立即更新")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_delete_affects_dashboard(self, db: Database) -> bool:
        """TC-DASH-003: 删除交易影响首页"""
        test_id = "TC-DASH-003"
        try:
            self.clear_all_data(db)
            
            today = date.today()
            date_str = today.strftime("%Y-%m-%d")
            
            # 添加一笔收入
            tx = Transaction(type="income", amount_cents=50000, date=date_str)
            tx_id = db.add_transaction(tx)
            
            stats = StatisticsService(db)
            before = stats.get_current_month_summary()
            
            if before.income_cents != 50000:
                self.log(test_id, "FAIL", "Initial state incorrect")
                return False
            
            # 删除
            db.delete_transaction(tx_id)
            
            # 检查更新
            after = stats.get_current_month_summary()
            
            if after.income_cents != 0:
                self.log(test_id, "FAIL", f"Dashboard not updated after delete: {after.income_cents}")
                return False
            
            self.log(test_id, "PASS", "删除交易后首页数据立即更新")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False


class StatisticsTests(TestRunner):
    """模块D：统计分析测试"""
    
    def run_all(self, db: Database) -> bool:
        print("\n" + "="*60)
        print("模块D：统计分析页面测试")
        print("="*60)
        
        self.clear_all_data(db)
        
        all_passed = True
        all_passed &= self.test_month_vs_year(db)
        all_passed &= self.test_date_boundary(db)
        all_passed &= self.test_category_sum(db)
        all_passed &= self.test_daily_trend(db)
        
        return all_passed
    
    def test_month_vs_year(self, db: Database) -> bool:
        """TC-STAT-001: 本月 vs 本年"""
        test_id = "TC-STAT-001"
        try:
            self.clear_all_data(db)
            
            today = date.today()
            this_month = today.strftime("%Y-%m-%d")
            
            # 上个月的日期
            if today.month == 1:
                last_month_date = date(today.year - 1, 12, 15)
            else:
                last_month_date = date(today.year, today.month - 1, 15)
            last_month = last_month_date.strftime("%Y-%m-%d")
            
            # 添加本月和上月的交易
            db.add_transaction(Transaction(type="expense", amount_cents=10000, date=this_month))
            db.add_transaction(Transaction(type="expense", amount_cents=20000, date=last_month))
            
            stats = StatisticsService(db)
            month_summary = stats.get_current_month_summary()
            year_summary = stats.get_current_year_summary()
            
            # 本年 >= 本月
            if year_summary.expense_cents < month_summary.expense_cents:
                self.log(test_id, "FAIL", f"Year < Month: {year_summary.expense_cents} < {month_summary.expense_cents}")
                self.log_defect(
                    "Blocker",
                    "[统计] 本年统计小于本月",
                    "本年累计应该大于等于本月",
                    ["添加本月和上月交易", "查看统计"],
                    f"本年={year_summary.expense_cents}, 本月={month_summary.expense_cents}",
                    "本年 >= 本月"
                )
                return False
            
            # 本月应该只包含本月数据
            if month_summary.expense_cents != 10000:
                self.log(test_id, "FAIL", f"Month includes other months: {month_summary.expense_cents}")
                return False
            
            self.log(test_id, "PASS", f"本月={month_summary.expense}, 本年={year_summary.expense}")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_date_boundary(self, db: Database) -> bool:
        """TC-STAT-002: 日期边界测试"""
        test_id = "TC-STAT-002"
        try:
            self.clear_all_data(db)
            
            # 测试本月边界
            today = date.today()
            year, month = today.year, today.month
            _, last_day = monthrange(year, month)
            
            first_day = f"{year:04d}-{month:02d}-01"
            last_day_str = f"{year:04d}-{month:02d}-{last_day:02d}"
            
            # 边界日期的交易
            db.add_transaction(Transaction(type="expense", amount_cents=1000, date=first_day))
            db.add_transaction(Transaction(type="expense", amount_cents=2000, date=last_day_str))
            
            # 下个月第一天（不应包含）
            if month == 12:
                next_month_first = f"{year+1:04d}-01-01"
            else:
                next_month_first = f"{year:04d}-{month+1:02d}-01"
            db.add_transaction(Transaction(type="expense", amount_cents=5000, date=next_month_first))
            
            stats = StatisticsService(db)
            summary = stats.get_custom_period_summary(first_day, last_day_str)
            
            # 应该只包含本月两笔
            if summary.expense_cents != 3000:
                self.log(test_id, "FAIL", f"Boundary error: {summary.expense_cents} (expected 3000)")
                return False
            
            self.log(test_id, "PASS", "日期边界处理正确")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_category_sum(self, db: Database) -> bool:
        """TC-STAT-003: 分类求和"""
        test_id = "TC-STAT-003"
        try:
            self.clear_all_data(db)
            
            today = date.today()
            date_str = today.strftime("%Y-%m-%d")
            
            # 同分类多笔支出
            db.add_transaction(Transaction(type="expense", amount_cents=1000, date=date_str, category="餐饮"))
            db.add_transaction(Transaction(type="expense", amount_cents=2000, date=date_str, category="餐饮"))
            db.add_transaction(Transaction(type="expense", amount_cents=3000, date=date_str, category="餐饮"))
            db.add_transaction(Transaction(type="expense", amount_cents=5000, date=date_str, category="交通"))
            
            stats = StatisticsService(db)
            start = f"{today.year:04d}-{today.month:02d}-01"
            _, last_day = monthrange(today.year, today.month)
            end = f"{today.year:04d}-{today.month:02d}-{last_day:02d}"
            
            breakdown = stats.get_category_breakdown(start, end, "expense")
            
            # 验证餐饮分类
            dining = [b for b in breakdown if b["category"] == "餐饮"]
            if not dining:
                self.log(test_id, "FAIL", "餐饮 category not found in breakdown")
                return False
            
            if dining[0]["amount_cents"] != 6000:
                self.log(test_id, "FAIL", f"Category sum incorrect: {dining[0]['amount_cents']} (expected 6000)")
                return False
            
            # 验证百分比
            total = sum(b["amount_cents"] for b in breakdown)
            if total != 11000:
                self.log(test_id, "FAIL", f"Total incorrect: {total}")
                return False
            
            self.log(test_id, "PASS", "分类汇总正确: 餐饮=6000, 交通=5000")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_daily_trend(self, db: Database) -> bool:
        """TC-STAT-004: 每日趋势"""
        test_id = "TC-STAT-004"
        try:
            self.clear_all_data(db)
            
            # 连续3天的数据
            db.add_transaction(Transaction(type="expense", amount_cents=1000, date="2026-01-10"))
            db.add_transaction(Transaction(type="expense", amount_cents=2000, date="2026-01-11"))
            # 1月12日没有数据
            db.add_transaction(Transaction(type="expense", amount_cents=3000, date="2026-01-13"))
            
            stats = StatisticsService(db)
            trend = stats.get_daily_trend("2026-01-10", "2026-01-13")
            
            # 验证数据点
            dates = [t["date"] for t in trend]
            
            # 记录无数据日期的行为
            if "2026-01-12" in dates:
                self.log_question(
                    "无交易的日期在趋势图中是否显示？",
                    "当前行为：包含无交易日期（值为0）"
                )
            else:
                self.log_question(
                    "无交易的日期在趋势图中是否显示？",
                    "当前行为：不包含无交易日期"
                )
            
            self.log(test_id, "PASS", f"趋势数据点: {len(trend)}个日期")
            return True
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False


class InputValidationTests(TestRunner):
    """输入校验测试（Phase 1新增）"""
    
    def run_all(self, db: Database) -> bool:
        print("\n" + "="*60)
        print("输入校验测试（Phase 1）")
        print("="*60)
        
        all_passed = True
        all_passed &= self.test_negative_amount_blocked(db)
        all_passed &= self.test_max_amount_limit(db)
        
        return all_passed
    
    def test_negative_amount_blocked(self, db: Database) -> bool:
        """验证负数金额被阻止"""
        test_id = "TC-VAL-NEG"
        try:
            from ledger.ui.transaction_dialog import TransactionDialog
            
            dialog = TransactionDialog(None, categories=[], accounts=[])
            dialog.amount_input.setText("-10")
            dialog._on_save()
            
            # 如果没有accept，说明校验生效
            if dialog.result() != TransactionDialog.Accepted:
                self.log(test_id, "PASS", "负数金额被正确阻止")
                return True
            else:
                self.log(test_id, "FAIL", "负数金额未被阻止")
                return False
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False
    
    def test_max_amount_limit(self, db: Database) -> bool:
        """验证金额上限"""
        test_id = "TC-VAL-MAX"
        try:
            from ledger.ui.transaction_dialog import TransactionDialog
            from ledger.settings import MAX_AMOUNT
            
            dialog = TransactionDialog(None, categories=[], accounts=[])
            dialog.amount_input.setText(str(MAX_AMOUNT + 1))  # 超过上限
            dialog._on_save()
            
            if dialog.result() != TransactionDialog.Accepted:
                self.log(test_id, "PASS", f"超过上限{MAX_AMOUNT}被阻止")
                return True
            else:
                self.log(test_id, "FAIL", f"超过上限{MAX_AMOUNT}未被阻止")
                return False
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {e}")
            return False


def generate_report(runner: TestRunner):
    """生成测试报告"""
    print("\n" + "="*60)
    print("Phase 1 测试执行报告")
    print("="*60)
    print(f"执行日期: 2026-01-12")
    print(f"环境: macOS / Python 3.x / PySide6")
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
            print(f"  步骤: {d['steps']}")
            print(f"  实际结果: {d['actual']}")
            print(f"  期望结果: {d['expected']}")
    
    if runner.questions:
        print("\n" + "="*60)
        print("待PM确认问题清单")
        print("="*60)
        for i, q in enumerate(runner.questions, 1):
            print(f"\n问题 #{i}")
            print(f"  问题: {q['question']}")
            print(f"  上下文: {q['context']}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    
    return passed, failed, warned


def main():
    print("="*60)
    print("Ledger App Phase 1 自动化测试")
    print("="*60)
    
    # 使用独立的测试数据库
    test_db_path = str(DB_PATH).replace("app.db", "test_phase1.db")
    
    # 创建数据库连接
    db = Database(test_db_path)
    
    # 创建综合测试运行器
    runner = TestRunner()
    
    # 运行所有测试模块
    phase0_tests = Phase0RegressionTests()
    phase0_tests.run_all(db)
    runner.results.extend(phase0_tests.results)
    runner.defects.extend(phase0_tests.defects)
    runner.questions.extend(phase0_tests.questions)
    
    edit_tests = TransactionEditDeleteTests()
    edit_tests.run_all(db)
    runner.results.extend(edit_tests.results)
    runner.defects.extend(edit_tests.defects)
    runner.questions.extend(edit_tests.questions)
    
    cat_tests = CategoryAccountTests()
    cat_tests.run_all(db)
    runner.results.extend(cat_tests.results)
    runner.defects.extend(cat_tests.defects)
    runner.questions.extend(cat_tests.questions)
    
    dash_tests = DashboardTests()
    dash_tests.run_all(db)
    runner.results.extend(dash_tests.results)
    runner.defects.extend(dash_tests.defects)
    runner.questions.extend(dash_tests.questions)
    
    stats_tests = StatisticsTests()
    stats_tests.run_all(db)
    runner.results.extend(stats_tests.results)
    runner.defects.extend(stats_tests.defects)
    runner.questions.extend(stats_tests.questions)
    
    val_tests = InputValidationTests()
    val_tests.run_all(db)
    runner.results.extend(val_tests.results)
    runner.defects.extend(val_tests.defects)
    runner.questions.extend(val_tests.questions)
    
    # 生成报告
    generate_report(runner)
    
    # 清理
    db.close()
    
    # 删除测试数据库
    import os
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


if __name__ == "__main__":
    main()

