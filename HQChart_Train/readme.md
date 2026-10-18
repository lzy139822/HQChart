# HQChart 训练 + 宝典 说明

把 HQChart 行情图改成**可模拟训练**的看盘/复盘工具：K线训练、分时(按分钟)训练、自动回放、买卖点图标、宝典(交易日志+快照)、宝典库(带分组树)。所有操作记录与观点存本地 SQLite，便于日后回放当时图样与点位。

## 目录结构

```
I:\HQChart\HQChart_Train\
├─ start.bat                # 一键启动(后台+前端+浏览器)
├─ readme.md                # 本说明
└─ backend\
   ├─ server.py             # Python 后台, 监听 127.0.0.1:8777
   ├─ tdx_reader.py         # 读取通达信 vipdoc 本地数据(.day/.lc1)
   ├─ store.py              # SQLite 存储(宝典/交易)
   └─ train.db              # 数据库(自动建表)

I:\HQChart\webhqchart.demo\   # 前端静态资源(由 start.bat 起 http.server 8000 提供)
├─ Demo_hqchart\hq_train.html     # K线训练(浮层)
├─ samples\minute_train.html      # 分时(按分钟)训练
├─ samples\baodian.html           # 宝典库(左分组树 + 右快照/备注)
└─ samples\review.html            # 复盘
```

## 环境要求

- Python 3.12：`G:\Python312\python.exe`（后台与前端静态服务都用它）
- 本地行情源：通达信数据目录 `D:\tdx\vipdoc`（分时训练需要 `.lc1` 分钟文件；K线训练用 HQChart 网络数据，可不依赖）

## 一键启动

双击 `start.bat`：
1. 启动后台 `server.py`（端口 8777）
2. 启动前端静态服务 `python -m http.server 8000`（根目录 `I:\HQChart\webhqchart.demo`）
3. 自动打开浏览器两个标签：
   - K线训练：`http://localhost:8000/Demo_hqchart/hq_train.html`
   - 分时训练：`http://localhost:8000/samples/minute_train.html`

脚本已做：UTF-8 模式(`PYTHONUTF8=1` + `chcp 65001`)规避中文乱码；端口占用检测，重复双击不会报错。
**关闭程序**：关掉那两个最小化黑窗即可。

## 手动启动（备用）

```bat
REM 1) 后台
G:\Python312\python.exe I:\HQChart\HQChart_Train\backend\server.py

REM 2) 另开窗口, 前端静态服务
cd /d I:\HQChart\webhqchart.demo
G:\Python312\python.exe -m http.server 8000

REM 3) 浏览器打开上面的 URL
```

## 使用要点

- **K线训练**：打开 hq_train 页面 → 🎯 训练 → 选「分时按分钟训练」或K线 → 用日期日历选起始日(留空=最新) → 按 →/空格 推进，或勾「自动」连续推进；买/卖按钮交易，支持**多次补仓**(按成交量加权算持仓均价)，平仓后结算。
- **分时训练**：选股票+日期(留空=最新交易日，日历选) → 加载 → ▶ 自动播放(速度滑块=毫秒/根，往右更慢) → 买卖点**红买/绿卖箭头**钉在分时线上。
- **结算信息**：顶部显示 交易数/胜率/已实现盈亏/收益率，信息条实时显示持仓均价+浮动盈亏。
- **宝典（📒）**：训练中点宝典 → 弹窗(品种/行情时间/名称/分组/操作 自动填，可改)+ 快照预览(带买卖箭头)+ 备注 → 确定即存。
- **宝典库（📖）**：左侧分组树，点条目看右侧**当时图样(带点位标记)+ 操作标签 + 备注**，可删除。
- **复盘（📊）**：汇总交易/宝典记录。

## 数据来源与日期范围

- 分钟数据来自 `D:\tdx\vipdoc\sh\minline\*.lc1`(1分钟)。文件只含**最近一段时间**(通常数周到数月)，若选的日期不在范围内会提示「本地分钟文件含：YYYYMMDD ~ YYYYMMDD」，改用区间内日期或留空取最新即可。
- 想补充某只票某天的分钟数据：在通达信里下载该票 1 分钟图，再回到训练页加载。

## 常见问题

- **页面打不开/取不到数据**：确认两个黑窗都在运行(端口 8777/8000 在监听)。
- **中文乱码**：用 `start.bat` 启动即可(已设 UTF-8)；不要单独在 GBK 控制台手动跑 `server.py` 后看它的中文输出。
- **端口被占用**：关闭旧的后台/前端窗口再双击 `start.bat`（脚本会自动跳过已占用的端口）。
- **想重置数据**：关闭后台后删除 `I:\HQChart\HQChart_Train\backend\train.db`，重启会重新建表(原有宝典/交易记录会清空)。
