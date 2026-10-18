# -*- coding: utf-8 -*-
"""通达信 vipdoc 本地数据读取器
- 日线 .day: 32 字节/条 (date,o,h,l,c /100, amount float, vol int, 备用)
- 1分钟 .lc1 / 5分钟 .lc5: 32 字节/条 (date YYYYMMDD, time HHMM /100? 见下)
日期编码与 .day 相同(整日日期), 时间为 0 起的分钟偏移, 按通达信规则解析.
"""
import os
import struct

VIPDOC = r"D:\tdx\vipdoc"
_LC_CACHE = {}   # .lc1 读取缓存(按 symbol+minute), 加速重复加载

# .day 单条: <5i1f1i 实际是 日期int, 开int, 高int, 低int, 收int, 额float, 量int, 留int = 32B
_DAY_STRUCT = struct.Struct("<iiiiifii")


def _market_dir(symbol: str):
    s = symbol.lower()
    code, mkt = s.split(".")
    if mkt == "sh":
        return "sh"
    if mkt == "sz":
        return "sz"
    if mkt == "bj":
        return "bj"
    raise ValueError("bad market: " + symbol)


def read_day(symbol: str):
    """读日线 .day, 返回 [(yyyymmdd, open, high, low, close, vol, amount), ...] 升序."""
    code, mkt = symbol.lower().split(".")
    path = os.path.join(VIPDOC, _market_dir(symbol), "lday", f"{mkt}{code}.day")
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "rb") as f:
        data = f.read()
    n = len(data) // 32
    for i in range(n):
        d, o, h, l, c, amt, vol, _ = _DAY_STRUCT.unpack_from(data, i * 32)
        if d < 19900101:
            continue
        out.append((d, o / 100.0, h / 100.0, l / 100.0, c / 100.0, vol, amt))
    return out


# 通达信 1/5分钟 .lc1/.lc5: 32字节/条
#   ushort 日期 = (年-2004)*2048 + 月*100 + 日
#   ushort 时间 = 时*60 + 分 (571=09:31, 900=15:00)
#   float 开/高/低/收/额, uint 量, uint 备用
_LC_STRUCT = struct.Struct("<HHfffffII")


def read_lc(symbol: str, minute=1):
    """读 1/5 分钟 .lc1/.lc5. 返回 [(yyyymmdd, hhmm, o, h, l, c, vol, amt), ...]."""
    key = (symbol.lower(), minute)
    if key in _LC_CACHE:
        return _LC_CACHE[key]
    code, mkt = symbol.lower().split(".")
    sub = "minline"
    ext = "lc1" if minute == 1 else "lc5"
    path = os.path.join(VIPDOC, _market_dir(symbol), sub, f"{mkt}{code}.{ext}")
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "rb") as f:
        data = f.read()
    n = len(data) // 32
    for i in range(n):
        days, mins, o, h, l, c, amt, vol, _pad = _LC_STRUCT.unpack_from(data, i * 32)
        y = 2004 + (days >> 11); rem = days & 0x7FF
        ymd = y * 10000 + (rem // 100) * 100 + (rem % 100)
        hh, mm = divmod(mins, 60)
        hhmm = hh * 100 + mm
        out.append((ymd, hhmm, o, h, l, c, vol, amt))
    _LC_CACHE[key] = out
    return out


def lc_dates(symbol: str, minute=1):
    """文件内全部交易日(去重升序)."""
    return sorted({b[0] for b in read_lc(symbol, minute)})


def has_day(symbol: str) -> bool:
    code, mkt = symbol.lower().split(".")
    return os.path.exists(os.path.join(VIPDOC, _market_dir(symbol), "lday", f"{mkt}{code}.day"))


def has_lc(symbol: str, minute=1) -> bool:
    code, mkt = symbol.lower().split(".")
    ext = "lc1" if minute == 1 else "lc5"
    return os.path.exists(os.path.join(VIPDOC, _market_dir(symbol), "minline", f"{mkt}{code}.{ext}"))


if __name__ == "__main__":
    import sys
    sym = sys.argv[1] if len(sys.argv) > 1 else "600006.sh"
    bars = read_day(sym)
    print(f"{sym} day bars={len(bars)}")
    for b in bars[:3]:
        print(b)
    print("...")
    for b in bars[-3:]:
        print(b)
    print("has_lc1:", has_lc(sym, 1))
