# A股技术分析 Claude Skill

基于 AKShare 数据源的 A 股市场技术分析技能，提供完整的股票技术指标分析能力。

## 功能特性

- 📊 **股票技术分析**：布林带、RSI、MACD、KDJ、ADX 等指标
- 📈 **实时行情**：获取 A 股实时报价
- 🏆 **涨跌榜**：今日涨幅/跌幅排行
- 🔍 **股票搜索**：按名称或代码搜索
- 📉 **指数分析**：上证、深证、创业板等指数技术分析
- 💰 **资金流向**：行业资金流向、北向资金

## 安装

### 1. 安装依赖

```bash
pip install akshare pandas numpy pyarrow
```

### 2. 安装 Skill

```bash
cd /Users/hanzijie/tradingview-akshare-mcp/.claude/skills
# Skill 已自动加载，无需额外安装
```

## 使用方法

### 命令行使用

```bash
cd /Users/hanzijie/tradingview-akshare-mcp/.claude/skills/a-share-technical-analysis-cskill

# 股票技术分析
python scripts/a_share_analyzer.py stock_analysis --symbol 600519

# 实时行情
python scripts/a_share_analyzer.py stock_quote --symbol 000001

# 涨幅榜
python scripts/a_share_analyzer.py top_gainers --limit 10

# 跌幅榜
python scripts/a_share_analyzer.py top_losers --limit 10

# 搜索股票
python scripts/a_share_analyzer.py stock_search --keyword 茅台

# 指数分析
python scripts/a_share_analyzer.py index_analysis --symbol 000001

# 行业资金流向
python scripts/a_share_analyzer.py sector_flow --limit 10

# 北向资金
python scripts/a_share_analyzer.py north_flow

# 缓存统计
python scripts/a_share_analyzer.py cache_stats

# 清空缓存
python scripts/a_share_analyzer.py clear_cache --cache_type all
```

### 在 Claude 中使用

直接用自然语言提问：

- "帮我分析一下茅台的技术面"
- "今天 A 股涨幅榜前十"
- "上证指数的 RSI 是多少"
- "北向资金今天流入多少"
- "搜索工业富联的股票代码"

## 主要指数代码

| 代码 | 名称 |
|------|------|
| 000001 | 上证指数 |
| 399001 | 深证成指 |
| 399006 | 创业板指 |
| 000300 | 沪深300 |
| 000016 | 上证50 |
| 000905 | 中证500 |

## 技术指标说明

| 指标 | 超买 | 超卖 | 说明 |
|------|------|------|------|
| RSI | >70 | <30 | 相对强弱指数 |
| KDJ | >80 | <20 | 随机指标 |
| ADX | >25 强趋势 | <20 弱趋势 | 趋势强度 |

## 数据源

- 东方财富 (优先)
- 新浪财经
- 腾讯财经
- 中证指数

## 缓存机制

- 实时数据：30秒内存缓存
- 历史数据：本地 Parquet 文件持久化
- 缓存目录：`~/.akshare_cache/`

## 许可证

MIT License
