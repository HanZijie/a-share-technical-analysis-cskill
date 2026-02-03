---
name: a-share-technical-analysis-cskill
description: A股市场技术分析技能，提供股票技术指标分析、实时行情、涨跌榜、指数分析、资金流向等功能。支持布林带、RSI、MACD、KDJ、ADX等技术指标计算，基于 AKShare 数据源，覆盖上交所、深交所全部A股。
version: 1.0.0
---

# A股技术分析技能

## 概述

这是一个专业的 A 股市场技术分析技能，基于 AKShare 数据源，提供完整的股票技术指标分析能力。

**核心能力：**
- 📊 **股票技术分析**：布林带、RSI、MACD、KDJ、ADX 等指标
- 📈 **实时行情**：获取 A 股实时报价
- 🏆 **涨跌榜**：今日涨幅/跌幅排行
- 🔍 **股票搜索**：按名称或代码搜索
- 📉 **指数分析**：上证、深证、创业板等指数技术分析
- 💰 **资金流向**：行业资金流向、北向资金

**数据覆盖：**
- 上海证券交易所 (SSE)：60/68 开头
- 深圳证券交易所 (SZSE)：00/30 开头
- 北京证券交易所 (BSE)：8/4 开头

## 何时使用此技能

**✅ 应该使用：**
- 用户询问 A 股股票的技术分析
- 用户想查看股票的 RSI、MACD、布林带等技术指标
- 用户想了解今日涨跌幅榜
- 用户询问北向资金或行业资金流向
- 用户想分析上证、深证、创业板等指数
- 用户搜索股票代码或名称
- 用户询问某只股票的实时行情

**❌ 不应使用：**
- 用户询问美股、港股等非 A 股市场
- 用户询问基金、债券、期货等非股票产品
- 用户需要深度基本面分析（详细财报解读）
- 用户需要量化交易策略编写

## 使用方法

### 前置条件

确保已安装依赖：
```bash
pip install akshare pandas numpy pyarrow
```

### 运行脚本

所有功能通过 `scripts/a_share_analyzer.py` 脚本提供。

**基本用法：**
```bash
cd /Users/hanzijie/tradingview-akshare-mcp/.claude/skills/a-share-technical-analysis-cskill
python scripts/a_share_analyzer.py <command> [arguments]
```

## 可用命令

### 1. stock_analysis - 股票完整技术分析

分析单只股票的技术面，包括布林带、RSI、MACD、KDJ、ADX 等指标。

**命令格式：**
```bash
python scripts/a_share_analyzer.py stock_analysis --symbol <股票代码> [--period daily|weekly|monthly] [--days 365]
```

**参数说明：**
| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| --symbol | ✅ | - | 6位股票代码，如 601138、000001 |
| --period | ❌ | daily | 时间周期：daily(日线)、weekly(周线)、monthly(月线) |
| --days | ❌ | 365 | 历史数据天数（30-3650） |

**示例：**
```bash
# 分析工业富联（日线，1年数据）
python scripts/a_share_analyzer.py stock_analysis --symbol 601138

# 分析茅台（周线，2年数据）
python scripts/a_share_analyzer.py stock_analysis --symbol 600519 --period weekly --days 730
```

**输出内容：**
- 基本信息：股票代码、名称、当前价格
- 价格数据：开盘、最高、最低、收盘、涨跌幅、成交量、换手率
- 布林带分析：上轨、中轨、下轨、BBW、信号判断
- 技术指标：RSI、MACD、KDJ、ADX、EMA50、EMA200
- 关键价位：支撑位、阻力位
- 综合评分：-10 到 +10 的评分及买卖建议

**技术指标解读：**

| 指标 | 超买区 | 中性区 | 超卖区 | 说明 |
|------|--------|--------|--------|------|
| RSI | >70 | 30-70 | <30 | 相对强弱指数 |
| KDJ (K值) | >80 | 20-80 | <20 | 随机指标 |
| ADX | >25 强趋势 | 20-25 中等 | <20 弱趋势 | 趋势强度 |

### 2. stock_quote - 实时行情快照

获取单只股票的实时行情。

**命令格式：**
```bash
python scripts/a_share_analyzer.py stock_quote --symbol <股票代码>
```

**示例：**
```bash
python scripts/a_share_analyzer.py stock_quote --symbol 000001
```

**输出内容：**
- 股票代码、名称
- 当前价格、涨跌额、涨跌幅
- 今开、最高、最低
- 成交量、成交额、换手率
- 市盈率(PE)、市净率(PB)

