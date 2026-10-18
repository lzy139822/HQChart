# -*- coding: utf-8 -*-
"""AkShare 在线数据路线 + 本地缓存(断网可复用)。
日线: 全史, 支持前/后/不复权。
分钟: 仅近期(约5个交易日)。
输出统一为 HQChart 8元素数组: [date, 昨收, 开, 高, 低, 收, 量, 额]
"""
import os
import json
import time

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
DAILY_TTL = 86400        # 日线缓存 1 天
MINUTE_TTL = 3600        # 分钟缓存 1 小时


def _path(key):
    return os.path.join(CACHE_DIR, key + ".json")


def _get(key, ttl):
    p = _path(key)
    if os.path.exists(p) and (time.time() - os.path.getmtime(p) < ttl):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _set(key, data):
    try:
        with open(_path(key), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def _code(symbol):
    return symbol.split(".")[0]


def daily(symbol, adjust="qfq"):
    """日线全史 -> [[date, yclose, o, h, l, c, vol, amount], ...]"""
    key = f"daily_{symbol}_{adjust}"
    c = _get(key, DAILY_TTL)
    if c is not None:
        return c
    import akshare as ak
    df = ak.stock_zh_a_hist(symbol=_code(symbol), period="daily", adjust=adjust)
    rows, prev = [], None
    for _, r in df.iterrows():
        d = int(str(r["日期"])[:10].replace("-", ""))
        o, h, l, cl = float(r["开盘"]), float(r["最高"]), float(r["最低"]), float(r["收盘"])
        v, a = int(r["成交量"]), float(r["成交额"])
        yc = prev if prev is not None else o
        rows.append([d, round(yc, 4), o, h, l, cl, v, a])
        prev = cl
    _set(key, rows)
    return rows


def minute(symbol, period="1", adjust="qfq"):
    """分钟K(近期) -> [[yyyymmddhhmm, yclose, o, h, l, c, vol, amount], ...]"""
    key = f"min_{symbol}_{period}_{adjust}"
    c = _get(key, MINUTE_TTL)
    if c is not None:
        return c
    import akshare as ak
    df = ak.stock_zh_a_hist_min_em(symbol=_code(symbol), period=period, adjust=adjust)
    rows, prev = [], None
    for _, r in df.iterrows():
        t = str(r["时间"]).replace("-", "").replace(":", "").replace(" ", "")
        d = int(t[:12])  # YYYYMMDDHHMM
        o, h, l, cl = float(r["开盘"]), float(r["最高"]), float(r["最低"]), float(r["收盘"])
        v, a = int(r["成交量"]), float(r["成交额"])
        yc = prev if prev is not None else o
        rows.append([d, round(yc, 4), o, h, l, cl, v, a])
        prev = cl
    _set(key, rows)
    return rows


def name(symbol):
    key = f"name_{symbol}"
    c = _get(key, DAILY_TTL * 30)
    if c:
        return c[0]
    import akshare as ak
    try:
        df = ak.stock_individual_info_em(symbol=_code(symbol))
        nm = str(df[df["item"] == "股票简称"]["value"].iloc[0])
    except Exception:
        nm = _code(symbol)
    _set(key, [nm])
    return nm
