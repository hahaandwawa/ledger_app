"""交易表格数据模型模块"""
from typing import List, Optional, Any, Final
from enum import IntEnum

from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QColor

from ledger.models.transaction import Transaction
from ledger.settings import DEFAULT_CATEGORY, DEFAULT_ACCOUNT, format_money
from ledger.ui.theme import COLOR_INCOME, COLOR_EXPENSE


class TransactionColumn(IntEnum):
    """交易表格列定义"""
    DATE = 0
    TYPE = 1
    AMOUNT = 2
    CATEGORY = 3
    ACCOUNT = 4
    NOTE = 5


COLUMN_HEADERS: Final = ["日期", "类型", "金额", "分类", "账户", "备注"]


class TransactionTableModel(QAbstractTableModel):
    """交易表格数据模型（Model/View架构）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._transactions: List[Transaction] = []

    def set_transactions(self, transactions: List[Transaction]) -> None:
        """设置交易数据"""
        self.beginResetModel()
        self._transactions = transactions
        self.endResetModel()

    def get_transaction(self, row: int) -> Optional[Transaction]:
        """根据行号获取交易对象"""
        if 0 <= row < len(self._transactions):
            return self._transactions[row]
        return None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._transactions)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(TransactionColumn)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._transactions)):
            return None
        
        tx = self._transactions[index.row()]
        col = index.column()
        
        if role == Qt.DisplayRole:
            if col == TransactionColumn.DATE:
                return tx.date
            elif col == TransactionColumn.TYPE:
                return "收入" if tx.type == "income" else "支出"
            elif col == TransactionColumn.AMOUNT:
                return format_money(tx.amount_cents)
            elif col == TransactionColumn.CATEGORY:
                return tx.category or DEFAULT_CATEGORY
            elif col == TransactionColumn.ACCOUNT:
                return tx.account or DEFAULT_ACCOUNT
            elif col == TransactionColumn.NOTE:
                return tx.note or ""
        
        elif role == Qt.TextAlignmentRole:
            # PM规则：所有列统一水平居中 + 垂直居中
            return Qt.AlignCenter
        
        elif role == Qt.ForegroundRole:
            if col in (TransactionColumn.TYPE, TransactionColumn.AMOUNT):
                return QColor(COLOR_INCOME if tx.type == "income" else COLOR_EXPENSE)
        
        elif role == Qt.UserRole:
            # 返回原始Transaction对象，用于编辑
            return tx
        
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if 0 <= section < len(COLUMN_HEADERS):
                return COLUMN_HEADERS[section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