### 3. top_gainers - 涨幅榜

获取今日 A 股涨幅排行。

**命令格式：**
```bash
python scripts/a_share_analyzer.py top_gainers [--limit 20]
```

**示例：**
```bash
# 涨幅榜前20
python scripts/a_share_analyzer.py top_gainers

# 涨幅榜前10
python scripts/a_share_analyzer.py top_gainers --limit 10
```

### 4. top_losers - 跌幅榜

获取今日 A 股跌幅排行。

**命令格式：**
```bash
python scripts/a_share_analyzer.py top_losers [--limit 20]
```

### 5. stock_search - 搜索股票

按名称或代码搜索股票。

**命令格式：**
```bash
python scripts/a_share_analyzer.py stock_search --keyword <关键词>
```

**示例：**
```bash
# 搜索茅台
python scripts/a_share_analyzer.py stock_search --keyword 茅台

# 搜索平安
python scripts/a_share_analyzer.py stock_search --keyword 平安

# 按代码搜索
python scripts/a_share_analyzer.py stock_search --keyword 601
```

### 6. index_analysis - 指数分析

分析 A 股主要指数的技术面。

**命令格式：**
```bash
python scripts/a_share_analyzer.py index_analysis --symbol <指数代码> [--period daily|weekly|monthly]
```

**主要指数代码：**
| 代码 | 名称 |
|------|------|
| 000001 | 上证指数 |
| 399001 | 深证成指 |
| 399006 | 创业板指 |
| 000300 | 沪深300 |
| 000016 | 上证50 |
| 000905 | 中证500 |
| 000688 | 科创50 |

**示例：**
```bash
# 分析上证指数
python scripts/a_share_analyzer.py index_analysis --symbol 000001

# 分析创业板指（周线）
python scripts/a_share_analyzer.py index_analysis --symbol 399006 --period weekly
```

### 7. sector_flow - 行业资金流向

获取行业板块资金流向排行。

**命令格式：**
```bash
python scripts/a_share_analyzer.py sector_flow [--limit 20]
```

**输出内容：**
- 行业名称
- 今日涨跌幅
- 主力净流入金额
- 主力净流入占比

### 8. north_flow - 北向资金

获取北向资金（沪港通、深港通）流入数据。

**命令格式：**
```bash
python scripts/a_share_analyzer.py north_flow
```

**输出内容：**
- 日期
- 当日净买入额
- 买入成交额
- 卖出成交额
- 历史累计净买额

### 9. cache_stats - 缓存统计

查看本地缓存的历史数据文件。

**命令格式：**
```bash
python scripts/a_share_analyzer.py cache_stats
```

### 10. clear_cache - 清空缓存

清空缓存数据。

**命令格式：**
```bash
python scripts/a_share_analyzer.py clear_cache [--cache_type memory|local|all] [--symbol <股票代码>]
```

**示例：**
```bash
# 清空内存缓存
python scripts/a_share_analyzer.py clear_cache --cache_type memory

# 清空某只股票的本地缓存
python scripts/a_share_analyzer.py clear_cache --cache_type local --symbol 601138

# 清空所有缓存
python scripts/a_share_analyzer.py clear_cache --cache_type all
```

## 技术指标详解

### 布林带 (Bollinger Bands)

布林带由三条线组成：
- **上轨 (BB_upper)**：中轨 + 2倍标准差
- **中轨 (SMA20)**：20日简单移动平均线
- **下轨 (BB_lower)**：中轨 - 2倍标准差
- **BBW**：带宽百分比 = (上轨-下轨)/中轨

**信号解读：**
- 价格 > 上轨：超买，卖出信号
- 价格 < 下轨：超卖，买入信号
- BBW 收窄：波动性降低，可能即将突破
- BBW 扩大：波动性增加，趋势可能加强

### RSI (相对强弱指数)

14日 RSI 计算公式：
```
RS = 平均上涨幅度 / 平均下跌幅度
RSI = 100 - (100 / (1 + RS))
```

**信号解读：**
- RSI > 70：超买区，考虑卖出
- RSI < 30：超卖区，考虑买入
- RSI 55-70：偏强
- RSI 30-45：偏弱

### MACD (指数平滑异同移动平均线)

- **MACD线**：12日EMA - 26日EMA
- **信号线**：MACD的9日EMA
- **柱状图**：MACD - 信号线

