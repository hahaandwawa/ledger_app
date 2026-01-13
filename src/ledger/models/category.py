"""分类数据模型"""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Category:
    """分类数据模型"""
    id: Optional[int] = None
    name: str = ""
    parent_id: Optional[int] = None  # 支持层级分类
    type: str = "expense"  # income / expense / both
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row: Tuple) -> "Category":
        """从数据库行创建Category对象"""
        return cls(
            id=row[0],
            name=row[1],
            parent_id=row[2],
            type=row[3],
            created_at=row[4]
        )

