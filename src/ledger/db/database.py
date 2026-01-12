import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from ledger.settings import DB_PATH, DB_SCHEMA_VERSION, DEFAULT_CATEGORIES
from ledger.models.transaction import Transaction
from ledger.models.category import Category
from ledger.models.account import Account


class Database:
    """数据库访问层，支持上下文管理器使用方式"""
    
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or DB_PATH
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_db()

    def _connect(self) -> None:
        """建立数据库连接"""
        self.conn = sqlite3.connect(self._db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _init_db(self) -> None:
        """初始化数据库schema，支持迁移"""
        cursor = self.conn.cursor()
        
        # 检查schema版本
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)
        cursor.execute("SELECT version FROM schema_version")
        row = cursor.fetchone()
        current_version = row[0] if row else 0
        
        # 执行迁移
        if current_version < 1:
            self._migrate_v1(cursor)
        if current_version < 2:
            self._migrate_v2(cursor)
        if current_version < 3:
            self._migrate_v3(cursor)
        
        # 更新schema版本
        if current_version < DB_SCHEMA_VERSION:
            cursor.execute("DELETE FROM schema_version")
            cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (DB_SCHEMA_VERSION,))
        
        self.conn.commit()

    def _migrate_v1(self, cursor: sqlite3.Cursor) -> None:
        """V1: 基础transactions表"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                amount_cents INTEGER NOT NULL,
                date TEXT NOT NULL,
                category TEXT,
                account TEXT,
                note TEXT,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_date 
            ON transactions(date DESC, created_at DESC)
        """)

    def _migrate_v2(self, cursor: sqlite3.Cursor) -> None:
        """V2: 添加categories和accounts表"""
        # Categories表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                parent_id INTEGER,
                type TEXT NOT NULL DEFAULT 'expense',
                created_at TEXT NOT NULL,
                FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
            )
        """)
        
        # Accounts表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL DEFAULT 'cash',
                created_at TEXT NOT NULL
            )
        """)
        
        # 添加外键字段到transactions（新字段，保留旧字段兼容）
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN category_id INTEGER REFERENCES categories(id)")
        except sqlite3.OperationalError:
            pass  # 列已存在
        
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN account_id INTEGER REFERENCES accounts(id)")
        except sqlite3.OperationalError:
            pass  # 列已存在
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_type ON categories(type)")

    def _migrate_v3(self, cursor: sqlite3.Cursor) -> None:
        """V3: 添加默认分类种子数据（仅首次运行时插入）"""
        # 检查是否已有分类数据
        cursor.execute("SELECT COUNT(*) FROM categories")
        count = cursor.fetchone()[0]
        
        # 仅当分类表为空时才插入默认数据
        if count == 0:
            created_at = datetime.now().isoformat()
            for cat_data in DEFAULT_CATEGORIES:
                cursor.execute("""
                    INSERT INTO categories (name, type, created_at)
                    VALUES (?, ?, ?)
                """, (cat_data["name"], cat_data["type"], created_at))

    # ==================== Transaction CRUD ====================
    
    def add_transaction(self, transaction: Transaction) -> int:
        """新增交易"""
        created_at = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (type, amount_cents, date, category, account, note, created_at, category_id, account_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            transaction.type,
            transaction.amount_cents,
            transaction.date,
            transaction.category,
            transaction.account,
            transaction.note,
            created_at,
            transaction.category_id,
            transaction.account_id
        ))
        self.conn.commit()
        transaction.id = cursor.lastrowid
        return transaction.id

    def update_transaction(self, transaction: Transaction) -> None:
        """更新交易（保持id和created_at不变）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE transactions SET
                type = ?,
                amount_cents = ?,
                date = ?,
                category = ?,
                account = ?,
                note = ?,
                category_id = ?,
                account_id = ?
            WHERE id = ?
        """, (
            transaction.type,
            transaction.amount_cents,
            transaction.date,
            transaction.category,
            transaction.account,
            transaction.note,
            transaction.category_id,
            transaction.account_id,
            transaction.id
        ))
        self.conn.commit()

    def delete_transaction(self, transaction_id: int) -> None:
        """删除交易"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        self.conn.commit()

    def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """根据ID获取交易"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
        row = cursor.fetchone()
        return Transaction.from_row(row) if row else None

    def get_all_transactions(self) -> List[Transaction]:
        """获取所有交易，按日期倒序"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM transactions ORDER BY date DESC, created_at DESC")
        rows = cursor.fetchall()
        return [Transaction.from_row(row) for row in rows]

    def get_transactions_by_date_range(self, start_date: str, end_date: str) -> List[Transaction]:
        """根据日期范围获取交易"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM transactions 
            WHERE date >= ? AND date <= ?
            ORDER BY date DESC, created_at DESC
        """, (start_date, end_date))
        rows = cursor.fetchall()
        return [Transaction.from_row(row) for row in rows]

    # ==================== Category CRUD ====================
    
    def add_category(self, category: Category) -> int:
        """新增分类"""
        created_at = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO categories (name, parent_id, type, created_at)
            VALUES (?, ?, ?, ?)
        """, (category.name, category.parent_id, category.type, created_at))
        self.conn.commit()
        category.id = cursor.lastrowid
        return category.id

    def update_category(self, category: Category) -> None:
        """更新分类"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE categories SET name = ?, parent_id = ?, type = ?
            WHERE id = ?
        """, (category.name, category.parent_id, category.type, category.id))
        self.conn.commit()

    def delete_category(self, category_id: int) -> None:
        """删除分类"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self.conn.commit()

    def get_all_categories(self) -> List[Category]:
        """获取所有分类"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY type, name")
        rows = cursor.fetchall()
        return [Category.from_row(row) for row in rows]

    def get_categories_by_type(self, category_type: str) -> List[Category]:
        """根据类型获取分类（income/expense/both）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM categories 
            WHERE type = ? OR type = 'both'
            ORDER BY name
        """, (category_type,))
        rows = cursor.fetchall()
        return [Category.from_row(row) for row in rows]

    # ==================== Account CRUD ====================
    
    def add_account(self, account: Account) -> int:
        """新增账户"""
        created_at = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO accounts (name, type, created_at)
            VALUES (?, ?, ?)
        """, (account.name, account.type, created_at))
        self.conn.commit()
        account.id = cursor.lastrowid
        return account.id

    def update_account(self, account: Account) -> None:
        """更新账户"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE accounts SET name = ?, type = ?
            WHERE id = ?
        """, (account.name, account.type, account.id))
        self.conn.commit()

    def delete_account(self, account_id: int) -> None:
        """删除账户"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        self.conn.commit()

    def get_all_accounts(self) -> List[Account]:
        """获取所有账户"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM accounts ORDER BY name")
        rows = cursor.fetchall()
        return [Account.from_row(row) for row in rows]

    # ==================== Statistics ====================
    
    def get_summary_by_date_range(self, start_date: str, end_date: str) -> Dict[str, int]:
        """获取日期范围内的收支汇总"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT type, SUM(amount_cents) as total
            FROM transactions
            WHERE date >= ? AND date <= ?
            GROUP BY type
        """, (start_date, end_date))
        
        result = {"income": 0, "expense": 0}
        for row in cursor.fetchall():
            result[row[0]] = row[1] or 0
        return result

    def get_category_summary(self, start_date: str, end_date: str, tx_type: str) -> List[Dict[str, Any]]:
        """获取分类汇总"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                COALESCE(category, '未分类') as category_name,
                SUM(amount_cents) as total
            FROM transactions
            WHERE date >= ? AND date <= ? AND type = ?
            GROUP BY category
            ORDER BY total DESC
        """, (start_date, end_date, tx_type))
        
        return [{"category": row[0], "amount_cents": row[1]} for row in cursor.fetchall()]

    def get_daily_summary(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取每日汇总（用于趋势图）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                date,
                SUM(CASE WHEN type = 'income' THEN amount_cents ELSE 0 END) as income,
                SUM(CASE WHEN type = 'expense' THEN amount_cents ELSE 0 END) as expense
            FROM transactions
            WHERE date >= ? AND date <= ?
            GROUP BY date
            ORDER BY date
        """, (start_date, end_date))
        
        return [{"date": row[0], "income": row[1], "expense": row[2]} for row in cursor.fetchall()]

    def get_daily_summary_by_category(
        self, start_date: str, end_date: str, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取每日汇总（支持分类筛选）
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            category: 可选的支出分类筛选（仅影响支出，收入不受影响）
        
        Returns:
            [{"date": str, "income": int, "expense": int}, ...]
        """
        cursor = self.conn.cursor()
        
        if category is None:
            # 无分类筛选，返回全部
            return self.get_daily_summary(start_date, end_date)
        
        # 有分类筛选：收入不受影响，支出只计算该分类
        cursor.execute("""
            SELECT 
                date,
                SUM(CASE WHEN type = 'income' THEN amount_cents ELSE 0 END) as income,
                SUM(CASE WHEN type = 'expense' AND category = ? THEN amount_cents ELSE 0 END) as expense
            FROM transactions
            WHERE date >= ? AND date <= ?
            GROUP BY date
            ORDER BY date
        """, (category, start_date, end_date))
        
        return [{"date": row[0], "income": row[1], "expense": row[2]} for row in cursor.fetchall()]

    def close(self) -> None:
        """关闭数据库连接"""
        if self.conn is not None:
            self.conn.close()
            self.conn = None