**信号解读：**
- 金叉（MACD上穿信号线）：买入信号
- 死叉（MACD下穿信号线）：卖出信号
- 柱状图放大：趋势加强
- 柱状图缩小：趋势减弱

### KDJ (随机指标)

- **K值**：当前收盘价在N日高低价区间的位置
- **D值**：K值的3日移动平均

**信号解读：**
- K > 80：超买
- K < 20：超卖
- K 上穿 D：金叉，买入信号
- K 下穿 D：死叉，卖出信号

### ADX (平均趋向指标)

衡量趋势强度，不判断方向。

**信号解读：**
- ADX > 25：强趋势市场
- ADX 20-25：中等趋势
- ADX < 20：弱趋势或震荡市

## 综合评分系统

综合评分范围：-10 到 +10

**评分因素：**
| 因素 | 看多 | 看空 |
|------|------|------|
| RSI超卖(<30) | +2 | - |
| RSI超买(>70) | - | -2 |
| MACD金叉向上 | +2 | - |
| MACD死叉向下 | - | -2 |
| 布林带超卖 | +2 | - |
| 布林带超买 | - | -2 |
| 多头排列 | +2 | - |
| KDJ超卖 | +1 | - |
| KDJ超买 | - | -1 |

**综合判断：**
| 评分 | 判断 |
|------|------|
| ≥4 | 强烈看多 |
| 2-3 | 看多 |
| -1 到 1 | 中性 |
| -3 到 -2 | 看空 |
| ≤-4 | 强烈看空 |

## 缓存机制

### 内存缓存
- 实时行情数据：30秒 TTL
- 其他实时数据：60秒 TTL

### 本地缓存
- 历史K线数据：Parquet 格式持久化
- 缓存目录：`~/.akshare_cache/`
- 自动增量更新：落后超过2天自动刷新

## 数据源

数据来自 AKShare，支持多源自动切换：

**实时行情：**
1. 东方财富全市场 (优先)
2. 新浪财经
3. 分板块合并

**股票历史：**
1. 东方财富 (优先)
2. 腾讯财经

**指数历史：**
1. 东方财富 (优先)
2. 中证指数

## 错误处理

**常见错误及解决方案：**

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| Invalid symbol format | 股票代码格式错误 | 使用6位数字代码 |
| No data found | 找不到数据 | 检查股票代码是否正确 |
| Insufficient data | 数据量不足 | 增加 --days 参数或换用日线 |
| 所有数据源都不可用 | 网络问题或API限制 | 稍后重试或检查网络 |

## 使用示例

### 场景1：分析茅台技术面

用户：帮我分析一下茅台的技术面

执行：
```bash
python scripts/a_share_analyzer.py stock_analysis --symbol 600519
```

### 场景2：查看今日涨幅榜

用户：今天 A 股涨幅榜前十是哪些？

执行：
```bash
python scripts/a_share_analyzer.py top_gainers --limit 10
```

### 场景3：上证指数分析

用户：上证指数现在 RSI 是多少？

执行：
```bash
python scripts/a_share_analyzer.py index_analysis --symbol 000001
```

### 场景4：搜索股票代码

用户：帮我搜一下工业富联的股票代码

执行：
```bash
python scripts/a_share_analyzer.py stock_search --keyword 工业富联
```

### 场景5：北向资金

用户：北向资金今天流入多少？

执行：
```bash
python scripts/a_share_analyzer.py north_flow
```

### 场景6：行业资金流向

用户：看看今天哪些行业资金流入最多

执行：
```bash
python scripts/a_share_analyzer.py sector_flow --limit 10
```

## 注意事项

1. **股票代码格式**：必须是6位数字，如 `601138`、`000001`
2. **指数代码**：上证指数是 `000001`，注意与平安银行 `000001` 区分，指数使用 `index_analysis` 命令
3. **数据延迟**：实时数据有30秒缓存，历史数据有本地缓存
4. **网络依赖**：首次使用需要网络获取数据
5. **交易时间**：非交易时间获取的是上一交易日收盘数据

## 关键词

A股、股票、技术分析、布林带、RSI、MACD、KDJ、ADX、涨跌榜、涨幅榜、跌幅榜、
北向资金、沪港通、深港通、资金流向、行业资金、上证指数、深证成指、创业板指、
沪深300、上证50、中证500、实时行情、股票搜索、技术指标、均线、EMA、SMA、
支撑位、阻力位、超买、超卖、金叉、死叉、趋势分析、工业富联、茅台、平安
