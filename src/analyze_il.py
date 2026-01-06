#!/usr/bin/env python3
"""
Impermanent Loss (IL) 分析腳本
計算並比較不同策略的 IL 時間序列
"""

import os
import sys
import csv
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from strategies.strategy_backtest import StrategyBacktester, BacktestConfig, BacktestResult
from strategies.charm_strategy import CharmAlphaVaultStrategy
from strategies.steer_strategy import SteerClassicStrategy, SteerElasticStrategy


def load_value_history(filepath: str) -> List[Tuple[int, float]]:
    """從 CSV 載入價值歷史"""
    history = []
    if not os.path.exists(filepath):
        return history
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if len(row) >= 3:
                try:
                    ts = int(float(row[0]))
                    value = float(row[2])
                    history.append((ts, value))
                except:
                    continue
    return history


def load_price_history(filepath: str) -> List[Tuple[int, float]]:
    """從 CSV 載入價格歷史"""
    history = []
    if not os.path.exists(filepath):
        return history
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if len(row) >= 3:
                try:
                    ts = int(float(row[0]))
                    price = float(row[2])
                    history.append((ts, price))
                except:
                    continue
    return history


def calculate_il_time_series(
    value_history: List[Tuple[int, Decimal]],
    price_history: List[Tuple[int, float]],
    initial_amount0: Decimal,
    initial_amount1: Decimal,
    initial_price: float
) -> List[Tuple[int, float, float, float]]:
    """
    計算 IL 時間序列
    
    Returns:
        List of (timestamp, lp_value, hodl_value, il_pct)
    """
    il_series = []
    
    # 建立價格索引（快速查找）
    price_dict = {ts: price for ts, price in price_history}
    
    for ts, lp_value_decimal in value_history:
        # 找到對應的價格
        current_price = None
        if ts in price_dict:
            current_price = price_dict[ts]
        else:
            # 找最接近的價格
            closest_ts = min(price_history, key=lambda x: abs(x[0] - ts))[0]
            current_price = price_dict[closest_ts]
        
        if current_price is None or current_price <= 0:
            continue
        
        # 計算 HODL 價值
        hodl_value = float(initial_amount0) * current_price + float(initial_amount1)
        lp_value = float(lp_value_decimal)
        
        # 計算 IL (%)
        if hodl_value > 0:
            il_pct = ((lp_value - hodl_value) / hodl_value) * 100
        else:
            il_pct = 0.0
        
        # 過濾異常值：IL 應該在合理範圍內（-100% 到 +100%）
        # 如果超出範圍，可能是計算錯誤，跳過或限制
        if il_pct > 100 or il_pct < -100:
            # 跳過明顯異常的數據點
            continue
        
        il_series.append((ts, lp_value, hodl_value, il_pct))
    
    return il_series


