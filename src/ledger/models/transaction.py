from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(slots=True)
class Transaction:
    """记账交易数据模型"""
    id: Optional[int] = None
    type: str = "expense"  # income / expense
    amount_cents: int = 0
    date: str = ""  # YYYY-MM-DD
    category: str = ""  # 兼容旧数据的字符串分类
    account: str = ""   # 兼容旧数据的字符串账户
    note: Optional[str] = ""
    created_at: Optional[str] = None
    category_id: Optional[int] = None  # 外键关联categories表
    account_id: Optional[int] = None   # 外键关联accounts表

    @property
    def amount_display(self) -> float:
        """获取显示用金额（元）"""
        return self.amount_cents / 100.0

    @classmethod
    def from_row(cls, row: Tuple) -> "Transaction":
        """从数据库行创建Transaction对象"""
        return cls(
            id=row[0],
            type=row[1],
            amount_cents=row[2],
            date=row[3],
            category=row[4] or "",
            account=row[5] or "",
            note=row[6],
            created_at=row[7],
            category_id=row[8] if len(row) > 8 else None,
            account_id=row[9] if len(row) > 9 else None
        )
