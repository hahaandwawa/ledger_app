"""交易编辑对话框模块"""
import logging
from typing import Optional, List, Final

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QDateEdit,
    QPushButton, QMessageBox
)
from PySide6.QtCore import QDate

from ledger.models.transaction import Transaction
from ledger.models.category import Category
from ledger.models.account import Account
from ledger.settings import MAX_AMOUNT_CENTS, format_money_from_float, CURRENCY_SYMBOL

logger: Final = logging.getLogger(__name__)


class TransactionDialog(QDialog):
    """交易编辑对话框（新增/编辑）"""
    
    def __init__(
        self,
        parent=None,
        transaction: Optional[Transaction] = None,
        categories: Optional[List[Category]] = None,
        accounts: Optional[List[Account]] = None,
        last_category: str = "",
        last_account: str = ""
    ):
        super().__init__(parent)
        self.transaction = transaction
        self.categories = categories or []
        self.accounts = accounts or []
        self.last_category = last_category
        self.last_account = last_account
        self.result_transaction: Optional[Transaction] = None
        
        self._is_edit_mode = transaction is not None and transaction.id is not None
        self._init_ui()
        
        if self._is_edit_mode:
            self._load_transaction_data()
    
    def _init_ui(self) -> None:
        title = "编辑交易" if self._is_edit_mode else "新增交易"
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        
        # 类型
        self.type_combo = QComboBox()
        self.type_combo.addItem("支出", "expense")
        self.type_combo.addItem("收入", "income")
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        form_layout.addRow("类型:", self.type_combo)
        
        # 金额
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText(f"请输入金额 ({CURRENCY_SYMBOL})")
        form_layout.addRow(f"金额 ({CURRENCY_SYMBOL}):", self.amount_input)
        
        # 日期
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        form_layout.addRow("日期:", self.date_input)
        
        # 分类（下拉框，可编辑）
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setInsertPolicy(QComboBox.NoInsert)
        self._populate_categories()
        form_layout.addRow("分类:", self.category_combo)
        
        # 账户（下拉框，可编辑）
        self.account_combo = QComboBox()
        self.account_combo.setEditable(True)
        self.account_combo.setInsertPolicy(QComboBox.NoInsert)
        self._populate_accounts()
        form_layout.addRow("账户:", self.account_combo)
        
        # 备注
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("可选")
        form_layout.addRow("备注:", self.note_input)
        
        layout.addLayout(form_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("保存")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)
        
        # 设置默认分类/账户（新增模式）
        if not self._is_edit_mode:
            if self.last_category:
                self.category_combo.setCurrentText(self.last_category)
            if self.last_account:
                self.account_combo.setCurrentText(self.last_account)
    
    def _populate_categories(self) -> None:
        """填充分类下拉框"""
        self.category_combo.clear()
        self.category_combo.addItem("")  # 空选项
        
        current_type = self.type_combo.currentData()
        for cat in self.categories:
            if cat.type == current_type or cat.type == "both":
                self.category_combo.addItem(cat.name, cat.id)
    
    def _populate_accounts(self) -> None:
        """填充账户下拉框"""
        self.account_combo.clear()
        self.account_combo.addItem("")  # 空选项
        for acc in self.accounts:
            self.account_combo.addItem(acc.name, acc.id)
    
    def _on_type_changed(self) -> None:
        """类型变化时更新分类列表"""
        current_text = self.category_combo.currentText()
        self._populate_categories()
        # 尝试恢复之前的选择
        idx = self.category_combo.findText(current_text)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
    
    def _load_transaction_data(self) -> None:
        """加载交易数据到表单"""
        if not self.transaction:
            return
        
        # 类型
        idx = self.type_combo.findData(self.transaction.type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        
        # 金额
        self.amount_input.setText(f"{self.transaction.amount_display:.2f}")
        
        # 日期
        date_parts = self.transaction.date.split("-")
        if len(date_parts) == 3:
            self.date_input.setDate(QDate(
                int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
            ))
        
        # 分类
        self._populate_categories()
        if self.transaction.category:
            self.category_combo.setCurrentText(self.transaction.category)
        
        # 账户
        if self.transaction.account:
            self.account_combo.setCurrentText(self.transaction.account)
        
        # 备注
        self.note_input.setText(self.transaction.note or "")
    
    def _on_save(self) -> None:
        """保存按钮点击"""
        try:
            # 验证金额
            amount_str = self.amount_input.text().strip()
            if not amount_str:
                raise ValueError("请输入金额")
            
            try:
                amount_float = float(amount_str)
            except ValueError:
                raise ValueError("金额格式不正确")
            
            if amount_float <= 0:
                raise ValueError("金额必须为正数")
            
            amount_cents = int(round(amount_float * 100))
            if amount_cents > MAX_AMOUNT_CENTS:
                raise ValueError(f"金额过大（上限：{format_money_from_float(MAX_AMOUNT_CENTS / 100)}）")
            
            # 构建Transaction
            category_text = self.category_combo.currentText().strip()
            account_text = self.account_combo.currentText().strip()
            
            # 获取分类/账户ID（如果选择的是已有项）
            category_id = self.category_combo.currentData()
            account_id = self.account_combo.currentData()
            
            self.result_transaction = Transaction(
                id=self.transaction.id if self._is_edit_mode else None,
                type=self.type_combo.currentData(),
                amount_cents=amount_cents,
                date=self.date_input.date().toString("yyyy-MM-dd"),
                category=category_text,
                account=account_text,
                note=self.note_input.text().strip(),
                created_at=self.transaction.created_at if self._is_edit_mode else None,
                category_id=category_id if isinstance(category_id, int) else None,
                account_id=account_id if isinstance(account_id, int) else None
            )
            
            self.accept()
            
        except ValueError as e:
            QMessageBox.warning(self, "输入错误", str(e))
    
    def get_result(self) -> Optional[Transaction]:
        """获取编辑结果"""
        return self.result_transaction

