#!/usr/bin/env python3
"""
A股技术分析技能测试
"""

import sys
from pathlib import Path

# 添加脚本路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from a_share_analyzer import (
    analyze_stock,
    get_stock_quote,
    get_top_gainers,
    get_top_losers,
    search_stock,
    analyze_index,
    get_sector_flow,
    get_north_flow,
    get_cache_stats_cmd,
    clear_cache_cmd
)


def test_stock_analysis():
    """测试股票技术分析"""
    print("\n✓ 测试 stock_analysis (600519 茅台)...")
    try:
        result = analyze_stock("600519", "daily", 180)
        if "error" in result:
            print(f"  ✗ 错误: {result['error']}")
            return False
        print(f"  ✓ 股票: {result['name']}")
        print(f"  ✓ 价格: {result['price_data']['current_price']}")
        print(f"  ✓ RSI: {result['technical_indicators']['rsi']}")
        print(f"  ✓ 综合评分: {result['comprehensive_analysis']['score']} ({result['comprehensive_analysis']['overall']})")
        return True
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False


def test_stock_quote():
    """测试实时行情"""
    print("\n✓ 测试 stock_quote (000001 平安银行)...")
    try:
        result = get_stock_quote("000001")
        if "error" in result:
            print(f"  ✗ 错误: {result['error']}")
            return False
        print(f"  ✓ 股票: {result['name']}")
        print(f"  ✓ 价格: {result['price']}")
        print(f"  ✓ 涨跌幅: {result['change_percent']}%")
        return True
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False


def test_top_gainers():
    """测试涨幅榜"""
    print("\n✓ 测试 top_gainers...")
    try:
        result = get_top_gainers(5)
        if "error" in result:
            print(f"  ✗ 错误: {result['error']}")
            return False
        print(f"  ✓ 获取 {result['count']} 只股票")
        if result['stocks']:
            top = result['stocks'][0]
            print(f"  ✓ 涨幅第一: {top['name']} ({top['symbol']}) +{top['change_percent']}%")
        return True
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False


def test_search_stock():
    """测试股票搜索"""
    print("\n✓ 测试 stock_search (茅台)...")
    try:
        result = search_stock("茅台")
        if "error" in result:
            print(f"  ✗ 错误: {result['error']}")
            return False
        print(f"  ✓ 找到 {result['count']} 个结果")
        if result['results']:
            first = result['results'][0]
            print(f"  ✓ 第一个: {first['name']} ({first['symbol']})")
        return True
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False


def test_index_analysis():
    """测试指数分析"""
    print("\n✓ 测试 index_analysis (000001 上证指数)...")
    try:
        result = analyze_index("000001", "daily")
        if "error" in result:
            print(f"  ✗ 错误: {result['error']}")
            return False
        print(f"  ✓ 指数: {result['name']}")
        print(f"  ✓ 点位: {result['price_data']['current']}")
        print(f"  ✓ RSI: {result['technical_indicators']['rsi']}")
        return True
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False


def test_sector_flow():
    """测试行业资金流向"""
    print("\n✓ 测试 sector_flow...")
    try:
        result = get_sector_flow(5)
        if "error" in result:
            print(f"  ✗ 错误: {result['error']}")
            return False
        print(f"  ✓ 获取 {result['count']} 个行业")
        if result['sectors']:
            top = result['sectors'][0]
            print(f"  ✓ 第一: {top['name']} 涨跌幅: {top['change_percent']}%")
        return True
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False


def test_north_flow():
    """测试北向资金"""
    print("\n✓ 测试 north_flow...")
    try:
        result = get_north_flow()
        if "error" in result:
            print(f"  ✗ 错误: {result['error']}")
            return False
        print(f"  ✓ 日期: {result['date']}")
        print(f"  ✓ 净流入: {result['net_inflow']} 亿")
        return True
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False


def test_cache_stats():
    """测试缓存统计"""
    print("\n✓ 测试 cache_stats...")
    try:
        result = get_cache_stats_cmd()
        print(f"  ✓ 内存缓存: {result['memory_cache_keys']} 个键")
        print(f"  ✓ 本地文件: {result['total_files']} 个")
        print(f"  ✓ 总大小: {result['total_size_kb']} KB")
        return True
    except Exception as e:
        print(f"  ✗ 异常: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("A股技术分析技能 - 集成测试")
    print("=" * 60)

    tests = [
        ("股票搜索", test_search_stock),
        ("实时行情", test_stock_quote),
        ("涨幅榜", test_top_gainers),
        ("股票技术分析", test_stock_analysis),
        ("指数分析", test_index_analysis),
        ("行业资金流向", test_sector_flow),
        ("北向资金", test_north_flow),
        ("缓存统计", test_cache_stats),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"  ✗ 测试异常: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status}: {name}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print(f"\n总计: {passed_count}/{total_count} 通过")

    return passed_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
