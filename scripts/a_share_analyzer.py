#!/usr/bin/env python3
"""
A股技术分析工具 - Claude Skill 脚本
基于 AKShare 数据源，提供完整的 A 股技术分析功能
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

try:
    import akshare as ak
except ImportError:
    print("错误: 请先安装 akshare: pip install akshare")
    sys.exit(1)


# ============== 缓存系统 ==============

class CacheManager:
    """
    缓存管理器
    - 内存缓存：用于实时数据，带 TTL
    - 本地缓存：用于历史K线数据，持久化存储
    """
    
    def __init__(self, cache_dir: str = None):
        self._memory_cache: dict[str, tuple[Any, float]] = {}
        if cache_dir is None:
            cache_dir = os.path.join(os.path.expanduser("~"), ".akshare_cache")
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._default_ttl = 60
    
    def _get_file_path(self, symbol: str, period: str, data_type: str = "stock") -> Path:
        return self._cache_dir / f"{data_type}_{symbol}_{period}.parquet"
    
    def get_memory(self, key: str, ttl: int = None) -> Optional[Any]:
        if key not in self._memory_cache:
            return None
        data, timestamp = self._memory_cache[key]
        ttl = ttl or self._default_ttl
        if datetime.now().timestamp() - timestamp > ttl:
            del self._memory_cache[key]
            return None
        return data
    
    def set_memory(self, key: str, data: Any) -> None:
        self._memory_cache[key] = (data, datetime.now().timestamp())
    
    def get_realtime_quotes(self) -> Optional[pd.DataFrame]:
        return self.get_memory("realtime_quotes", ttl=30)
    
    def set_realtime_quotes(self, df: pd.DataFrame) -> None:
        self.set_memory("realtime_quotes", df)
    
    def get_historical_data(
        self, symbol: str, period: str, start_date: str, end_date: str, data_type: str = "stock"
    ) -> Optional[pd.DataFrame]:
        file_path = self._get_file_path(symbol, period, data_type)
        if not file_path.exists():
            return None
        try:
            df = pd.read_parquet(file_path)
            if df.empty:
                return None
            df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
            start_dt = datetime.strptime(start_date, "%Y%m%d").strftime('%Y-%m-%d')
            end_dt = datetime.strptime(end_date, "%Y%m%d").strftime('%Y-%m-%d')
            filtered = df[(df['日期'] >= start_dt) & (df['日期'] <= end_dt)].copy()
            if filtered.empty:
                return None
            cached_last_date = df['日期'].max()
            cached_last_dt = datetime.strptime(cached_last_date, '%Y-%m-%d')
            end_dt_obj = datetime.strptime(end_dt, '%Y-%m-%d')
            if (end_dt_obj - cached_last_dt).days > 2:
                return None
            return filtered
        except Exception:
            return None
    
    def save_historical_data(self, df: pd.DataFrame, symbol: str, period: str, data_type: str = "stock") -> None:
        if df.empty:
            return
        file_path = self._get_file_path(symbol, period, data_type)
        try:
            new_df = df.copy()
            new_df['日期'] = pd.to_datetime(new_df['日期']).dt.strftime('%Y-%m-%d')
            if file_path.exists():
                existing_df = pd.read_parquet(file_path)
                existing_df['日期'] = pd.to_datetime(existing_df['日期']).dt.strftime('%Y-%m-%d')
                combined = pd.concat([existing_df, new_df], ignore_index=True)
                combined = combined.drop_duplicates(subset=['日期'], keep='last')
                combined = combined.sort_values('日期').reset_index(drop=True)
            else:
                combined = new_df.sort_values('日期').reset_index(drop=True)
            combined.to_parquet(file_path, index=False)
        except Exception:
            pass
    
    def get_cache_stats(self) -> dict:
        stats = {
            "memory_cache_keys": len(self._memory_cache),
            "cache_dir": str(self._cache_dir),
            "local_files": []
        }
        for f in self._cache_dir.glob("*.parquet"):
            stats["local_files"].append({
                "name": f.name,
                "size_kb": round(f.stat().st_size / 1024, 2),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
        return stats
    
    def clear_memory_cache(self) -> None:
        self._memory_cache.clear()
    
    def clear_local_cache(self, symbol: str = None) -> int:
        count = 0
        if symbol:
            for f in self._cache_dir.glob(f"*_{symbol}_*.parquet"):
                f.unlink()
                count += 1
        else:
            for f in self._cache_dir.glob("*.parquet"):
                f.unlink()
                count += 1
        return count


cache = CacheManager()


# ============== 多数据源支持 ==============

class DataSourceManager:
    """多数据源管理器，支持自动切换备份源"""
    
    def __init__(self):
        self.request_interval = 1.0
        self.last_request_time = 0
        self.failure_count = {}
        self.max_failures = 3
    
    def _wait_for_rate_limit(self):
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _record_failure(self, source: str):
        self.failure_count[source] = self.failure_count.get(source, 0) + 1
    
    def _record_success(self, source: str):
        self.failure_count[source] = 0
    
    def _is_source_healthy(self, source: str) -> bool:
        return self.failure_count.get(source, 0) < self.max_failures
    
    def get_realtime_quotes(self) -> pd.DataFrame:
        sources = [
            ("em", lambda: ak.stock_zh_a_spot_em()),
            ("sina", lambda: self._get_sina_realtime()),
            ("em_combined", lambda: self._get_combined_realtime()),
        ]
        last_error = None
        for source_name, fetch_func in sources:
            if not self._is_source_healthy(source_name):
                continue
            try:
                self._wait_for_rate_limit()
                df = fetch_func()
                if df is not None and not df.empty:
                    self._record_success(source_name)
                    return df
            except Exception as e:
                self._record_failure(source_name)
                last_error = e
                continue
        self.failure_count.clear()
        raise Exception(f"所有数据源都不可用: {last_error}")
    
    def _get_sina_realtime(self) -> pd.DataFrame:
        try:
            df = ak.stock_zh_a_spot()
            if df is not None and not df.empty:
                column_map = {
                    'symbol': '代码', 'code': '代码', 'name': '名称',
                    'trade': '最新价', 'pricechange': '涨跌额', 'changepercent': '涨跌幅',
                    'open': '今开', 'high': '最高', 'low': '最低',
                    'volume': '成交量', 'amount': '成交额', 'turnoverratio': '换手率',
                }
                df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
            return df
        except:
            return None
    
    def _get_combined_realtime(self) -> pd.DataFrame:
        try:
            dfs = []
            for func in [ak.stock_kc_a_spot_em, ak.stock_cy_a_spot_em, ak.stock_sh_a_spot_em, ak.stock_sz_a_spot_em]:
                try:
                    dfs.append(func())
                except:
                    pass
            if dfs:
                combined = pd.concat(dfs, ignore_index=True)
                if '代码' in combined.columns:
                    combined = combined.drop_duplicates(subset=['代码'], keep='first')
                return combined
            return None
        except:
            return None

    def get_stock_history(self, symbol: str, period: str, start_date: str, end_date: str, adjust: str = "qfq") -> pd.DataFrame:
        sources = [
            ("em", lambda: ak.stock_zh_a_hist(symbol=symbol, period=period, start_date=start_date, end_date=end_date, adjust=adjust)),
            ("tx", lambda: self._get_tencent_history(symbol, start_date, end_date, adjust)),
        ]
        last_error = None
        for source_name, fetch_func in sources:
            if not self._is_source_healthy(source_name):
                continue
            try:
                self._wait_for_rate_limit()
                df = fetch_func()
                if df is not None and not df.empty:
                    self._record_success(source_name)
                    return df
            except Exception as e:
                self._record_failure(source_name)
                last_error = e
                continue
        self.failure_count.clear()
        raise Exception(f"所有数据源都不可用: {last_error}")
    
    def _get_tencent_history(self, symbol: str, start_date: str, end_date: str, adjust: str) -> pd.DataFrame:
        try:
            df = ak.stock_zh_a_daily(symbol=symbol, adjust=adjust)
            if df is not None and not df.empty:
                df['date'] = pd.to_datetime(df['date'])
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
                column_map = {'date': '日期', 'open': '开盘', 'high': '最高', 'low': '最低', 'close': '收盘', 'volume': '成交量'}
                df = df.rename(columns=column_map)
                if '成交额' not in df.columns:
                    df['成交额'] = df['成交量'] * df['收盘']
                if '涨跌幅' not in df.columns:
                    df['涨跌幅'] = df['收盘'].pct_change() * 100
                if '换手率' not in df.columns:
                    df['换手率'] = 0
            return df
        except:
            return None
    
    def get_index_history(self, symbol: str, period: str, start_date: str, end_date: str) -> pd.DataFrame:
        sources = [
            ("em", lambda: ak.index_zh_a_hist(symbol=symbol, period=period, start_date=start_date, end_date=end_date)),
            ("csindex", lambda: self._get_csindex_history(symbol, start_date, end_date)),
        ]
        last_error = None
        for source_name, fetch_func in sources:
            if not self._is_source_healthy(source_name):
                continue
            try:
                self._wait_for_rate_limit()
                df = fetch_func()
                if df is not None and not df.empty:
                    self._record_success(source_name)
                    return df
            except Exception as e:
                self._record_failure(source_name)
                last_error = e
                continue
        self.failure_count.clear()
        raise Exception(f"所有数据源都不可用: {last_error}")
    
    def _get_csindex_history(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            df = ak.stock_zh_index_hist_csindex(symbol=symbol, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                column_map = {'日期': '日期', '开盘': '开盘', '最高': '最高', '最低': '最低', '收盘': '收盘', '涨跌幅': '涨跌幅', '成交量': '成交量', '成交金额': '成交额'}
                df = df.rename(columns=column_map)
                if '成交额' not in df.columns and '成交量' in df.columns:
                    df['成交额'] = df['成交量'] * df['收盘']
            return df
        except:
            return None


data_source = DataSourceManager()


# ============== 缓存包装函数 ==============

def get_realtime_quotes_cached() -> pd.DataFrame:
    cached = cache.get_realtime_quotes()
    if cached is not None:
        return cached
    df = data_source.get_realtime_quotes()
    cache.set_realtime_quotes(df)
    return df


def get_stock_history_cached(symbol: str, period: str, start_date: str, end_date: str, adjust: str = "qfq") -> pd.DataFrame:
    cached_df = cache.get_historical_data(symbol, period, start_date, end_date, "stock")
    if cached_df is not None and len(cached_df) > 0:
        return cached_df
    df = data_source.get_stock_history(symbol=symbol, period=period, start_date=start_date, end_date=end_date, adjust=adjust)
    if not df.empty:
        cache.save_historical_data(df, symbol, period, "stock")
    return df


def get_index_history_cached(symbol: str, period: str, start_date: str, end_date: str) -> pd.DataFrame:
    cached_df = cache.get_historical_data(symbol, period, start_date, end_date, "index")
    if cached_df is not None and len(cached_df) > 0:
        return cached_df
    df = data_source.get_index_history(symbol=symbol, period=period, start_date=start_date, end_date=end_date)
    if not df.empty:
        cache.save_historical_data(df, symbol, period, "index")
    return df


# ============== 技术指标计算函数 ==============

def calculate_bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: int = 2) -> pd.DataFrame:
    df = df.copy()
    df['SMA20'] = df['收盘'].rolling(window=window).mean()
    df['BB_std'] = df['收盘'].rolling(window=window).std()
    df['BB_upper'] = df['SMA20'] + (df['BB_std'] * num_std)
    df['BB_lower'] = df['SMA20'] - (df['BB_std'] * num_std)
    df['BBW'] = (df['BB_upper'] - df['BB_lower']) / df['SMA20']
    return df


def calculate_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    df = df.copy()
    delta = df['收盘'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    df.loc[loss == 0, 'RSI'] = 100
    return df


def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    df = df.copy()
    df['EMA12'] = df['收盘'].ewm(span=fast, adjust=False).mean()
    df['EMA26'] = df['收盘'].ewm(span=slow, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_signal'] = df['MACD'].ewm(span=signal, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    return df


def calculate_stochastic(df: pd.DataFrame, k_window: int = 14, d_window: int = 3) -> pd.DataFrame:
    df = df.copy()
    low_min = df['最低'].rolling(window=k_window).min()
    high_max = df['最高'].rolling(window=k_window).max()
    denominator = high_max - low_min
    df['Stoch_K'] = np.where(denominator != 0, 100 * (df['收盘'] - low_min) / denominator, 50)
    df['Stoch_D'] = df['Stoch_K'].rolling(window=d_window).mean()
    return df


def calculate_adx(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    df = df.copy()
    df['TR'] = np.maximum(df['最高'] - df['最低'], np.maximum(abs(df['最高'] - df['收盘'].shift(1)), abs(df['最低'] - df['收盘'].shift(1))))
    df['+DM'] = np.where((df['最高'] - df['最高'].shift(1)) > (df['最低'].shift(1) - df['最低']), np.maximum(df['最高'] - df['最高'].shift(1), 0), 0)
    df['-DM'] = np.where((df['最低'].shift(1) - df['最低']) > (df['最高'] - df['最高'].shift(1)), np.maximum(df['最低'].shift(1) - df['最低'], 0), 0)
    df['TR_smooth'] = df['TR'].rolling(window=window).sum()
    df['+DI'] = 100 * (df['+DM'].rolling(window=window).sum() / df['TR_smooth'].replace(0, np.nan))
    df['-DI'] = 100 * (df['-DM'].rolling(window=window).sum() / df['TR_smooth'].replace(0, np.nan))
    di_sum = df['+DI'] + df['-DI']
    df['DX'] = np.where(di_sum != 0, 100 * abs(df['+DI'] - df['-DI']) / di_sum, 0)
    df['ADX'] = df['DX'].rolling(window=window).mean()
    return df


def get_bb_signal(price: float, upper: float, lower: float, middle: float) -> tuple:
    if pd.isna(upper) or pd.isna(lower):
        return 0, "N/A"
    if price > upper:
        return -2, "SELL (超买)"
    elif price < lower:
        return 2, "BUY (超卖)"
    elif price > middle:
        return 1, "NEUTRAL (偏多)"
    else:
        return -1, "NEUTRAL (偏空)"


def get_comprehensive_score(latest: pd.Series, prev: pd.Series) -> tuple:
    score = 0
    signals = []
    
    if pd.isna(latest['RSI']):
        signals.append("RSI数据不足")
    elif latest['RSI'] < 30:
        score += 2
        signals.append("RSI超卖(+2)")
    elif latest['RSI'] > 70:
        score -= 2
        signals.append("RSI超买(-2)")
    elif latest['RSI'] < 45:
        score -= 1
        signals.append("RSI偏弱(-1)")
    elif latest['RSI'] > 55:
        score += 1
        signals.append("RSI偏强(+1)")
    
    if pd.isna(latest['MACD']) or pd.isna(latest['MACD_signal']):
        signals.append("MACD数据不足")
    elif latest['MACD'] > latest['MACD_signal'] and latest['MACD_hist'] > prev['MACD_hist']:
        score += 2
        signals.append("MACD金叉向上(+2)")
    elif latest['MACD'] > latest['MACD_signal']:
        score += 1
        signals.append("MACD金叉(+1)")
    elif latest['MACD'] < latest['MACD_signal'] and latest['MACD_hist'] < prev['MACD_hist']:
        score -= 2
        signals.append("MACD死叉向下(-2)")
    else:
        score -= 1
        signals.append("MACD死叉(-1)")
    
    bb_rating, bb_signal = get_bb_signal(latest['收盘'], latest['BB_upper'], latest['BB_lower'], latest['SMA20'])
    score += bb_rating
    signals.append(f"布林带{bb_signal}({bb_rating:+d})")
    
    ema200 = latest.get('EMA200', np.nan)
    if pd.notna(latest['EMA50']) and pd.notna(ema200):
        if latest['收盘'] > latest['EMA50'] > ema200:
            score += 2
            signals.append("多头排列(+2)")
        elif latest['收盘'] < latest['EMA50']:
            score -= 1
            signals.append("价格<EMA50(-1)")
    elif pd.notna(latest['EMA50']) and latest['收盘'] < latest['EMA50']:
        score -= 1
        signals.append("价格<EMA50(-1)")
    
    if pd.isna(latest['Stoch_K']):
        signals.append("KDJ数据不足")
    elif latest['Stoch_K'] < 20:
        score += 1
        signals.append("KD超卖(+1)")
    elif latest['Stoch_K'] > 80:
        score -= 1
        signals.append("KD超买(-1)")
    
    if score >= 4:
        overall = "强烈看多"
    elif score >= 2:
        overall = "看多"
    elif score >= -1:
        overall = "中性"
    elif score >= -3:
        overall = "看空"
    else:
        overall = "强烈看空"
    
    return score, signals, overall


# ============== 分析函数 ==============

def analyze_stock(symbol: str, period: str = "daily", days: int = 365) -> dict:
    """完整股票技术分析"""
    if not symbol or not symbol.isdigit() or len(symbol) != 6:
        return {"error": f"无效的股票代码格式: {symbol}，必须是6位数字"}
    
    days = max(30, min(days, 3650))
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    
    try:
        df = get_stock_history_cached(symbol=symbol, period=period, start_date=start_date, end_date=end_date, adjust="qfq")
    except Exception as e:
        return {"error": f"获取 {symbol} 数据失败: {str(e)}"}
    
    if df.empty:
        return {"error": f"未找到 {symbol} 的数据"}
    
    min_required = 30
    if len(df) < min_required:
        return {"error": f"{symbol} 数据不足: 仅有 {len(df)} 条记录，至少需要 {min_required} 条"}
    
    df = calculate_bollinger_bands(df)
    df = calculate_rsi(df)
    df = calculate_macd(df)
    df = calculate_stochastic(df)
    df = calculate_adx(df)
    df['EMA50'] = df['收盘'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['收盘'].ewm(span=200, adjust=False).mean()
    
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    try:
        stock_info = ak.stock_individual_info_em(symbol=symbol)
        stock_name = stock_info[stock_info['item'] == '股票简称']['value'].values[0]
    except:
        stock_name = symbol
    
    bb_rating, bb_signal = get_bb_signal(latest['收盘'], latest['BB_upper'], latest['BB_lower'], latest['SMA20'])
    score, signals, overall = get_comprehensive_score(latest, prev)
    
    return {
        "symbol": symbol,
        "name": stock_name,
        "period": period,
        "timestamp": datetime.now().isoformat(),
        "price_data": {
            "current_price": round(float(latest['收盘']), 2),
            "open": round(float(latest['开盘']), 2),
            "high": round(float(latest['最高']), 2),
            "low": round(float(latest['最低']), 2),
            "change_percent": round(float(latest['涨跌幅']), 2),
            "volume": int(latest['成交量']),
            "amount": float(latest['成交额']),
            "turnover": round(float(latest['换手率']), 2)
        },
        "bollinger_analysis": {
            "rating": bb_rating,
            "signal": bb_signal,
            "bbw": round(float(latest['BBW']) * 100, 2),
            "bb_upper": round(float(latest['BB_upper']), 2),
            "bb_middle": round(float(latest['SMA20']), 2),
            "bb_lower": round(float(latest['BB_lower']), 2)
        },
        "technical_indicators": {
            "rsi": round(float(latest['RSI']), 2),
            "rsi_signal": "超买" if latest['RSI'] > 70 else "超卖" if latest['RSI'] < 30 else "中性",
            "sma20": round(float(latest['SMA20']), 2),
            "ema50": round(float(latest['EMA50']), 2),
            "ema200": round(float(latest['EMA200']), 2),
            "macd": round(float(latest['MACD']), 4),
            "macd_signal": round(float(latest['MACD_signal']), 4),
            "macd_hist": round(float(latest['MACD_hist']), 4),
            "macd_cross": "金叉" if latest['MACD'] > latest['MACD_signal'] else "死叉",
            "adx": round(float(latest['ADX']), 2),
            "trend_strength": "强趋势" if latest['ADX'] > 25 else "中等" if latest['ADX'] > 20 else "弱趋势",
            "stoch_k": round(float(latest['Stoch_K']), 2),
            "stoch_d": round(float(latest['Stoch_D']), 2)
        },
        "key_levels": {
            "resistance_1": round(float(latest['SMA20']), 2),
            "resistance_2": round(float(latest['EMA50']), 2),
            "resistance_3": round(float(latest['BB_upper']), 2),
            "support_1": round(float(latest['BB_lower']), 2),
            "support_2": round(float(latest['EMA200']), 2)
        },
        "comprehensive_analysis": {
            "score": score,
            "signals": signals,
            "overall": overall
        }
    }


def get_stock_quote(symbol: str) -> dict:
    """获取实时行情"""
    try:
        df = get_realtime_quotes_cached()
        stock = df[df['代码'] == symbol]
        if stock.empty:
            return {"error": f"未找到股票 {symbol}"}
        row = stock.iloc[0]
        return {
            "symbol": symbol,
            "name": row['名称'],
            "price": float(row['最新价']),
            "change": float(row['涨跌额']),
            "change_percent": float(row['涨跌幅']),
            "open": float(row['今开']),
            "high": float(row['最高']),
            "low": float(row['最低']),
            "volume": int(row['成交量']),
            "amount": float(row['成交额']),
            "turnover": float(row['换手率']),
            "pe_ratio": float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else None,
            "pb_ratio": float(row['市净率']) if pd.notna(row['市净率']) else None,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


def get_top_gainers(limit: int = 20) -> dict:
    """获取涨幅榜"""
    df = get_realtime_quotes_cached()
    df = df.sort_values('涨跌幅', ascending=False).head(limit)
    stocks = []
    for _, row in df.iterrows():
        stocks.append({
            "symbol": normalize_symbol(row['代码']),
            "name": row['名称'],
            "price": float(row['最新价']),
            "change_percent": float(row['涨跌幅']),
            "volume": int(row['成交量']),
            "amount": float(row['成交额'])
        })
    return {"type": "top_gainers", "count": len(stocks), "timestamp": datetime.now().isoformat(), "stocks": stocks}


def get_top_losers(limit: int = 20) -> dict:
    """获取跌幅榜"""
    df = get_realtime_quotes_cached()
    df = df.sort_values('涨跌幅', ascending=True).head(limit)
    stocks = []
    for _, row in df.iterrows():
        stocks.append({
            "symbol": normalize_symbol(row['代码']),
            "name": row['名称'],
            "price": float(row['最新价']),
            "change_percent": float(row['涨跌幅']),
            "volume": int(row['成交量']),
            "amount": float(row['成交额'])
        })
    return {"type": "top_losers", "count": len(stocks), "timestamp": datetime.now().isoformat(), "stocks": stocks}


def normalize_symbol(symbol: str) -> str:
    """标准化股票代码为6位数字格式"""
    if not symbol:
        return symbol
    # 移除 sh/sz/bj 前缀
    symbol = str(symbol).lower()
    for prefix in ['sh', 'sz', 'bj']:
        if symbol.startswith(prefix):
            symbol = symbol[len(prefix):]
            break
    # 移除 .sh/.sz/.bj 后缀
    for suffix in ['.sh', '.sz', '.bj']:
        if symbol.endswith(suffix):
            symbol = symbol[:-len(suffix)]
            break
    return symbol


def search_stock(keyword: str) -> dict:
    """搜索股票"""
    df = get_realtime_quotes_cached()
    matches = df[df['名称'].str.contains(keyword, na=False) | df['代码'].str.contains(keyword, na=False)].head(20)
    stocks = []
    for _, row in matches.iterrows():
        stocks.append({
            "symbol": normalize_symbol(row['代码']),
            "name": row['名称'],
            "price": float(row['最新价']),
            "change_percent": float(row['涨跌幅'])
        })
    return {"keyword": keyword, "count": len(stocks), "results": stocks}


def analyze_index(symbol: str, period: str = "daily") -> dict:
    """分析指数"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    
    try:
        df = get_index_history_cached(symbol=symbol, period=period, start_date=start_date, end_date=end_date)
    except Exception as e:
        return {"error": f"获取指数 {symbol} 数据失败: {str(e)}"}
    
    if df.empty:
        return {"error": f"未找到指数 {symbol} 的数据"}
    
    df = calculate_bollinger_bands(df)
    df = calculate_rsi(df)
    df = calculate_macd(df)
    
    latest = df.iloc[-1]
    
    index_names = {
        "000001": "上证指数", "399001": "深证成指", "399006": "创业板指",
        "000300": "沪深300", "000016": "上证50", "000905": "中证500"
    }
    
    return {
        "symbol": symbol,
        "name": index_names.get(symbol, symbol),
        "period": period,
        "price_data": {
            "current": round(float(latest['收盘']), 2),
            "open": round(float(latest['开盘']), 2),
            "high": round(float(latest['最高']), 2),
            "low": round(float(latest['最低']), 2),
            "change_percent": round(float(latest['涨跌幅']), 2),
            "volume": int(latest['成交量']),
            "amount": float(latest['成交额'])
        },
        "technical_indicators": {
            "rsi": round(float(latest['RSI']), 2),
            "sma20": round(float(latest['SMA20']), 2),
            "bb_upper": round(float(latest['BB_upper']), 2),
            "bb_lower": round(float(latest['BB_lower']), 2),
            "macd": round(float(latest['MACD']), 4),
            "macd_signal": round(float(latest['MACD_signal']), 4)
        },
        "timestamp": datetime.now().isoformat()
    }


