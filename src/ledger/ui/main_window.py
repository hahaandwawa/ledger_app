import logging
import sqlite3
from typing import Optional, Final

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableView, QHeaderView,
    QMessageBox, QTabWidget, QStatusBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QAction, QKeySequence, QShortcut

from ledger.db.database import Database
from ledger.models.transaction import Transaction
from ledger.models.category import Category
from ledger.models.account import Account
from ledger.services.statistics_service import StatisticsService
from ledger.settings import format_money
from ledger.ui.transaction_model import TransactionTableModel
from ledger.ui.transaction_dialog import TransactionDialog
from ledger.ui.dashboard_widget import DashboardWidget
from ledger.ui.statistics_widget import StatisticsWidget
from ledger.ui.management_dialogs import SettingsDialog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger: Final = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.stats_service = StatisticsService(self.db)
        
        # 记忆上一次使用的分类/账户
        self._last_category = ""
        self._last_account = ""
        
        self.setWindowTitle("Ledger App - 本地记账软件")
        self.resize(1000, 700)
        
        self._init_menu()
        self._init_ui()
        self._init_shortcuts()
        self._init_statusbar()
        
        # 初始加载数据
        self._refresh_all()
    
    def _init_menu(self) -> None:
        """初始化菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新增交易", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._on_new_transaction)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        edit_action = QAction("编辑交易", self)
        edit_action.setShortcut(QKeySequence("Return"))
        edit_action.triggered.connect(self._on_edit_transaction)
        edit_menu.addAction(edit_action)
        
        delete_action = QAction("删除交易", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self._on_delete_transaction)
        edit_menu.addAction(delete_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置")
        
        manage_action = QAction("分类与账户管理", self)
        manage_action.triggered.connect(self._on_open_settings)
        settings_menu.addAction(manage_action)
    
    def _init_ui(self) -> None:
        """初始化界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签页
        self.tab_widget = QTabWidget()
        
        # Tab 1: 首页总览
        self.dashboard = DashboardWidget(self.stats_service)
        self.tab_widget.addTab(self.dashboard, "📊 总览")
        
        # Tab 2: 交易记录
        transactions_widget = QWidget()
        transactions_layout = QVBoxLayout(transactions_widget)
        transactions_layout.setContentsMargins(10, 10, 10, 10)
        
        # 工具栏
        toolbar_layout = QHBoxLayout()
        
        new_btn = QPushButton("➕ 新增交易")
        new_btn.clicked.connect(self._on_new_transaction)
        toolbar_layout.addWidget(new_btn)
        
        edit_btn = QPushButton("✏️ 编辑")
        edit_btn.clicked.connect(self._on_edit_transaction)
        toolbar_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ 删除")
        delete_btn.clicked.connect(self._on_delete_transaction)
        toolbar_layout.addWidget(delete_btn)
        
        toolbar_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self._refresh_all)
        toolbar_layout.addWidget(refresh_btn)
        
        transactions_layout.addLayout(toolbar_layout)
        
        # 交易列表（使用Model/View架构）
        self.transaction_model = TransactionTableModel()
        self.transaction_view = QTableView()
        self.transaction_view.setModel(self.transaction_model)
        self.transaction_view.setSelectionBehavior(QTableView.SelectRows)
        self.transaction_view.setSelectionMode(QTableView.SingleSelection)
        self.transaction_view.setAlternatingRowColors(True)
        self.transaction_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.transaction_view.doubleClicked.connect(self._on_edit_transaction)
        
        transactions_layout.addWidget(self.transaction_view)
        
        self.tab_widget.addTab(transactions_widget, "📝 交易记录")
        
        # Tab 3: 统计分析
        self.statistics = StatisticsWidget(self.stats_service)
        self.tab_widget.addTab(self.statistics, "📈 统计分析")
        
        # 切换标签页时刷新数据
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        layout.addWidget(self.tab_widget)
    
    def _init_shortcuts(self) -> None:
        """初始化键盘快捷键"""
        # Delete键删除
        delete_shortcut = QShortcut(QKeySequence.Delete, self.transaction_view)
        delete_shortcut.activated.connect(self._on_delete_transaction)
        
        # Enter键编辑
        enter_shortcut = QShortcut(QKeySequence("Return"), self.transaction_view)
        enter_shortcut.activated.connect(self._on_edit_transaction)
        
        # Ctrl+N 新增
        new_shortcut = QShortcut(QKeySequence.New, self)
        new_shortcut.activated.connect(self._on_new_transaction)
    
    def _init_statusbar(self) -> None:
        """初始化状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")
    
    def _on_tab_changed(self, index: int) -> None:
        """标签页切换"""
        if index == 0:  # Dashboard
            self.dashboard.refresh()
        elif index == 2:  # Statistics
            self.statistics.refresh()
    
    def _refresh_all(self) -> None:
        """刷新所有数据"""
        try:
            transactions = self.db.get_all_transactions()
            self.transaction_model.set_transactions(transactions)
            self.dashboard.refresh()
            self.statistics.refresh()  # 同时刷新统计页面
            self.statusbar.showMessage(f"已加载 {len(transactions)} 条交易记录", 3000)
        except Exception as e:
            logger.exception("刷新数据失败")
            QMessageBox.critical(self, "错误", f"加载数据失败: {e}")
    
    def _get_selected_transaction(self) -> Optional[Transaction]:
        """获取当前选中的交易"""
        indexes = self.transaction_view.selectedIndexes()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.transaction_model.get_transaction(row)
    
    def _ensure_category_exists(self, category_name: str, tx_type: str) -> None:
        """确保分类存在于数据库中，如果不存在则自动创建"""
        if not category_name:
            return
        
        # 检查是否已存在
        existing = self.db.get_all_categories()
        if any(cat.name == category_name for cat in existing):
            return
        
        # 不存在，自动创建
        try:
            new_cat = Category(name=category_name, type=tx_type)
            self.db.add_category(new_cat)
            logger.info(f"自动创建分类: {category_name} (type={tx_type})")
        except sqlite3.IntegrityError:
            # 可能是并发创建，忽略
            pass
    
    def _ensure_account_exists(self, account_name: str) -> None:
        """确保账户存在于数据库中，如果不存在则自动创建"""
        if not account_name:
            return
        
        # 检查是否已存在
        existing = self.db.get_all_accounts()
        if any(acc.name == account_name for acc in existing):
            return
        
        # 不存在，自动创建（默认类型为 other）
        try:
            new_acc = Account(name=account_name, type="other")
            self.db.add_account(new_acc)
            logger.info(f"自动创建账户: {account_name}")
        except sqlite3.IntegrityError:
            # 可能是并发创建，忽略
            pass
    
    def _on_new_transaction(self) -> None:
        """新增交易"""
        categories = self.db.get_all_categories()
        accounts = self.db.get_all_accounts()
        
        dialog = TransactionDialog(
            self,
            categories=categories,
            accounts=accounts,
            last_category=self._last_category,
            last_account=self._last_account
        )
        
        if dialog.exec() == TransactionDialog.Accepted:
            tx = dialog.get_result()
            if tx:
                try:
                    # 自动将新分类/账户添加到数据库（长期记忆）
                    self._ensure_category_exists(tx.category, tx.type)
                    self._ensure_account_exists(tx.account)
                    
                    self.db.add_transaction(tx)
                    # 记忆选择
                    self._last_category = tx.category
                    self._last_account = tx.account
                    self._refresh_all()
                    self.statusbar.showMessage("交易已保存", 3000)
                except sqlite3.Error as e:
                    logger.exception("保存交易失败")
                    QMessageBox.critical(self, "保存失败", f"数据库错误: {e}")
                except Exception as e:
                    logger.exception("保存交易失败")
                    QMessageBox.critical(self, "保存失败", f"未知错误: {e}")
    
    def _on_edit_transaction(self) -> None:
        """编辑交易"""
        tx = self._get_selected_transaction()
        if not tx:
            QMessageBox.information(self, "提示", "请先选择要编辑的交易")
            return
        
        categories = self.db.get_all_categories()
        accounts = self.db.get_all_accounts()
        
        dialog = TransactionDialog(
            self,
            transaction=tx,
            categories=categories,
            accounts=accounts
        )
        
        if dialog.exec() == TransactionDialog.Accepted:
            updated_tx = dialog.get_result()
            if updated_tx:
                try:
                    # 自动将新分类/账户添加到数据库（长期记忆）
                    self._ensure_category_exists(updated_tx.category, updated_tx.type)
                    self._ensure_account_exists(updated_tx.account)
                    
                    self.db.update_transaction(updated_tx)
                    self._refresh_all()
                    self.statusbar.showMessage("交易已更新", 3000)
                except sqlite3.Error as e:
                    logger.exception("更新交易失败")
                    QMessageBox.critical(self, "更新失败", f"数据库错误: {e}")
                except Exception as e:
                    logger.exception("更新交易失败")
                    QMessageBox.critical(self, "更新失败", f"未知错误: {e}")
    
    def _on_delete_transaction(self) -> None:
        """删除交易"""
        tx = self._get_selected_transaction()
        if not tx:
            QMessageBox.information(self, "提示", "请先选择要删除的交易")
            return
        
        # 二次确认
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除这笔交易吗？\n\n"
            f"日期: {tx.date}\n"
            f"类型: {'收入' if tx.type == 'income' else '支出'}\n"
            f"金额: {format_money(tx.amount_cents)}\n"
            f"分类: {tx.category or '未分类'}\n\n"
            f"此操作无法撤销！",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.db.delete_transaction(tx.id)
                self._refresh_all()
                self.statusbar.showMessage("交易已删除", 3000)
            except sqlite3.Error as e:
                logger.exception("删除交易失败")
                QMessageBox.critical(self, "删除失败", f"数据库错误: {e}")
            except Exception as e:
                logger.exception("删除交易失败")
                QMessageBox.critical(self, "删除失败", f"未知错误: {e}")
    
    def _on_open_settings(self) -> None:
        """打开设置对话框"""
        dialog = SettingsDialog(self.db, self)
        dialog.exec()
    
    def closeEvent(self, event: QCloseEvent) -> None:
        """窗口关闭事件"""
        self.db.close()
        event.accept()
