# -*- coding: utf-8 -*-
"""HQChart_Train 数据后端(零第三方依赖, 用内置 http.server)
双路线:
  A. 通达信 vipdoc 本地(离线优先)
  B. AkShare(在线兜底/补分钟)  —— 二期接入, 先留接口
接口(均为 HQChart NetworkFilter 需要的数据):
  GET /api/kline?symbol=600006.sh&period=day&right=1
  GET /api/minute?symbol=600006.sh&date=20261016      # 分时图(单日分钟)
  GET /api/minute_kline?symbol=600006.sh&date=20261016 # 单日1分钟K(训练用)
  GET /api/symbols?q=600
  GET /api/health
"""
import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import tdx_reader
import ak_data
import store

store.init()  # 启动即建表

PORT = 8777
_NAME_CACHE = {}


def _name_of(symbol):
    if symbol in _NAME_CACHE:
        return _NAME_CACHE[symbol]
    return symbol.split(".")[0]


def _day_to_hq(bars):
    """通达信 .day 元组 -> HQChart 8元素数组"""
    data, prev = [], None
    for b in bars:
        yc = prev if prev is not None else b[1]
        data.append([b[0], round(yc, 4), b[1], b[2], b[3], b[4], b[5], b[6]])
        prev = b[4]
    return data


def kline_response(symbol, period="day", right=0):
    # 本地优先(不复权); 要复权或本地没有 -> AkShare 在线(带缓存)
    data = []
    if right == 0:
        bars = tdx_reader.read_day(symbol)
        if bars:
            data = _day_to_hq(bars)
    if not data:
        try:
            adj = "qfq" if right == 1 else ("hfq" if right == 2 else "")
            data = ak_data.daily(symbol, adj)
        except Exception as e:
            print("ak daily err:", symbol, e)
            data = []
    return {"name": _name_of(symbol), "symbol": symbol, "data": data,
            "ver": 2.0, "period": period, "right": right}


def minute_response(symbol, date):
    """分时图数据. 优先本地 .lc1; 无则返回空(前端提示走 AkShare/下载)."""
    bars = tdx_reader.read_lc(symbol, 1)
    if not bars:
        return {"code": 0, "stock": []}
    ymd = int(date)
    pts = [b for b in bars if b[0] == ymd]
    if not pts:
        return {"code": 0, "stock": []}
    day = tdx_reader.read_day(symbol)
    yclose = None
    for i, b in enumerate(day):
        if b[0] == ymd and i > 0:
            yclose = day[i - 1][4]
            break
    minute = [{"time": b[1], "price": b[2], "vol": b[3], "amount": b[4]} for b in pts]
    return {"code": 0, "stock": [{"date": ymd, "minute": minute,
                                  "yclose": yclose, "symbol": symbol,
                                  "name": _name_of(symbol)}]}


def minute_kline_response(symbol, date):
    """单日 1 分钟 K 线(训练按分钟推进用). 本地 .lc1 优先, 否则 AkShare 近期分钟."""
    data = []
    ymd = int(date) if str(date or "").isdigit() else 0
    # 1) 本地 .lc1
    try:
        bars = tdx_reader.read_lc(symbol, 1)
    except Exception as e:
        print("read_lc err:", symbol, e)
        bars = []
    lc_range = (bars[0][0], bars[-1][0]) if bars else None
    if not ymd and bars:
        ymd = bars[-1][0]  # 未指定日期 -> 自动取最新交易日
    pts = [b for b in bars if b[0] == ymd] if (bars and ymd) else []
    if pts:
        # read_lc 现返回 (ymd, hhmm, o, h, l, c, vol, amt); yclose 用当日首根开盘占位
        yclose = pts[0][2]
        for b in pts:
            dt = int(f"{b[0]}{b[1]:04d}")
            data.append([dt, round(yclose, 4), b[2], b[3], b[4], b[5], b[6], b[7]])
    else:
        # 2) AkShare 近期分钟
        try:
            mk = ak_data.minute(symbol, "1", "qfq")
            data = [row for row in mk if int(str(row[0])[:8]) == ymd]
        except Exception as e:
            print("ak minute err:", symbol, e)
            data = []
    return {"name": _name_of(symbol), "symbol": symbol, "data": data, "ver": 2.0,
            "date": ymd, "lc_range": lc_range}


def symbols_response(q):
    res = []
    root = tdx_reader.VIPDOC
    for mkt, folder, pre in (("sh", "sh", "sh"), ("sz", "sz", "sz")):
        d = os.path.join(root, folder, "lday")
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.endswith(".day"):
                continue
            code = fn[:-4]
            if code.startswith(q) or code == q:
                res.append({"symbol": f"{code[2:]}.{mkt}", "code": code[2:]})
                if len(res) >= 30:
                    return {"list": res}
    return {"list": res}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        path = u.path
        if path == "/api/trades":
            sym = q.get("symbol", [""])[0] or None
            mode = q.get("mode", [""])[0] or None
            return self._send({"list": store.list_trades(sym, mode)})
        if path == "/api/notes":
            sym = q.get("symbol", [""])[0] or None
            mode = q.get("mode", [""])[0] or None
            with_snap = q.get("snapshot", ["0"])[0] == "1"
            return self._send({"list": store.list_notes(sym, mode, with_snap)})
        if path == "/api/note/delete":
            nid = int(q.get("id", ["0"])[0])
            store.delete_note(nid)
            return self._send({"ok": True})
        if path == "/api/export":
            kind = q.get("type", ["trades"])[0]
            sym = q.get("symbol", [""])[0] or None
            mode = q.get("mode", [""])[0] or None
            return self._send_csv(kind, store.export_csv(kind, sym, mode))
        if path == "/api/health":
            return self._send({"ok": True, "vipdoc": os.path.exists(tdx_reader.VIPDOC)})
        if path == "/api/kline":
            sym = q.get("symbol", ["600006.sh"])[0]
            per = q.get("period", ["day"])[0]
            right = int(q.get("right", ["0"])[0])
            return self._send(kline_response(sym, per, right))
        if path == "/api/minute":
            sym = q.get("symbol", ["600006.sh"])[0]
            dt = q.get("date", [""])[0]
            return self._send(minute_response(sym, dt))
        if path == "/api/minute_kline":
            sym = q.get("symbol", ["600006.sh"])[0]
            dt = q.get("date", [""])[0]
            return self._send(minute_kline_response(sym, dt))
        if path == "/api/symbols":
            pre = q.get("q", [""])[0]
            return self._send(symbols_response(pre))
        if path == "/api/name":
            sym = q.get("symbol", [""])[0]
            try:
                return self._send({"symbol": sym, "name": ak_data.name(sym)})
            except Exception as e:
                return self._send({"symbol": sym, "name": sym.split(".")[0], "err": str(e)})
        return self._send({"error": "unknown path " + path})

    def _send_csv(self, kind, text):
        body = text.encode("utf-8-sig")  # BOM 让 Excel 正确识别 UTF-8
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Disposition",
                         f"attachment; filename={kind}.csv")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        path = u.path
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = {}
        if path == "/api/trade":
            store.add_trade(body)
            return self._send({"ok": True})
        if path == "/api/note":
            store.add_note(body)
            return self._send({"ok": True})
        return self._send({"error": "unknown path " + path})


if __name__ == "__main__":
    print(f"HQChart_Train backend on http://127.0.0.1:{PORT}  (vipdoc={tdx_reader.VIPDOC})")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