def get_sector_flow(limit: int = 20) -> dict:
    """获取行业资金流向"""
    try:
        df = ak.stock_sector_fund_flow_rank(indicator="今日")
        df = df.head(limit)
        sectors = []
        for _, row in df.iterrows():
            sectors.append({
                "name": row['名称'],
                "change_percent": float(row['今日涨跌幅']) if pd.notna(row['今日涨跌幅']) else 0,
                "main_net_inflow": float(row['今日主力净流入-净额']) if pd.notna(row['今日主力净流入-净额']) else 0,
                "main_net_inflow_percent": float(row['今日主力净流入-净占比']) if pd.notna(row['今日主力净流入-净占比']) else 0
            })
        return {"type": "sector_flow", "count": len(sectors), "timestamp": datetime.now().isoformat(), "sectors": sectors}
    except Exception as e:
        return {"error": str(e)}


def get_north_flow() -> dict:
    """获取北向资金流向"""
    try:
        df = ak.stock_hsgt_hist_em(symbol="北向资金")
        latest = df.iloc[-1] if not df.empty else None
        if latest is None:
            return {"error": "无北向资金数据"}
        
        def safe_get(series, key, default=0):
            if key in series.index:
                val = series[key]
                return float(val) if pd.notna(val) else default
            return default
        
        return {
            "type": "north_flow",
            "date": str(latest['日期']),
            "net_inflow": safe_get(latest, '当日成交净买额'),
            "buy_amount": safe_get(latest, '买入成交额'),
            "sell_amount": safe_get(latest, '卖出成交额'),
            "accumulated": safe_get(latest, '历史累计净买额'),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}