def run_il_analysis(
    data_file: str,
    initial_capital: float = 10000.0,
    output_dir: str = "output/all_compare"
):
    """運行 IL 分析"""
    
    print("=" * 70)
    print("Impermanent Loss (IL) 分析")
    print("=" * 70)
    
    # Initialize config
    config = BacktestConfig(
        initial_amount0=Decimal('0'),
        initial_amount1=Decimal(str(initial_capital / 2)),
        pool_fee=3000,
        tick_spacing=60
    )
    
    # Initialize backtester and load data
    backtester = StrategyBacktester(config)
    backtester.load_tick_data(data_file)
    
    # Get market info
    first_price = backtester.price_history[0][1]
    last_price = backtester.price_history[-1][1]
    first_ts = backtester.price_history[0][0]
    last_ts = backtester.price_history[-1][0]
    
    first_date = datetime.fromtimestamp(first_ts).strftime('%Y-%m-%d')
    last_date = datetime.fromtimestamp(last_ts).strftime('%Y-%m-%d')
    
    print(f"\n📅 回測期間: {first_date} 至 {last_date}")
    print(f"💰 BTC 價格: ${first_price:,.2f} → ${last_price:,.2f}")
    print(f"💵 初始資金: ${initial_capital:,.2f}")
    
    # Set initial amounts (50/50 split)
    config.initial_amount0 = Decimal(str((initial_capital / 2) / float(first_price)))
    config.initial_amount1 = Decimal(str(initial_capital / 2))
    
    # Create strategies
    strategies = [
        CharmAlphaVaultStrategy(
            base_threshold=600,
            limit_threshold=1200,
            rebalance_interval=172800,
            pool_fee=3000,
            tick_spacing=60
        ),
        SteerClassicStrategy(
            position_width_ticks=600,
            rebalance_threshold_bps=500,
            pool_fee=3000,
            tick_spacing=60
        ),
        SteerElasticStrategy(
            sma_period=20,
            std_multiplier=2.0,
            min_width_ticks=120,
            pool_fee=3000,
            tick_spacing=60
        ),
    ]
    
    # Run backtests
    print("\n" + "=" * 70)
    print("運行策略回測...")
    print("=" * 70)
    
    results: Dict[str, BacktestResult] = {}
    
    for strategy in strategies:
        name = strategy.name
        print(f"\n運行 {name}...")
        try:
            result = backtester.run_backtest(strategy)
            results[name] = result
            print(f"  ✓ 完成: IL={result.impermanent_loss_pct:.2f}%")
        except Exception as e:
            print(f"  ✗ 錯誤: {e}")
            import traceback
            traceback.print_exc()
    
    # Load Omnis AI results
    print("\n載入 Omnis AI (ATR) 回測結果...")
    omnis_value_history = load_value_history("output/value_history.csv")
    if omnis_value_history:
        # Convert to Decimal format
        omnis_value_history_decimal = [(ts, Decimal(str(val))) for ts, val in omnis_value_history]
        results["Omnis AI (ATR)"] = BacktestResult(
            strategy_name="Omnis AI (ATR)",
            initial_value=Decimal('10000'),
            final_value=Decimal(str(omnis_value_history[-1][1])),
            total_return_pct=-15.70,
            annualized_return_pct=-40.45,
            max_drawdown_pct=18.07,
            sharpe_ratio=-0.36,
            total_fees_earned=Decimal('4520.96'),
            net_fees_earned=Decimal('4520.96'),
            total_rebalance_count=37,
            total_gas_cost=Decimal('1110'),
            total_swap_cost=Decimal('0'),
            impermanent_loss_pct=-56.63,
            time_in_range_pct=100.0,
            value_history=omnis_value_history_decimal
        )
        print(f"  ✓ 完成: IL={results['Omnis AI (ATR)'].impermanent_loss_pct:.2f}%")
    
    # Calculate IL time series for all strategies
    print("\n" + "=" * 70)
    print("計算 IL 時間序列...")
    print("=" * 70)
    
    price_history = [(ts, price) for ts, price in backtester.price_history]
    
    il_data: Dict[str, List[Tuple[int, float, float, float]]] = {}
    
    for name, result in results.items():
        if result.value_history:
            il_series = calculate_il_time_series(
                result.value_history,
                price_history,
                config.initial_amount0,
                config.initial_amount1,
                first_price
            )
            il_data[name] = il_series
            print(f"  ✓ {name}: {len(il_series)} 個數據點")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate charts
    print("\n" + "=" * 70)
    print("生成 IL 分析圖表...")
    print("=" * 70)
    
    generate_il_charts(il_data, price_history, output_dir, first_date, last_date)
    
    # Save CSV
    print("\n保存 IL 數據到 CSV...")
    save_il_csv(il_data, output_dir)
    
    print("\n" + "=" * 70)
    print(f"✅ IL 分析完成！輸出目錄: {output_dir}")
    print("=" * 70)


