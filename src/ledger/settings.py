"""应用程序配置模块"""
from pathlib import Path
from typing import Final, Dict, List

# ==================== 路径配置 ====================
BASE_DIR: Final = Path(__file__).resolve().parent.parent.parent.parent
APP_DIR: Final = BASE_DIR / "ledger_app"
DATA_DIR: Final = APP_DIR / "data"
DB_PATH: Final = DATA_DIR / "app.db"

# 确保数据目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ==================== 应用信息 ====================
APP_NAME: Final = "Ledger App"
VERSION: Final = "1.2.1"

# ==================== 数据库配置 ====================
DB_SCHEMA_VERSION: Final = 3  # V3: 添加默认分类种子数据

# ==================== 货币设置 ====================
CURRENCY_SYMBOL: Final = "$"
CURRENCY_CODE: Final = "USD"

# ==================== 业务规则 ====================
MAX_AMOUNT: Final = 1_000_000.00  # 金额上限：一百万
MAX_AMOUNT_CENTS: Final = int(MAX_AMOUNT * 100)  # 转换为分

# ==================== UI 显示默认值 ====================
DEFAULT_CATEGORY: Final = "未分类"
DEFAULT_ACCOUNT: Final = "未指定账户"

# ==================== 类型映射 ====================
CATEGORY_TYPES: Final[Dict[str, str]] = {
    "expense": "支出",
    "income": "收入",
    "both": "通用",
}

ACCOUNT_TYPES: Final[Dict[str, str]] = {
    "cash": "现金",
    "debit": "储蓄卡",
    "credit": "信用卡",
    "other": "其他",
}

# ==================== 默认数据 ====================
DEFAULT_CATEGORIES: Final[List[Dict[str, str]]] = [
    {"name": "吃饭", "type": "expense"},
    {"name": "娱乐", "type": "expense"},
    {"name": "购物", "type": "expense"},
    {"name": "房租水电", "type": "expense"},
    {"name": "工资", "type": "income"},
]


# ==================== 工具函数 ====================
def format_money(amount_cents: int) -> str:
    """统一的金额格式化函数，返回货币格式（如 $1,234.56）"""
    amount = amount_cents / 100.0
    return f"{CURRENCY_SYMBOL}{amount:,.2f}"


def format_money_from_float(amount: float) -> str:
    """从浮点数格式化金额"""
    return f"{CURRENCY_SYMBOL}{amount:,.2f}"