def get_cache_stats_cmd() -> dict:
    """获取缓存统计信息"""
    stats = cache.get_cache_stats()
    return {
        "type": "cache_stats",
        "memory_cache_keys": stats["memory_cache_keys"],
        "cache_directory": stats["cache_dir"],
        "local_cache_files": stats["local_files"],
        "total_files": len(stats["local_files"]),
        "total_size_kb": round(sum(f["size_kb"] for f in stats["local_files"]), 2),
        "timestamp": datetime.now().isoformat()
    }


def clear_cache_cmd(cache_type: str = "memory", symbol: str = None) -> dict:
    """清空缓存"""
    result = {"type": "clear_cache", "cache_type": cache_type, "timestamp": datetime.now().isoformat()}
    if cache_type in ("memory", "all"):
        cache.clear_memory_cache()
        result["memory_cleared"] = True
    if cache_type in ("local", "all"):
        deleted_count = cache.clear_local_cache(symbol)
        result["local_files_deleted"] = deleted_count
        if symbol:
            result["symbol"] = symbol
    return result


# ============== 主入口 ==============

def main():
    parser = argparse.ArgumentParser(description="A股技术分析工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # stock_analysis
    p_analysis = subparsers.add_parser("stock_analysis", help="股票完整技术分析")
    p_analysis.add_argument("--symbol", required=True, help="股票代码 (6位数字)")
    p_analysis.add_argument("--period", default="daily", choices=["daily", "weekly", "monthly"], help="时间周期")
    p_analysis.add_argument("--days", type=int, default=365, help="历史数据天数")
    
    # stock_quote
    p_quote = subparsers.add_parser("stock_quote", help="实时行情快照")
    p_quote.add_argument("--symbol", required=True, help="股票代码")
    
    # top_gainers
    p_gainers = subparsers.add_parser("top_gainers", help="涨幅榜")
    p_gainers.add_argument("--limit", type=int, default=20, help="返回数量")
    
    # top_losers
    p_losers = subparsers.add_parser("top_losers", help="跌幅榜")
    p_losers.add_argument("--limit", type=int, default=20, help="返回数量")
    
    # stock_search
    p_search = subparsers.add_parser("stock_search", help="搜索股票")
    p_search.add_argument("--keyword", required=True, help="搜索关键词")
    
    # index_analysis
    p_index = subparsers.add_parser("index_analysis", help="指数分析")
    p_index.add_argument("--symbol", required=True, help="指数代码")
    p_index.add_argument("--period", default="daily", choices=["daily", "weekly", "monthly"], help="时间周期")
    
    # sector_flow
    p_sector = subparsers.add_parser("sector_flow", help="行业资金流向")
    p_sector.add_argument("--limit", type=int, default=20, help="返回数量")
    
    # north_flow
    subparsers.add_parser("north_flow", help="北向资金")
    
    # cache_stats
    subparsers.add_parser("cache_stats", help="缓存统计")
    
    # clear_cache
    p_clear = subparsers.add_parser("clear_cache", help="清空缓存")
    p_clear.add_argument("--cache_type", default="memory", choices=["memory", "local", "all"], help="缓存类型")
    p_clear.add_argument("--symbol", help="指定股票代码")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    result = None
    
    if args.command == "stock_analysis":
        result = analyze_stock(args.symbol, args.period, args.days)
    elif args.command == "stock_quote":
        result = get_stock_quote(args.symbol)
    elif args.command == "top_gainers":
        result = get_top_gainers(args.limit)
    elif args.command == "top_losers":
        result = get_top_losers(args.limit)
    elif args.command == "stock_search":
        result = search_stock(args.keyword)
    elif args.command == "index_analysis":
        result = analyze_index(args.symbol, args.period)
    elif args.command == "sector_flow":
        result = get_sector_flow(args.limit)
    elif args.command == "north_flow":
        result = get_north_flow()
    elif args.command == "cache_stats":
        result = get_cache_stats_cmd()
    elif args.command == "clear_cache":
        result = clear_cache_cmd(args.cache_type, args.symbol)
    
    if result:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
