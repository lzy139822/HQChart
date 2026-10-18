# -*- coding: utf-8 -*-
"""SQLite 存盘: 交易记录(trades) + 宝典笔记/快照(notes). 单文件库, 自动建表, 零第三方依赖."""
import os
import io
import csv
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "train.db")


def _conn():
    conn = __import__("sqlite3").connect(DB_PATH)
    conn.row_factory = __import__("sqlite3").Row
    return conn


def init():
    conn = _conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS trades(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, mode TEXT,
        buy_time TEXT, buy_price REAL,
        sell_time TEXT, sell_price REAL,
        vol INTEGER, pnl REAL,
        created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS notes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, mode TEXT,
        name TEXT, grp TEXT,
        op TEXT, op_time TEXT, op_price REAL,
        bar_time TEXT, comment TEXT,
        snapshot TEXT,
        created_at TEXT)""")
    # 旧库补列(已存在则忽略)
    for col, typ in (("name", "TEXT"), ("grp", "TEXT"), ("op", "TEXT"),
                     ("op_time", "TEXT"), ("op_price", "REAL")):
        try:
            c.execute(f"ALTER TABLE notes ADD COLUMN {col} {typ}")
        except Exception:
            pass
    conn.commit()
    conn.close()


def add_trade(t):
    conn = _conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO trades(symbol,mode,buy_time,buy_price,sell_time,sell_price,vol,pnl,created_at)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (t.get("symbol"), t.get("mode"), t.get("buy_time"), t.get("buy_price"),
         t.get("sell_time"), t.get("sell_price"), t.get("vol"), t.get("pnl"),
         datetime.datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


def add_note(n):
    conn = _conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO notes(symbol,mode,name,grp,op,op_time,op_price,bar_time,comment,snapshot,created_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (n.get("symbol"), n.get("mode"), n.get("name"), n.get("grp"),
         n.get("op"), n.get("op_time"), n.get("op_price"),
         n.get("bar_time"), n.get("comment"), n.get("snapshot"),
         datetime.datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    conn.close()


def delete_note(note_id):
    conn = _conn()
    c = conn.cursor()
    c.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()
    conn.close()


def _where(symbol, mode):
    clauses, args = [], []
    if symbol:
        clauses.append("symbol=?")
        args.append(symbol)
    if mode:
        clauses.append("mode=?")
        args.append(mode)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", args


def list_trades(symbol=None, mode=None):
    conn = _conn()
    c = conn.cursor()
    w, a = _where(symbol, mode)
    rows = c.execute("SELECT * FROM trades" + w + " ORDER BY id DESC", a).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_notes(symbol=None, mode=None, with_snapshot=False):
    conn = _conn()
    c = conn.cursor()
    w, a = _where(symbol, mode)
    cols = ("id,symbol,mode,name,grp,op,op_time,op_price,bar_time,comment,created_at"
            + (",snapshot" if with_snapshot else ""))
    rows = c.execute("SELECT " + cols + " FROM notes" + w + " ORDER BY id DESC", a).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def export_csv(kind, symbol=None, mode=None):
    if kind == "trades":
        rows = list_trades(symbol, mode)
        cols = ["id", "symbol", "mode", "buy_time", "buy_price", "sell_time",
                "sell_price", "vol", "pnl", "created_at"]
    else:
        rows = list_notes(symbol, mode)
        cols = ["id", "symbol", "mode", "name", "grp", "op", "op_time",
                "op_price", "bar_time", "comment", "created_at"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols)
    for r in rows:
        w.writerow([r.get(c, "") for c in cols])
    return buf.getvalue()
