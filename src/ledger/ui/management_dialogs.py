"""分类和账户管理对话框模块"""
import sqlite3
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox,
    QTabWidget, QWidget
)
from PySide6.QtCore import Qt

from ledger.db.database import Database
from ledger.models.category import Category
from ledger.models.account import Account
from ledger.settings import CATEGORY_TYPES, ACCOUNT_TYPES


class SettingsDialog(QDialog):
    """设置对话框（包含分类和账户管理）"""
    
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("设置")
        self.setMinimumSize(600, 450)
        self._init_ui()
    
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # 标签页
        tab_widget = QTabWidget()
        
        # 分类管理
        self.category_widget = CategoryManagementWidget(self.db)
        tab_widget.addTab(self.category_widget, "分类管理")
        
        # 账户管理
        self.account_widget = AccountManagementWidget(self.db)
        tab_widget.addTab(self.account_widget, "账户管理")
        
        layout.addWidget(tab_widget)
        
        # 关闭按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)


class CategoryManagementWidget(QWidget):
    """分类管理组件"""
    
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._editing_id: Optional[int] = None
        self._init_ui()
        self._load_data()
    
    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        
        # 左侧：分类列表
        left_layout = QVBoxLayout()
        self.category_list = QListWidget()
        self.category_list.currentRowChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.category_list)
        
        list_btn_layout = QHBoxLayout()
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.setEnabled(False)
        list_btn_layout.addWidget(self.delete_btn)
        list_btn_layout.addStretch()
        left_layout.addLayout(list_btn_layout)
        
        layout.addLayout(left_layout, 1)
        
        # 右侧：编辑表单
        right_layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        form_layout.addRow("名称:", self.name_input)
        
        self.type_combo = QComboBox()
        for type_id, type_name in CATEGORY_TYPES.items():
            self.type_combo.addItem(type_name, type_id)
        form_layout.addRow("类型:", self.type_combo)
        
        right_layout.addLayout(form_layout)
        
        self.save_btn = QPushButton("新增分类")
        self.save_btn.clicked.connect(self._on_save)
        right_layout.addWidget(self.save_btn)
        right_layout.addStretch()
        
        layout.addLayout(right_layout, 1)
    
    def _load_data(self) -> None:
        self.category_list.clear()
        for cat in self.db.get_all_categories():
            type_label = CATEGORY_TYPES.get(cat.type, cat.type)
            item = QListWidgetItem(f"{cat.name} [{type_label}]")
            item.setData(Qt.UserRole, cat)
            self.category_list.addItem(item)
    
    def _on_selection_changed(self, row: int) -> None:
        self.delete_btn.setEnabled(row >= 0)
        if row >= 0:
            cat: Category = self.category_list.item(row).data(Qt.UserRole)
            self.name_input.setText(cat.name)
            idx = self.type_combo.findData(cat.type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            self.save_btn.setText("更新分类")
            self._editing_id = cat.id
        else:
            self._clear_form()
    
    def _clear_form(self) -> None:
        self.name_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.save_btn.setText("新增分类")
        self._editing_id = None
    
    def _on_save(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入分类名称")
            return
        
        cat_type = self.type_combo.currentData()
        is_update = self._editing_id is not None
        
        try:
            cat = Category(id=self._editing_id, name=name, type=cat_type)
            if is_update:
                self.db.update_category(cat)
            else:
                self.db.add_category(cat)
            
            # 保存成功：刷新列表并显示提示
            self._load_data()
            self._clear_form()
            self.category_list.clearSelection()
            
            action = "更新" if is_update else "新增"
            QMessageBox.information(self, "成功", f"分类「{name}」已{action}保存")
            
        except sqlite3.IntegrityError:
            QMessageBox.warning(
                self, "无法保存", 
                f"分类名称「{name}」已存在，请使用其他名称。"
            )
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"数据库错误: {e}")
    
    def _on_delete(self) -> None:
        row = self.category_list.currentRow()
        if row < 0:
            return
        cat: Category = self.category_list.item(row).data(Qt.UserRole)
        if QMessageBox.question(self, "确认", f"删除分类「{cat.name}」？") == QMessageBox.Yes:
            try:
                self.db.delete_category(cat.id)
                self._load_data()
            except sqlite3.IntegrityError:
                QMessageBox.warning(
                    self, "无法删除",
                    "该分类正在被使用，无法删除。\n请先修改或删除关联的交易。"
                )
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {e}")


class AccountManagementWidget(QWidget):
    """账户管理组件"""
    
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self._editing_id: Optional[int] = None
        self._init_ui()
        self._load_data()
    
    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        
        left_layout = QVBoxLayout()
        self.account_list = QListWidget()
        self.account_list.currentRowChanged.connect(self._on_selection_changed)
        left_layout.addWidget(self.account_list)
        
        list_btn_layout = QHBoxLayout()
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self._on_delete)
        self.delete_btn.setEnabled(False)
        list_btn_layout.addWidget(self.delete_btn)
        list_btn_layout.addStretch()
        left_layout.addLayout(list_btn_layout)
        
        layout.addLayout(left_layout, 1)
        
        right_layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        form_layout.addRow("名称:", self.name_input)
        
        self.type_combo = QComboBox()
        for type_id, type_name in ACCOUNT_TYPES.items():
            self.type_combo.addItem(type_name, type_id)
        form_layout.addRow("类型:", self.type_combo)
        
        right_layout.addLayout(form_layout)
        
        self.save_btn = QPushButton("新增账户")
        self.save_btn.clicked.connect(self._on_save)
        right_layout.addWidget(self.save_btn)
        right_layout.addStretch()
        
        layout.addLayout(right_layout, 1)
    
    def _load_data(self) -> None:
        self.account_list.clear()
        for acc in self.db.get_all_accounts():
            type_label = ACCOUNT_TYPES.get(acc.type, acc.type)
            item = QListWidgetItem(f"{acc.name} [{type_label}]")
            item.setData(Qt.UserRole, acc)
            self.account_list.addItem(item)
    
    def _on_selection_changed(self, row: int) -> None:
        self.delete_btn.setEnabled(row >= 0)
        if row >= 0:
            acc: Account = self.account_list.item(row).data(Qt.UserRole)
            self.name_input.setText(acc.name)
            idx = self.type_combo.findData(acc.type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            self.save_btn.setText("更新账户")
            self._editing_id = acc.id
        else:
            self._clear_form()
    
    def _clear_form(self) -> None:
        self.name_input.clear()
        self.type_combo.setCurrentIndex(0)
        self.save_btn.setText("新增账户")
        self._editing_id = None
    
    def _on_save(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入账户名称")
            return
        
        acc_type = self.type_combo.currentData()
        is_update = self._editing_id is not None
        
        try:
            acc = Account(id=self._editing_id, name=name, type=acc_type)
            if is_update:
                self.db.update_account(acc)
            else:
                self.db.add_account(acc)
            
            # 保存成功：刷新列表并显示提示
            self._load_data()
            self._clear_form()
            self.account_list.clearSelection()
            
            action = "更新" if is_update else "新增"
            QMessageBox.information(self, "成功", f"账户「{name}」已{action}保存")
            
        except sqlite3.IntegrityError:
            QMessageBox.warning(
                self, "无法保存",
                f"账户名称「{name}」已存在，请使用其他名称。"
            )
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"数据库错误: {e}")
    
    def _on_delete(self) -> None:
        row = self.account_list.currentRow()
        if row < 0:
            return
        acc: Account = self.account_list.item(row).data(Qt.UserRole)
        if QMessageBox.question(self, "确认", f"删除账户「{acc.name}」？") == QMessageBox.Yes:
            try:
                self.db.delete_account(acc.id)
                self._load_data()
            except sqlite3.IntegrityError:
                QMessageBox.warning(
                    self, "无法删除",
                    "该账户正在被使用，无法删除。\n请先修改或删除关联的交易。"
                )
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {e}")

