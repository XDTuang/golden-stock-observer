#!/usr/bin/env python3
"""
兜金观测 — 交易日历与数据新鲜度辅助模块
==========================================

提供 A 股市场交易日判断与"数据新鲜度"判定所需的工具函数。

设计目标（与"数据更新策略精准度"直接相关）：
  1. 更新脚本只在真正的交易日、且收盘后运行 —— 避免把不完整/过期的
     K 线当作"今日数据"发布。
  2. 管线结束后可校验"最新数据日期"是否等于"最近一个交易日"，
     若不等则说明抓取不完整（周末/节假日/盘中/接口中断），应拒绝发布。

交易日规则：
  - 周六、周日为非交易日
  - 法定节假日为非交易日（下表按年维护，2026 已列出）
  - 调休补班日按"工作日"处理（即视为交易日，除非在休市表里）

坐标说明：所有日期按"本地时区（Asia/Shanghai）"处理，避免 UTC 偏差。
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

# ── A 股休市日（按年维护，格式 YYYY-MM-DD）──────────────────────
# 数据来源：上交所/深交所年度休市安排。每年末更新下一年度即可。
HOLIDAYS: dict[int, set[str]] = {
    2026: {
        # 元旦
        "2026-01-01",
        # 春节（2/15 至 2/22 调休，含周末）
        "2026-02-15", "2026-02-16", "2026-02-17", "2026-02-18",
        "2026-02-19", "2026-02-20", "2026-02-21", "2026-02-22",
        # 清明
        "2026-04-04", "2026-04-05", "2026-04-06",
        # 劳动节
        "2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04", "2026-05-05",
        # 端午
        "2026-06-19", "2026-06-20", "2026-06-21",
        # 中秋
        "2026-09-25", "2026-09-26", "2026-09-27",
        # 国庆
        "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
        "2026-10-05", "2026-10-06", "2026-10-07",
    },
}

# 调休补班日（周末上班，视为交易日）。若某休市日实际为补班，请勿列入本表。
MAKEUP_WORKDAYS: dict[int, set[str]] = {
    2026: {
        "2026-02-14",  # 春节前补班（周六）
        "2026-09-19",  # 中秋前补班（周六）
        "2026-10-10",  # 国庆后补班（周六）
    },
}

# A 股收盘时间（用于"盘后"判定）
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30


def _parse(date: _dt.date | str | None) -> Optional[_dt.date]:
    if date is None:
        return None
    if isinstance(date, _dt.date):
        return date
    return _dt.date.fromisoformat(str(date)[:10])


def is_holiday(d: _dt.date | str) -> bool:
    """给定日期是否为法定休市日（不含周末）。"""
    d = _parse(d)
    assert d is not None
    return d.isoformat() in HOLIDAYS.get(d.year, set())


def is_trading_day(d: _dt.date | str | None = None) -> bool:
    """
    判断给定日期（默认今天）是否为 A 股交易日。

    规则：周一到周五，且不在休市表中；补班周末视为交易日。
    """
    d = _parse(d) or _dt.date.today()
    # 补班日：即使是周末也算交易日
    if d.isoformat() in MAKEUP_WORKDAYS.get(d.year, set()):
        return True
    if d.weekday() >= 5:  # 5=Sat, 6=Sun
        return False
    if is_holiday(d):
        return False
    return True


def last_trading_day(d: _dt.date | str | None = None) -> _dt.date:
    """返回不晚于 d 的最近一个交易日（默认今天）。"""
    d = _parse(d) or _dt.date.today()
    while not is_trading_day(d):
        d -= _dt.timedelta(days=1)
    return d


def next_trading_day(d: _dt.date | str | None = None) -> _dt.date:
    """返回不早于 d 的下一个交易日（默认今天）。"""
    d = _parse(d) or _dt.date.today()
    while not is_trading_day(d):
        d += _dt.timedelta(days=1)
    return d


def market_close_passed(now: Optional[_dt.datetime] = None) -> bool:
    """
    当前是否已过今日收盘时间（15:30，含 30 分钟缓冲）。

    若今天不是交易日，则视为"已收盘"（不应在盘中更新）。
    """
    now = now or _dt.datetime.now()
    if not is_trading_day(now.date()):
        return True
    close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE,
                        second=0, microsecond=0)
    return now >= close


def should_update_now(now: Optional[_dt.datetime] = None,
                      force: bool = False) -> tuple[bool, str]:
    """
    综合判断是否"适合此刻执行数据更新"。

    Returns:
        (ok, reason)
        ok=False 时应中止自动更新（除非 force=True）。
    """
    if force:
        return True, "force 模式：跳过交易日/盘后校验"
    now = now or _dt.datetime.now()
    if not is_trading_day(now.date()):
        return False, f"{now.date()} 非交易日，跳过更新（如需强制请用 --force）"
    if not market_close_passed(now):
        return False, (f"尚未收盘（{now:%H:%M}，需 ≥ "
                       f"{MARKET_CLOSE_HOUR}:{MARKET_CLOSE_MINUTE}），"
                       f"盘中数据不完整，跳过更新")
    return True, "交易日且已收盘，可以更新"


def eval_freshness(latest_data_date: str,
                   now: Optional[_dt.datetime] = None) -> dict:
    """
    评估"最新数据日期"的新鲜度。

    Args:
        latest_data_date: 信号数据中最新的交易日（YYYY-MM-DD）
        now: 校验时刻（默认现在）

    Returns:
        {
          "latest_data_date": str,
          "expected_date": str,        # 期望的最新交易日 = last_trading_day(today)
          "is_fresh": bool,            # latest == expected
          "gap_days": int,            # expected - latest 的交易日差
          "checked_at": str,
          "status": "fresh" | "stale" | "future",
        }
    """
    now = now or _dt.datetime.now()
    expected = last_trading_day(now.date())
    if not market_close_passed(now):
        # 当日尚未收盘（盘前/盘中）：数据最晚只能到上一交易日，期望随之回退，
        # 避免凌晨/早盘把「昨日收盘数据」误判为 stale（2026-08-20 修复）
        expected = last_trading_day(now.date() - _dt.timedelta(days=1))
    latest = _parse(latest_data_date)

    status = "stale"
    is_fresh = False
    gap = 0
    if latest is not None:
        if latest > expected:
            status = "future"   # 数据日期晚于期望（时钟/时区异常）
        elif latest == expected:
            status = "fresh"
            is_fresh = True
        else:
            # 计算交易日差
            cur = latest
            while cur < expected:
                cur += _dt.timedelta(days=1)
                if is_trading_day(cur):
                    gap += 1
            status = "stale"

    return {
        "latest_data_date": latest_data_date,
        "expected_date": expected.isoformat(),
        "is_fresh": is_fresh,
        "gap_days": gap,
        "checked_at": now.isoformat(timespec="seconds"),
        "status": status,
    }


if __name__ == "__main__":
    import sys
    today = _dt.date.today()
    print(f"今天: {today}  是否交易日: {is_trading_day(today)}")
    print(f"最近交易日: {last_trading_day(today)}")
    print(f"下一交易日: {next_trading_day(today)}")
    print(f"已收盘: {market_close_passed()}")
    ok, reason = should_update_now()
    print(f"是否适合更新: {ok} — {reason}")
    if len(sys.argv) > 1:
        print("新鲜度:", eval_freshness(sys.argv[1]))
