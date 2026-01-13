"""统计分析服务模块"""
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional, Literal
from dataclasses import dataclass
from ledger.db.database import Database

# 时间粒度类型
GranularityType = Literal["day", "week", "month", "year"]


@dataclass
class PeriodSummary:
    """期间汇总数据"""
    income_cents: int = 0
    expense_cents: int = 0
    
    @property
    def income(self) -> float:
        """收入金额（元）"""
        return self.income_cents / 100.0
    
    @property
    def expense(self) -> float:
        """支出金额（元）"""
        return self.expense_cents / 100.0
    
    @property
    def balance_cents(self) -> int:
        """结余（分）"""
        return self.income_cents - self.expense_cents
    
    @property
    def balance(self) -> float:
        """结余金额（元）"""
        return self.balance_cents / 100.0


class StatisticsService:
    """统计分析服务层"""
    
    def __init__(self, db: Database):
        self.db = db

    @staticmethod
    def get_month_range(year: int, month: int) -> Tuple[str, str]:
        """获取某月的日期范围"""
        _, last_day = monthrange(year, month)
        return (
            f"{year:04d}-{month:02d}-01",
            f"{year:04d}-{month:02d}-{last_day:02d}"
        )

    @staticmethod
    def get_year_range(year: int) -> Tuple[str, str]:
        """获取某年的日期范围"""
        return f"{year:04d}-01-01", f"{year:04d}-12-31"

    @staticmethod
    def get_last_n_full_months_range(n: int) -> Tuple[str, str]:
        """
        获取过去 N 个完整自然月的日期范围
        
        重要规则：
        - 不包含当前月（当前月未完成）
        - 区间为 N 个完整的自然月
        - 使用自然月计算，正确处理跨年和闰年
        
        示例（假设今天是 2026-01-12）：
        - N=3: 2025-10-01 ~ 2025-12-31（2025年10月、11月、12月）
        - N=6: 2025-07-01 ~ 2025-12-31（2025年7月至12月）
        
        Args:
            n: 需要的完整月份数量
        
        Returns:
            (start_date, end_date) 格式为 "YYYY-MM-DD"
        """
        today = date.today()
        
        # 结束月 = 当前月的前一个月
        if today.month == 1:
            end_year, end_month = today.year - 1, 12
        else:
            end_year, end_month = today.year, today.month - 1
        
        # 计算结束日期（结束月的最后一天）
        _, end_last_day = monthrange(end_year, end_month)
        end_date = f"{end_year:04d}-{end_month:02d}-{end_last_day:02d}"
        
        # 计算开始月 = 从结束月往前数 n-1 个月（因为结束月本身算1个月）
        # 总共需要往前 (n-1) 个月
        start_year, start_month = end_year, end_month
        for _ in range(n - 1):
            if start_month == 1:
                start_year -= 1
                start_month = 12
            else:
                start_month -= 1
        
        # 开始日期（开始月的第一天）
        start_date = f"{start_year:04d}-{start_month:02d}-01"
        
        return start_date, end_date

    @staticmethod
    def get_last_3_months_range() -> Tuple[str, str]:
        """获取过去三个完整自然月的日期范围"""
        return StatisticsService.get_last_n_full_months_range(3)

    @staticmethod
    def get_last_6_months_range() -> Tuple[str, str]:
        """获取过去六个完整自然月（半年）的日期范围"""
        return StatisticsService.get_last_n_full_months_range(6)

    @staticmethod
    def get_last_12_months_range() -> Tuple[str, str]:
        """获取过去十二个完整自然月（一年）的日期范围"""
        return StatisticsService.get_last_n_full_months_range(12)

    def get_current_month_summary(self) -> PeriodSummary:
        """获取本月收支汇总"""
        today = date.today()
        start, end = self.get_month_range(today.year, today.month)
        return self._get_period_summary(start, end)

    def get_last_month_summary(self) -> PeriodSummary:
        """获取上月收支汇总"""
        today = date.today()
        if today.month == 1:
            year, month = today.year - 1, 12
        else:
            year, month = today.year, today.month - 1
        start, end = self.get_month_range(year, month)
        return self._get_period_summary(start, end)

    def get_current_year_summary(self) -> PeriodSummary:
        """获取本年收支汇总"""
        today = date.today()
        start, end = self.get_year_range(today.year)
        return self._get_period_summary(start, end)

    def get_custom_period_summary(self, start_date: str, end_date: str) -> PeriodSummary:
        """获取自定义期间收支汇总"""
        return self._get_period_summary(start_date, end_date)

    def _get_period_summary(self, start_date: str, end_date: str) -> PeriodSummary:
        """获取期间汇总（内部方法）"""
        summary = self.db.get_summary_by_date_range(start_date, end_date)
        return PeriodSummary(
            income_cents=summary.get("income", 0),
            expense_cents=summary.get("expense", 0)
        )

    def get_category_breakdown(self, start_date: str, end_date: str, tx_type: str = "expense") -> List[Dict[str, Any]]:
        """获取分类明细"""
        raw_data = self.db.get_category_summary(start_date, end_date, tx_type)
        total = sum(item["amount_cents"] for item in raw_data)
        
        result = []
        for item in raw_data:
            amount = item["amount_cents"]
            result.append({
                "category": item["category"],
                "amount_cents": amount,
                "amount": amount / 100.0,
                "percentage": (amount / total * 100) if total > 0 else 0
            })
        return result

    def get_daily_trend(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """获取每日趋势数据（仅有数据的日期）"""
        raw_data = self.db.get_daily_summary(start_date, end_date)
        return [{
            "date": item["date"],
            "income": item["income"] / 100.0,
            "expense": item["expense"] / 100.0,
            "income_cents": item["income"],
            "expense_cents": item["expense"]
        } for item in raw_data]

    def get_trend_data(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        获取趋势图数据，自动选择时间粒度并填充连续时间点
        
        时间粒度规则：
        - 区间 ≤ 31 天：按"天"
        - 区间 > 31 天：按"月"
        
        返回格式：
        {
            "granularity": "day" | "month",
            "data": [{"label": str, "income": float, "expense": float}, ...]
        }
        
        注意: 此方法委托给 get_trend_data_advanced，保留用于向后兼容。
        """
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        days_diff = (end - start).days + 1
        
        # 自动选择粒度：≤31天按日，否则按月
        granularity: GranularityType = "day" if days_diff <= 31 else "month"
        return self.get_trend_data_advanced(start_date, end_date, granularity, category=None)

    def get_trend_data_advanced(
        self,
        start_date: str,
        end_date: str,
        granularity: GranularityType = "day",
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取高级趋势图数据，支持手动选择时间粒度和分类筛选
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            granularity: 时间粒度 ("day" | "week" | "month" | "year")
            category: 可选的支出分类筛选（仅影响支出，收入不受影响）
        
        Returns:
            {
                "granularity": str,
                "data": [{"label": str, "income": float, "expense": float}, ...]
            }
        """
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        if granularity == "day":
            return self._get_daily_trend_advanced(start, end, category)
        elif granularity == "week":
            return self._get_weekly_trend_advanced(start, end, category)
        elif granularity == "month":
            return self._get_monthly_trend_advanced(start, end, category)
        elif granularity == "year":
            return self._get_yearly_trend_advanced(start, end, category)
        else:
            # 默认按天
            return self._get_daily_trend_advanced(start, end, category)

    def _get_daily_trend_advanced(
        self, start: date, end: date, category: Optional[str] = None
    ) -> Dict[str, Any]:
        """按天聚合，支持分类筛选"""
        raw_data = self.db.get_daily_summary_by_category(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            category
        )
        
        data_map = {item["date"]: item for item in raw_data}
        
        result = []
        current = start
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            if date_str in data_map:
                item = data_map[date_str]
                result.append({
                    "label": date_str,
                    "income": item["income"] / 100.0,
                    "expense": item["expense"] / 100.0,
                })
            else:
                result.append({
                    "label": date_str,
                    "income": 0.0,
                    "expense": 0.0,
                })
            current += timedelta(days=1)
        
        return {"granularity": "day", "data": result}

    def _get_weekly_trend_advanced(
        self, start: date, end: date, category: Optional[str] = None
    ) -> Dict[str, Any]:
        """按周（ISO周）聚合，支持分类筛选"""
        raw_data = self.db.get_daily_summary_by_category(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            category
        )
        
        # 按ISO周聚合
        weekly_map: Dict[str, Dict[str, int]] = {}
        for item in raw_data:
            item_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
            iso_year, iso_week, _ = item_date.isocalendar()
            week_key = f"{iso_year}-W{iso_week:02d}"
            if week_key not in weekly_map:
                weekly_map[week_key] = {"income": 0, "expense": 0}
            weekly_map[week_key]["income"] += item["income"]
            weekly_map[week_key]["expense"] += item["expense"]
        
        # 生成连续周序列
        result = []
        current = start
        visited_weeks = set()
        
        while current <= end:
            iso_year, iso_week, _ = current.isocalendar()
            week_key = f"{iso_year}-W{iso_week:02d}"
            
            if week_key not in visited_weeks:
                visited_weeks.add(week_key)
                if week_key in weekly_map:
                    result.append({
                        "label": week_key,
                        "income": weekly_map[week_key]["income"] / 100.0,
                        "expense": weekly_map[week_key]["expense"] / 100.0,
                    })
                else:
                    result.append({
                        "label": week_key,
                        "income": 0.0,
                        "expense": 0.0,
                    })
            current += timedelta(days=1)
        
        return {"granularity": "week", "data": result}

    def _get_monthly_trend_advanced(
        self, start: date, end: date, category: Optional[str] = None
    ) -> Dict[str, Any]:
        """按月聚合，支持分类筛选"""
        raw_data = self.db.get_daily_summary_by_category(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            category
        )
        
        # 按月聚合
        monthly_map: Dict[str, Dict[str, int]] = {}
        for item in raw_data:
            month_key = item["date"][:7]  # YYYY-MM
            if month_key not in monthly_map:
                monthly_map[month_key] = {"income": 0, "expense": 0}
            monthly_map[month_key]["income"] += item["income"]
            monthly_map[month_key]["expense"] += item["expense"]
        
        # 生成连续月份
        result = []
        current_year, current_month = start.year, start.month
        end_year, end_month = end.year, end.month
        
        while (current_year, current_month) <= (end_year, end_month):
            month_key = f"{current_year:04d}-{current_month:02d}"
            if month_key in monthly_map:
                result.append({
                    "label": month_key,
                    "income": monthly_map[month_key]["income"] / 100.0,
                    "expense": monthly_map[month_key]["expense"] / 100.0,
                })
            else:
                result.append({
                    "label": month_key,
                    "income": 0.0,
                    "expense": 0.0,
                })
            
            if current_month == 12:
                current_year += 1
                current_month = 1
            else:
                current_month += 1
        
        return {"granularity": "month", "data": result}

    def _get_yearly_trend_advanced(
        self, start: date, end: date, category: Optional[str] = None
    ) -> Dict[str, Any]:
        """按年聚合，支持分类筛选"""
        raw_data = self.db.get_daily_summary_by_category(
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
            category
        )
        
        # 按年聚合
        yearly_map: Dict[str, Dict[str, int]] = {}
        for item in raw_data:
            year_key = item["date"][:4]  # YYYY
            if year_key not in yearly_map:
                yearly_map[year_key] = {"income": 0, "expense": 0}
            yearly_map[year_key]["income"] += item["income"]
            yearly_map[year_key]["expense"] += item["expense"]
        
        # 生成连续年份
        result = []
        for year in range(start.year, end.year + 1):
            year_key = f"{year:04d}"
            if year_key in yearly_map:
                result.append({
                    "label": year_key,
                    "income": yearly_map[year_key]["income"] / 100.0,
                    "expense": yearly_map[year_key]["expense"] / 100.0,
                })
            else:
                result.append({
                    "label": year_key,
                    "income": 0.0,
                    "expense": 0.0,
                })
        
        return {"granularity": "year", "data": result}

    def get_expense_categories(self, start_date: str, end_date: str) -> List[str]:
        """获取时间范围内的所有支出分类名称"""
        raw_data = self.db.get_category_summary(start_date, end_date, "expense")
        return [item["category"] for item in raw_data]

    def get_month_over_month_change(self) -> Dict[str, Any]:
        """获取环比变化（本月vs上月）"""
        current = self.get_current_month_summary()
        last = self.get_last_month_summary()
        
        expense_change = current.expense_cents - last.expense_cents
        income_change = current.income_cents - last.income_cents
        
        return {
            "expense_change_cents": expense_change,
            "expense_change": expense_change / 100.0,
            "expense_change_pct": (expense_change / last.expense_cents * 100) if last.expense_cents > 0 else 0,
            "income_change_cents": income_change,
            "income_change": income_change / 100.0,
            "income_change_pct": (income_change / last.income_cents * 100) if last.income_cents > 0 else 0,
        }

