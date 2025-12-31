"""
輸出生成器：生成 CSV、圖片和日誌文件
"""
import csv
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime

try:
    from .performance_analyzer import PerformanceMetrics
except ImportError:
    from performance_analyzer import PerformanceMetrics


class OutputGenerator:
    """輸出生成器"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_value_history_csv(
        self,
        value_history: List[Tuple[int, float]],
        filename: str = "value_history.csv"
    ) -> str:
        """導出價值歷史到 CSV"""
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'datetime', 'value_usdc'])
            
            for timestamp, value in value_history:
                dt = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow([timestamp, dt, f"{value:.2f}"])
        
        return str(filepath)
    
    def export_price_history_csv(
        self,
        price_history: List[Tuple[int, float]],
        filename: str = "price_history.csv"
    ) -> str:
        """導出價格歷史到 CSV"""
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'datetime', 'price_usdc'])
            
            for timestamp, price in price_history:
                dt = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow([timestamp, dt, f"{price:.2f}"])
        
        return str(filepath)
    
    def export_metrics_csv(
        self,
        metrics: PerformanceMetrics,
        filename: str = "metrics.csv"
    ) -> str:
        """導出績效指標到 CSV"""
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 基本指標
            writer.writerow(['指標', '數值', '單位'])
            writer.writerow(['總收益率', f"{metrics.total_return:.2f}", '%'])
            writer.writerow(['年化收益率', f"{metrics.annualized_return:.2f}", '%'])
            writer.writerow(['最大回撤', f"{metrics.max_drawdown:.2f}", '%'])
            writer.writerow(['夏普比率', f"{metrics.sharpe_ratio:.2f}", ''])
            writer.writerow(['波動率', f"{metrics.volatility:.2f}", '%'])
            writer.writerow(['', '', ''])
            
            # LP 特定指標
            writer.writerow(['LP 特定指標', '', ''])
            writer.writerow(['總手續費收入', f"{metrics.total_fees_earned:.2f}", 'USDC'])
            writer.writerow(['無常損失', f"{metrics.impermanent_loss:.2f}", '%'])
            writer.writerow(['流動性效率', f"{metrics.liquidity_efficiency:.2f}", '%'])
            writer.writerow(['', '', ''])
            
            # 交易統計
            writer.writerow(['交易統計', '', ''])
            writer.writerow(['Swap 次數', f"{metrics.num_swaps:,}", ''])
            writer.writerow(['Mint 次數', f"{metrics.num_mints:,}", ''])
            writer.writerow(['Burn 次數', f"{metrics.num_burns:,}", ''])
        
        return str(filepath)
    
    def export_metrics_json(
        self,
        metrics: PerformanceMetrics,
        filename: str = "metrics.json"
    ) -> str:
        """導出績效指標到 JSON"""
        filepath = self.output_dir / filename
        
        data = {
            'basic_metrics': {
                'total_return': metrics.total_return,
                'annualized_return': metrics.annualized_return,
                'max_drawdown': metrics.max_drawdown,
                'sharpe_ratio': metrics.sharpe_ratio,
                'volatility': metrics.volatility,
            },
            'lp_metrics': {
                'total_fees_earned': metrics.total_fees_earned,
                'impermanent_loss': metrics.impermanent_loss,
                'liquidity_efficiency': metrics.liquidity_efficiency,
            },
            'trading_stats': {
                'num_swaps': metrics.num_swaps,
                'num_mints': metrics.num_mints,
                'num_burns': metrics.num_burns,
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def export_plots(
        self,
        value_history: List[Tuple[int, float]],
        price_history: List[Tuple[int, float]],
        metrics: PerformanceMetrics,
        prefix: str = "backtest",
        atr_range_history: Optional[List[Tuple[int, float, float, float, float]]] = None
    ) -> List[str]:
        """生成圖表（需要 matplotlib）"""
        try:
            import matplotlib
            matplotlib.use('Agg')  # 非交互式後端
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from datetime import datetime
        except ImportError:
            print("警告：matplotlib 未安裝，無法生成圖表")
            print("請運行: pip install matplotlib")
            return []
        
        filepaths = []
        
        # 1. 價值歷史圖
        if value_history:
            fig, ax = plt.subplots(figsize=(12, 6))
            timestamps = [ts for ts, _ in value_history]
            values = [v for _, v in value_history]
            dates = [datetime.fromtimestamp(ts) for ts in timestamps]
            
            ax.plot(dates, values, linewidth=2, label='Portfolio Value')
            ax.axhline(y=values[0] if values else 0, color='r', linestyle='--', alpha=0.5, label='Initial Capital')
            ax.set_xlabel('Date')
            ax.set_ylabel('Value (USDC)')
            ax.set_title('Portfolio Value Over Time')
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            filepath = self.output_dir / f"{prefix}_value_history.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            filepaths.append(str(filepath))
        
        # 2. 價格歷史圖
        if price_history:
            fig, ax = plt.subplots(figsize=(12, 6))
            timestamps = [ts for ts, _ in price_history]
            prices = [p for _, p in price_history]
            dates = [datetime.fromtimestamp(ts) for ts in timestamps]
            
            ax.plot(dates, prices, linewidth=1.5, color='green', alpha=0.7, label='WBTC/USDC Price')
            ax.set_xlabel('Date')
            ax.set_ylabel('Price (USDC)')
            ax.set_title('WBTC/USDC Price Over Time')
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            filepath = self.output_dir / f"{prefix}_price_history.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            filepaths.append(str(filepath))
        
        # 3. 收益率分佈圖
        if metrics.return_history:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.hist(metrics.return_history, bins=50, alpha=0.7, edgecolor='black')
            ax.axvline(x=0, color='r', linestyle='--', alpha=0.5)
            ax.set_xlabel('Return (%)')
            ax.set_ylabel('Frequency')
            ax.set_title('Return Distribution')
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            
            filepath = self.output_dir / f"{prefix}_return_distribution.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            filepaths.append(str(filepath))
        
        # 4. 價格與 ATR 範圍疊圖（如果提供了 ATR 數據）
        if atr_range_history and price_history:
            try:
                atr_plot = self.plot_price_with_atr_range(
                    price_history=price_history,
                    atr_range_history=atr_range_history,
                    prefix=prefix
                )
                if atr_plot:
                    filepaths.append(atr_plot)
            except Exception as e:
                print(f"  ⚠ 生成 ATR 範圍圖時發生錯誤: {e}")
        
        return filepaths
    
    def plot_price_with_atr_range(
        self,
        price_history: List[Tuple[int, float]],
        atr_range_history: List[Tuple[int, float, float, float, float]],
        prefix: str = "backtest",
        rebalance_history: Optional[List[Tuple[int, float, float, float]]] = None,
        metrics: Optional[Any] = None,
        initial_capital: float = 0.0,
        value_history: Optional[List[Tuple[int, float]]] = None
    ) -> str:
        """繪製價格與 ATR 範圍疊圖（類似 DeFi 儀表板樣式）"""
        if not price_history or not atr_range_history:
            return ""
        
        try:
            import matplotlib
            matplotlib.use('Agg')  # 非交互式後端
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from datetime import datetime
            import numpy as np
            from matplotlib.patches import Rectangle
        except ImportError:
            print("警告：matplotlib 未安裝，無法生成圖表")
            return ""
        
        # 創建圖表，使用更大的尺寸
        fig = plt.figure(figsize=(18, 10))
        fig.patch.set_facecolor('#ffffff')
        
        # 創建網格佈局：頂部指標 + 主圖表
        gs = fig.add_gridspec(2, 1, height_ratios=[1, 5], hspace=0.3)
        
        # 頂部指標面板
        metrics_ax = fig.add_subplot(gs[0])
        metrics_ax.axis('off')
        metrics_ax.set_facecolor('#f9fafb')
        
        # 計算指標
        if price_history:
            final_price = price_history[-1][1]
            if atr_range_history:
                last_atr = atr_range_history[-1]
                current_price = last_atr[1]
                atr_lower = last_atr[3]
                atr_upper = last_atr[4]
                in_range = atr_lower <= current_price <= atr_upper
            else:
                current_price = final_price
                atr_lower = atr_upper = 0
                in_range = False
        else:
            current_price = atr_lower = atr_upper = 0
            in_range = False
        
        # 計算費用相關指標
        total_fees = metrics.total_fees_earned if metrics else 0.0
        
        # 計算最終價值（從 value_history 獲取，如果有的話）
        if value_history and len(value_history) > 0:
            final_value = value_history[-1][1]
        elif len(price_history) > 1 and initial_capital > 0:
            # 簡化估算：假設價值與價格成正比
            price_change = price_history[-1][1] / price_history[0][1]
            final_value = initial_capital * price_change
        else:
            final_value = initial_capital
        
        # 計算 Fee APR（年化收益率）
        if initial_capital > 0 and len(price_history) > 1:
            # 計算時間跨度（年）
            time_span_days = (price_history[-1][0] - price_history[0][0]) / 86400
            time_span_years = time_span_days / 365.25
            if time_span_years > 0:
                fee_apr = (total_fees / initial_capital / time_span_years) * 100
            else:
                fee_apr = (total_fees / initial_capital) * 100
        else:
            fee_apr = 0.0
        
        # 計算 LP Width
        if atr_lower > 0 and atr_upper > 0:
            range_pct = ((atr_upper - atr_lower) / current_price) * 100 if current_price > 0 else 0
            if range_pct < 5:
                lp_width = "Narrow"
            elif range_pct < 15:
                lp_width = "Medium"
            else:
                lp_width = "Wide"
        else:
            lp_width = "N/A"
        
        # 計算 TVL（使用最終價值）
        tvl = final_value if final_value > 0 else initial_capital
        
        # 顯示指標
        metrics_text = []
        metrics_text.append(f"Fee APR: {fee_apr:+.2f}%")
        metrics_text.append(f"TVL: US${tvl:,.2f}")
        metrics_text.append(f"Earned Fees: US${total_fees:,.2f}")
        metrics_text.append(f"LP Width: {lp_width}")
        metrics_text.append(f"Status: {'In Range' if in_range else 'Out of Range'}")
        
        # 在頂部顯示指標（橫向排列）
        metrics_ax.text(0.05, 0.5, metrics_text[0], fontsize=12, fontweight='bold', 
                       color='#10b981' if fee_apr > 0 else '#ef4444',
                       transform=metrics_ax.transAxes, va='center')
        metrics_ax.text(0.25, 0.5, metrics_text[1], fontsize=12, fontweight='500',
                       transform=metrics_ax.transAxes, va='center')
        metrics_ax.text(0.45, 0.5, metrics_text[2], fontsize=12, fontweight='500',
                       transform=metrics_ax.transAxes, va='center')
        metrics_ax.text(0.65, 0.5, metrics_text[3], fontsize=12, fontweight='500',
                       transform=metrics_ax.transAxes, va='center')
        status_color = '#10b981' if in_range else '#ef4444'
        metrics_ax.text(0.85, 0.5, metrics_text[4], fontsize=12, fontweight='bold',
                       color=status_color, transform=metrics_ax.transAxes, va='center')
        
        # 主圖表
        ax = fig.add_subplot(gs[1])
        ax.set_facecolor('#fafafa')
        
        # 提取價格歷史數據
        timestamps = [ts for ts, _ in price_history]
        prices = [p for _, p in price_history]
        dates = [datetime.fromtimestamp(ts) for ts in timestamps]
        
        # 提取 ATR 範圍歷史數據
        atr_timestamps = [ts for ts, _, _, _, _ in atr_range_history]
        atr_prices = [p for _, p, _, _, _ in atr_range_history]
        atr_values = [atr for _, _, atr, _, _ in atr_range_history]
        atr_lower_list = [lower for _, _, _, lower, _ in atr_range_history]
        atr_upper_list = [upper for _, _, _, _, upper in atr_range_history]
        atr_dates = [datetime.fromtimestamp(ts) for ts in atr_timestamps]
        
        # 繪製 ATR 範圍（淺紫色陰影）
        ax.fill_between(
            atr_dates,
            atr_lower_list,
            atr_upper_list,
            alpha=0.25,
            color='#9b87f5',  # 淺紫色
            label='Price Range (Upper/Lower)',
            zorder=1
        )
        
        # 繪製 Upper 和 Lower 線
        ax.plot(atr_dates, atr_upper_list, color='#7c6cf0', linewidth=1.5, alpha=0.6, 
                label='Upper', linestyle='-', zorder=2)
        ax.plot(atr_dates, atr_lower_list, color='#7c6cf0', linewidth=1.5, alpha=0.6, 
                label='Lower', linestyle='-', zorder=2)
        
        # 繪製當前價格線（藍色實線）
        ax.plot(dates, prices, color='#3b82f6', linewidth=2.5, label='Price', 
                alpha=0.9, zorder=3)
        
        # 標記 rebalance 點（如果有）
        if rebalance_history:
            for reb_ts, reb_price, reb_lower, reb_upper in rebalance_history:
                reb_date = datetime.fromtimestamp(reb_ts)
                # 在價格線上標記 rebalance 點
                ax.scatter(reb_date, reb_price, color='#f59e0b', s=100, 
                          marker='v', zorder=4, edgecolors='white', linewidths=2,
                          label='Rebalance' if reb_ts == rebalance_history[0][0] else '')
        
        # 設置標籤和標題
        ax.set_xlabel('Time', fontsize=13, fontweight='500', color='#374151')
        ax.set_ylabel('Price (USDC)', fontsize=13, fontweight='500', color='#374151')
        ax.set_title('Historical Price with ATR Range', fontsize=16, fontweight='bold', 
                    color='#111827', pad=20)
        
        # 設置圖例
        legend = ax.legend(loc='upper left', fontsize=11, framealpha=0.95, 
                          edgecolor='#e5e7eb', facecolor='white', frameon=True)
        legend.get_frame().set_linewidth(0.5)
        
        # 設置網格
        ax.grid(True, alpha=0.2, color='#9ca3af', linestyle='-', linewidth=0.5, zorder=0)
        ax.set_axisbelow(True)
        
        # 格式化 x 軸日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        
        # 根據數據範圍設置合適的 locator（避免生成過多 ticks）
        if len(dates) > 0:
            date_range = (dates[-1] - dates[0]).days
            if date_range > 365:
                # 超過一年，使用月份
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=max(1, date_range // 365)))
            elif date_range > 30:
                # 超過一個月，使用週
                ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=max(1, date_range // 30)))
            elif date_range > 7:
                # 超過一週，使用天
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, date_range // 7)))
            else:
                # 一週內，使用天
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
        
        plt.xticks(rotation=0, ha='center')
        
        # 設置 y 軸格式
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        
        # 添加邊框樣式
        for spine in ax.spines.values():
            spine.set_edgecolor('#e5e7eb')
            spine.set_linewidth(0.5)
        
        # 調整佈局
        plt.tight_layout()
        
        # 保存圖表
        filepath = self.output_dir / f"{prefix}_price_atr_range.png"
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white', edgecolor='none')
        plt.close()
        
        return str(filepath)