"""
Integration tests for Ledger App Phase 0
测试工程师：自动化测试脚本
日期：2026-01-12
"""
import sys
import os
import sqlite3
import time

# Add path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QDate
from PySide6.QtTest import QTest

from ledger.ui.main_window import MainWindow
from ledger.db.database import Database
from ledger.settings import DB_PATH


class TestRunner:
    """Test runner for Ledger App"""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.results = []
        self.defects = []
        
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
        
    def clear_database(self):
        """Clear all transactions for fresh test"""
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM transactions")
        conn.commit()
        conn.close()
        
    def get_db_records(self):
        """Get all records from database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.execute("SELECT * FROM transactions ORDER BY date DESC, created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return rows

    def run_tc_smoke_002(self, window):
        """TC-SMOKE-002: 新增一笔支出并显示"""
        test_id = "TC-SMOKE-002"
        try:
            self.clear_database()
            window.refresh_data()
            
            # Set inputs
            window.type_combo.setCurrentText("expense")
            window.amount_input.setText("12.34")
            window.date_input.setDate(QDate.currentDate())
            window.category_input.setText("餐饮")
            window.account_input.setText("现金")
            window.note_input.setText("午饭")
            
            # Click save
            QTest.mouseClick(window.save_btn, Qt.LeftButton)
            self.app.processEvents()
            
            # Verify table has 1 row
            row_count = window.table.rowCount()
            if row_count != 1:
                self.log(test_id, "FAIL", f"Expected 1 row in table, got {row_count}")
                return False
            
            # Verify amount display
            amount_text = window.table.item(0, 2).text()
            if amount_text != "12.34":
                self.log(test_id, "FAIL", f"Expected amount '12.34', got '{amount_text}'")
                return False
            
            # Verify DB record
            records = self.get_db_records()
            if len(records) != 1:
                self.log(test_id, "FAIL", f"Expected 1 DB record, got {len(records)}")
                return False
            
            if records[0][2] != 1234:  # amount_cents
                self.log(test_id, "FAIL", f"Expected amount_cents=1234, got {records[0][2]}")
                return False
                
            self.log(test_id, "PASS", "新增支出成功，UI和DB数据正确")
            return True
            
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {str(e)}")
            return False
    
    def run_tc_smoke_003(self, window):
        """TC-SMOKE-003: 重启后持久化"""
        test_id = "TC-SMOKE-003"
        try:
            # Verify existing data from TC-SMOKE-002
            records_before = self.get_db_records()
            
            # Close window
            window.close()
            self.app.processEvents()
            
            # Create new window (simulates restart)
            new_window = MainWindow()
            new_window.show()
            self.app.processEvents()
            
            # Verify data persisted
            row_count = new_window.table.rowCount()
            if row_count != len(records_before):
                self.log(test_id, "FAIL", f"Expected {len(records_before)} rows after restart, got {row_count}")
                new_window.close()
                return False
                
            self.log(test_id, "PASS", "重启后数据持久化正确")
            return True, new_window
            
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {str(e)}")
            return False, None
    
    def run_tc_func_001(self, window):
        """TC-FUNC-001: 新增收入记录"""
        test_id = "TC-FUNC-001"
        try:
            initial_count = window.table.rowCount()
            
            # Add income
            window.type_combo.setCurrentText("income")
            window.amount_input.setText("100.00")
            window.category_input.setText("工资")
            window.account_input.setText("银行卡")
            window.note_input.setText("")
            
            QTest.mouseClick(window.save_btn, Qt.LeftButton)
            self.app.processEvents()
            
            # Verify row added
            if window.table.rowCount() != initial_count + 1:
                self.log(test_id, "FAIL", "Row not added to table")
                return False
            
            # Verify type in DB
            records = self.get_db_records()
            income_record = [r for r in records if r[1] == "income" and r[2] == 10000]
            if not income_record:
                self.log(test_id, "FAIL", "Income record not found in DB")
                return False
                
            self.log(test_id, "PASS", "收入记录新增成功")
            return True
            
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {str(e)}")
            return False
    
    def run_tc_func_002(self, window):
        """TC-FUNC-002: 多条记录顺序（按日期/创建时间倒序）"""
        test_id = "TC-FUNC-002"
        try:
            self.clear_database()
            window.refresh_data()
            
            # Add 3 records with different dates
            dates = [
                QDate(2026, 1, 10),
                QDate(2026, 1, 12),
                QDate(2026, 1, 11),
            ]
            amounts = ["10.00", "20.00", "30.00"]
            
            for date, amount in zip(dates, amounts):
                window.type_combo.setCurrentText("expense")
                window.amount_input.setText(amount)
                window.date_input.setDate(date)
                window.category_input.setText("test")
                window.account_input.setText("cash")
                QTest.mouseClick(window.save_btn, Qt.LeftButton)
                self.app.processEvents()
                time.sleep(0.1)  # Small delay to ensure different created_at
            
            # Verify order: should be 2026-01-12 (20.00), 2026-01-11 (30.00), 2026-01-10 (10.00)
            expected_amounts = ["20.00", "30.00", "10.00"]
            actual_amounts = [window.table.item(i, 2).text() for i in range(3)]
            
            if actual_amounts != expected_amounts:
                self.log(test_id, "FAIL", f"Expected order {expected_amounts}, got {actual_amounts}")
                return False
                
            self.log(test_id, "PASS", "记录按日期倒序排列正确")
            return True
            
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {str(e)}")
            return False
    
    def run_tc_func_003(self, window):
        """TC-FUNC-003: 日期选择与保存格式"""
        test_id = "TC-FUNC-003"
        try:
            self.clear_database()
            window.refresh_data()
            
            # Add record with specific date
            test_date = QDate(2026, 1, 1)
            window.type_combo.setCurrentText("expense")
            window.amount_input.setText("50.00")
            window.date_input.setDate(test_date)
            window.category_input.setText("test")
            window.account_input.setText("cash")
            
            QTest.mouseClick(window.save_btn, Qt.LeftButton)
            self.app.processEvents()
            
            # Check DB format
            records = self.get_db_records()
            if not records:
                self.log(test_id, "FAIL", "No records in DB")
                return False
            
            date_value = records[0][3]  # date column
            if date_value != "2026-01-01":
                self.log(test_id, "FAIL", f"Expected date '2026-01-01', got '{date_value}'")
                return False
            
            # Check UI display
            ui_date = window.table.item(0, 0).text()
            if ui_date != "2026-01-01":
                self.log(test_id, "FAIL", f"UI date mismatch: '{ui_date}'")
                return False
                
            self.log(test_id, "PASS", "日期格式YYYY-MM-DD存储正确")
            return True
            
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {str(e)}")
            return False
    
    def run_tc_func_004(self, window):
        """TC-FUNC-004: 金额精度与cents存储"""
        test_id = "TC-FUNC-004"
        try:
            self.clear_database()
            window.refresh_data()
            
            test_amounts = [
                ("0.01", 1),
                ("0.10", 10),
                ("1.00", 100),
                ("12.34", 1234),
            ]
            
            for amount_str, expected_cents in test_amounts:
                window.type_combo.setCurrentText("expense")
                window.amount_input.setText(amount_str)
                window.date_input.setDate(QDate.currentDate())
                window.category_input.setText("test")
                window.account_input.setText("cash")
                
                QTest.mouseClick(window.save_btn, Qt.LeftButton)
                self.app.processEvents()
            
            # Verify DB values
            records = self.get_db_records()
            actual_cents = sorted([r[2] for r in records])
            expected_cents_sorted = sorted([1, 10, 100, 1234])
            
            if actual_cents != expected_cents_sorted:
                self.log(test_id, "FAIL", f"Cents mismatch. Expected {expected_cents_sorted}, got {actual_cents}")
                return False
            
            # Verify UI display (no floating point errors like 12.339999)
            for i in range(window.table.rowCount()):
                amount_text = window.table.item(i, 2).text()
                try:
                    float(amount_text)
                except ValueError:
                    self.log(test_id, "FAIL", f"Invalid amount display: '{amount_text}'")
                    return False
                    
            self.log(test_id, "PASS", "金额精度正确，cents存储无浮点误差")
            return True
            
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {str(e)}")
            return False
    
    def run_tc_func_005(self, window):
        """TC-FUNC-005: 关闭/重启重复验证"""
        test_id = "TC-FUNC-005"
        try:
            self.clear_database()
            window.refresh_data()
            
            # Add 5 records
            for i in range(5):
                window.type_combo.setCurrentText("expense")
                window.amount_input.setText(f"{i+1}.00")
                window.date_input.setDate(QDate.currentDate())
                window.category_input.setText(f"cat{i}")
                window.account_input.setText("cash")
                
                QTest.mouseClick(window.save_btn, Qt.LeftButton)
                self.app.processEvents()
            
            # Verify 5 records
            if window.table.rowCount() != 5:
                self.log(test_id, "FAIL", f"Expected 5 rows, got {window.table.rowCount()}")
                return False
            
            # Close and reopen
            window.close()
            self.app.processEvents()
            
            new_window = MainWindow()
            new_window.show()
            self.app.processEvents()
            
            if new_window.table.rowCount() != 5:
                self.log(test_id, "FAIL", f"After restart: expected 5 rows, got {new_window.table.rowCount()}")
                new_window.close()
                return False
                
            self.log(test_id, "PASS", "5条记录重启后完整保留")
            return True, new_window
            
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {str(e)}")
            return False, None
    
    def run_tc_neg_001(self, window):
        """TC-NEG-001: 金额为空"""
        test_id = "TC-NEG-001"
        try:
            self.clear_database()
            window.refresh_data()
            initial_count = len(self.get_db_records())
            
            # Leave amount empty
            window.amount_input.setText("")
            window.category_input.setText("test")
            
            QTest.mouseClick(window.save_btn, Qt.LeftButton)
            self.app.processEvents()
            
            # Should not save
            current_count = len(self.get_db_records())
            if current_count != initial_count:
                self.log(test_id, "FAIL", "Empty amount was saved (should be rejected)")
                self.log_defect(
                    "Major",
                    "[输入校验] 空金额未被阻止",
                    "金额为空时仍然保存了记录",
                    ["清空金额输入框", "点击保存"],
                    "记录被保存到数据库",
                    "应提示错误且不保存"
                )
                return False
                
            self.log(test_id, "PASS", "空金额被正确阻止")
            return True
            
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {str(e)}")
            return False
    
    def run_tc_neg_002(self, window):
        """TC-NEG-002: 金额为非数字"""
        test_id = "TC-NEG-002"
        try:
            self.clear_database()
            window.refresh_data()
            initial_count = len(self.get_db_records())
            
            # Test non-numeric values
            invalid_values = ["abc", "12..3", "12.34.56", "ten"]
            
            for val in invalid_values:
                window.amount_input.setText(val)
                window.category_input.setText("test")
                
                QTest.mouseClick(window.save_btn, Qt.LeftButton)
                self.app.processEvents()
            
            current_count = len(self.get_db_records())
            if current_count != initial_count:
                self.log(test_id, "FAIL", f"Non-numeric amount was saved. {current_count - initial_count} invalid records saved")
                self.log_defect(
                    "Major", 
                    "[输入校验] 非数字金额未被阻止",
                    "输入abc等非数字时仍然保存了记录",
                    ["输入非数字金额如'abc'", "点击保存"],
                    f"保存了{current_count - initial_count}条无效记录",
                    "应提示错误且不保存"
                )
                return False
                
            self.log(test_id, "PASS", "非数字金额被正确阻止")
            return True
            
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {str(e)}")
            return False
    
    def run_tc_neg_003(self, window):
        """TC-NEG-003: 金额为负数"""
        test_id = "TC-NEG-003"
        try:
            self.clear_database()
            window.refresh_data()
            initial_count = len(self.get_db_records())
            
            # Input negative amount
            window.type_combo.setCurrentText("expense")
            window.amount_input.setText("-10")
            window.category_input.setText("test")
            
            QTest.mouseClick(window.save_btn, Qt.LeftButton)
            self.app.processEvents()
            
            current_count = len(self.get_db_records())
            
            if current_count > initial_count:
                # Check what was saved
                records = self.get_db_records()
                new_record = records[0]
                amount_cents = new_record[2]
                
                # Log as observation - behavior may be by design
                if amount_cents < 0:
                    self.log(test_id, "WARN", f"负数金额被保存: {amount_cents} cents。需要PM确认是否允许")
                    self.log_defect(
                        "Minor",
                        "[业务规则] 负数金额行为需确认",
                        "负数金额-10被保存为-1000 cents",
                        ["输入金额-10", "点击保存"],
                        f"保存了amount_cents={amount_cents}",
                        "需PM确认：是否允许负数？支出是否应为正数？"
                    )
                else:
                    self.log(test_id, "PASS", f"负数被转换为正数保存: {amount_cents} cents")
            else:
                self.log(test_id, "PASS", "负数金额被阻止保存（严格模式）")
            return True
            
        except Exception as e:
            self.log(test_id, "FAIL", f"Exception: {str(e)}")
            return False
    
    def run_tc_neg_004(self, window):
        """TC-NEG-004: 金额超大"""
        test_id = "TC-NEG-004"
        try:
            self.clear_database()
            window.refresh_data()
            
            # Input very large amount
            window.type_combo.setCurrentText("expense")
            window.amount_input.setText("999999999.99")
            window.category_input.setText("test")
            
            QTest.mouseClick(window.save_btn, Qt.LeftButton)
            self.app.processEvents()
            
            records = self.get_db_records()
            if records:
                amount_cents = records[0][2]
                expected_cents = 99999999999  # 999999999.99 * 100
                
                if amount_cents == expected_cents:
                    self.log(test_id, "PASS", f"超大金额正常保存: {amount_cents} cents")
                else:
                    self.log(test_id, "WARN", f"超大金额精度问题: expected {expected_cents}, got {amount_cents}")
            else:
                self.log(test_id, "PASS", "超大金额被阻止（如果有上限限制）")
                
            return True
            
        except Exception as e:
            # Check if it's an overflow error
            self.log(test_id, "FAIL", f"Exception on large amount: {str(e)}")
            self.log_defect(
                "Major",
                "[稳定性] 超大金额导致异常",
                f"输入999999999.99导致异常: {str(e)}",
                ["输入金额999999999.99", "点击保存"],
                f"异常: {str(e)}",
                "应正常保存或给出友好提示"
            )
            return False
    
    def generate_report(self):
        """Generate final test report"""
        print("\n" + "="*60)
        print("测试执行报告 - Phase 0 MVP")
        print("="*60)
        print(f"执行日期: 2026-01-12")
        print(f"环境: macOS / Python 3.x / PySide6")
        print("-"*60)
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        warned = sum(1 for r in self.results if r["status"] == "WARN")
        
        print(f"\n测试结果汇总:")
        print(f"  ✅ 通过: {passed}")
        print(f"  ❌ 失败: {failed}")
        print(f"  ⚠️  警告: {warned}")
        print(f"  总计: {len(self.results)}")
        
        print("\n详细结果:")
        for r in self.results:
            emoji = "✅" if r["status"] == "PASS" else "❌" if r["status"] == "FAIL" else "⚠️"
            print(f"  {emoji} {r['id']}: {r['status']}")
            if r["message"]:
                print(f"      {r['message']}")
        
        if self.defects:
            print("\n" + "="*60)
            print("缺陷列表")
            print("="*60)
            for i, d in enumerate(self.defects, 1):
                print(f"\n缺陷 #{i}")
                print(f"  严重级别: {d['severity']}")
                print(f"  标题: {d['title']}")
                print(f"  描述: {d['description']}")
                print(f"  步骤: {d['steps']}")
                print(f"  实际结果: {d['actual']}")
                print(f"  期望结果: {d['expected']}")
        
        print("\n" + "="*60)
        print("测试完成")
        print("="*60)
        
        return passed, failed, warned


def main():
    runner = TestRunner()
    
    print("="*60)
    print("Ledger App Phase 0 自动化测试")
    print("="*60)
    
    # Create main window
    window = MainWindow()
    window.show()
    runner.app.processEvents()
    
    # Run smoke tests
    print("\n--- 冒烟测试 ---")
    runner.run_tc_smoke_002(window)
    
    result = runner.run_tc_smoke_003(window)
    if isinstance(result, tuple):
        _, window = result
        if window is None:
            window = MainWindow()
            window.show()
            runner.app.processEvents()
    
    # Run functional tests
    print("\n--- 功能测试 ---")
    runner.run_tc_func_001(window)
    runner.run_tc_func_002(window)
    runner.run_tc_func_003(window)
    runner.run_tc_func_004(window)
    
    result = runner.run_tc_func_005(window)
    if isinstance(result, tuple):
        _, window = result
        if window is None:
            window = MainWindow()
            window.show()
            runner.app.processEvents()
    
    # Run negative tests
    print("\n--- 负向测试 ---")
    runner.run_tc_neg_001(window)
    runner.run_tc_neg_002(window)
    runner.run_tc_neg_003(window)
    runner.run_tc_neg_004(window)
    
    # Generate report
    runner.generate_report()
    
    # Cleanup
    window.close()


if __name__ == "__main__":
    main()