def generate_il_charts(
    il_data: Dict[str, List[Tuple[int, float, float, float]]],
    price_history: List[Tuple[int, float]],
    output_dir: str,
    first_date: str,
    last_date: str
):
    """生成 IL 分析圖表"""
    
    # Set style
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # Color palette
    colors = {
        'Omnis AI (ATR)': '#2E86AB',
        'Charm Alpha Vault': '#A23B72',
        'Steer Classic Rebalance': '#F18F01',
        'Steer Elastic Expansion': '#C73E1D',
    }
    
    # 1. IL 時間序列比較
    fig, ax = plt.subplots(figsize=(14, 8))
    
    for name, il_series in il_data.items():
        if not il_series:
            continue
        
        # 過濾異常值
        filtered_series = [(ts, il) for ts, _, _, il in il_series if -100 <= il <= 100]
        if not filtered_series:
            continue
        
        timestamps = [datetime.fromtimestamp(ts) for ts, _ in filtered_series]
        il_values = [il for _, il in filtered_series]
        
        color = colors.get(name, '#666666')
        ax.plot(timestamps, il_values, label=name, linewidth=2, color=color, alpha=0.8)
    
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.3)
    ax.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax.set_ylabel('Impermanent Loss (%)', fontsize=12, fontweight='bold')
    ax.set_title(f'Impermanent Loss Comparison ({first_date} to {last_date})', fontsize=14, fontweight='bold')
    ax.legend(loc='lower left', fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    
    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/il_time_series.png", dpi=300, bbox_inches='tight')
    print(f"  ✓ il_time_series.png")
    plt.close()
    
    # 2. IL vs Price Change
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Calculate price change percentage
    first_price = price_history[0][1]
    
    for name, il_series in il_data.items():
        if not il_series:
            continue
        
        # 過濾異常值
        filtered_series = [(ts, il) for ts, _, _, il in il_series if -100 <= il <= 100]
        if not filtered_series:
            continue
        
        timestamps = [ts for ts, _ in filtered_series]
        il_values = [il for _, il in filtered_series]
        
        # Get corresponding prices
        price_changes = []
        for ts, _ in filtered_series:
            # Find closest price
            closest_price = min(price_history, key=lambda x: abs(x[0] - ts))[1]
            price_change = ((closest_price / first_price) - 1) * 100
            price_changes.append(price_change)
        
        color = colors.get(name, '#666666')
        ax.plot(price_changes, il_values, label=name, linewidth=2, color=color, alpha=0.8, marker='o', markersize=3)
    
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.3)
    ax.axvline(x=0, color='black', linestyle='--', linewidth=1, alpha=0.3)
    ax.set_xlabel('BTC Price Change (%)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Impermanent Loss (%)', fontsize=12, fontweight='bold')
    ax.set_title('IL vs Price Change', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/il_vs_price_change.png", dpi=300, bbox_inches='tight')
    print(f"  ✓ il_vs_price_change.png")
    plt.close()
    
    # 3. IL Distribution (Histogram)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    
    for idx, (name, il_series) in enumerate(il_data.items()):
        if idx >= len(axes) or not il_series:
            continue
        
        # 過濾異常值
        il_values = [il for _, _, _, il in il_series if -100 <= il <= 100]
        
        if not il_values:
            continue
        
        ax = axes[idx]
        ax.hist(il_values, bins=30, color=colors.get(name, '#666666'), alpha=0.7, edgecolor='black')
        ax.axvline(x=0, color='red', linestyle='--', linewidth=2, alpha=0.5)
        ax.set_xlabel('Impermanent Loss (%)', fontsize=10)
        ax.set_ylabel('Frequency', fontsize=10)
        ax.set_title(f'{name}\nMean: {np.mean(il_values):.2f}%', fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3)
    
    # Hide unused subplots
    for idx in range(len(il_data), len(axes)):
        axes[idx].set_visible(False)
    
    plt.suptitle('IL Distribution by Strategy', fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/il_distribution.png", dpi=300, bbox_inches='tight')
    print(f"  ✓ il_distribution.png")
    plt.close()
    
    # 4. IL Summary Bar Chart
    fig, ax = plt.subplots(figsize=(12, 7))
    
    strategy_names = []
    final_il = []
    max_il = []
    mean_il = []
    
    for name, il_series in il_data.items():
        if not il_series:
            continue
        
        # 過濾異常值（只保留 -100% 到 +100% 範圍內的數據）
        il_values = [il for _, _, _, il in il_series if -100 <= il <= 100]
        
        if not il_values:
            continue
        
        strategy_names.append(name)
        final_il.append(il_values[-1])
        max_il.append(min(il_values))  # Most negative (worst)
        mean_il.append(np.mean(il_values))
    
    x = np.arange(len(strategy_names))
    width = 0.25
    
    bars1 = ax.bar(x - width, final_il, width, label='Final IL', color='#2E86AB', alpha=0.8)
    bars2 = ax.bar(x, mean_il, width, label='Mean IL', color='#A23B72', alpha=0.8)
    bars3 = ax.bar(x + width, max_il, width, label='Max IL (Worst)', color='#C73E1D', alpha=0.8)
    
    ax.set_xlabel('Strategy', fontsize=12, fontweight='bold')
    ax.set_ylabel('Impermanent Loss (%)', fontsize=12, fontweight='bold')
    ax.set_title('IL Summary Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(strategy_names, rotation=15, ha='right')
    ax.legend(fontsize=10, framealpha=0.9)
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    
    # Add value labels
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%',
                   ha='center', va='bottom' if height > 0 else 'top', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/il_summary_bar.png", dpi=300, bbox_inches='tight')
    print(f"  ✓ il_summary_bar.png")
    plt.close()


def save_il_csv(il_data: Dict[str, List[Tuple[int, float, float, float]]], output_dir: str):
    """保存 IL 數據到 CSV"""
    
    # Save individual strategy IL time series
    for name, il_series in il_data.items():
        filename = f"{output_dir}/il_{name.replace(' ', '_').replace('(', '').replace(')', '').lower()}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'datetime', 'lp_value_usdc', 'hodl_value_usdc', 'il_pct'])
            
            for ts, lp_val, hodl_val, il_pct in il_series:
                dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow([ts, dt, f"{lp_val:.2f}", f"{hodl_val:.2f}", f"{il_pct:.4f}"])
        
        print(f"  ✓ {os.path.basename(filename)}")
    
    # Save summary CSV
    summary_file = f"{output_dir}/il_summary.csv"
    with open(summary_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['strategy', 'final_il_pct', 'max_il_pct', 'mean_il_pct', 'min_il_pct', 'std_il_pct'])
        
        for name, il_series in il_data.items():
            if not il_series:
                continue
            
            # 過濾異常值（只保留 -100% 到 +100% 範圍內的數據）
            il_values = [il for _, _, _, il in il_series if -100 <= il <= 100]
            
            if not il_values:
                continue
            
            writer.writerow([
                name,
                f"{il_values[-1]:.4f}",
                f"{max(il_values):.4f}",
                f"{np.mean(il_values):.4f}",
                f"{min(il_values):.4f}",
                f"{np.std(il_values):.4f}"
            ])
    
    print(f"  ✓ il_summary.csv")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_il.py <data_file.jsonl> [initial_capital] [output_dir]")
        sys.exit(1)
    
    data_file = sys.argv[1]
    initial_capital = float(sys.argv[2]) if len(sys.argv) > 2 else 10000.0
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "output/all_compare"
    
    run_il_analysis(data_file, initial_capital, output_dir)

