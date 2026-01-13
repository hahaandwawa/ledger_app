"""账户数据模型"""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Account:
    """账户数据模型"""
    id: Optional[int] = None
    name: str = ""
    type: str = "cash"  # cash / debit / credit / other
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: Tuple) -> "Account":
        """从数据库行创建Account对象"""
        return cls(
            id=row[0],
            name=row[1],
            type=row[2],
            created_at=row[3]
        )

    @staticmethod
    def type_display(account_type: str) -> str:
        """获取账户类型的显示文本"""
        # 延迟导入避免循环依赖
        from ledger.settings import ACCOUNT_TYPES
        return ACCOUNT_TYPES.get(account_type, account_type)

