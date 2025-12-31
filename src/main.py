"""
AMM 回測系統主程序
"""
import argparse
import sys
from pathlib import Path
try:
    from .backtest_engine import BacktestEngine
    from .performance_analyzer import PerformanceAnalyzer
    from .output_generator import OutputGenerator
except ImportError:
    from backtest_engine import BacktestEngine
    from performance_analyzer import PerformanceAnalyzer
    from output_generator import OutputGenerator


def main():
    parser = argparse.ArgumentParser(description='AMM 回測系統')
    parser.add_argument(
        '--data',
        type=str,
        default='data/wbtc_usdc_pool_events.jsonl',
        help='數據文件路徑'
    )
    parser.add_argument(
        '--capital',
        type=float,
        default=10000.0,
        help='初始資金 (USDC)'
    )
    parser.add_argument(
        '--start-block',
        type=int,
        default=None,
        help='起始區塊號'
    )
    parser.add_argument(
        '--end-block',
        type=int,
        default=None,
        help='結束區塊號'
    )
    parser.add_argument(
        '--start-timestamp',
        type=int,
        default=None,
        help='起始時間戳'
    )
    parser.add_argument(
        '--end-timestamp',
        type=int,
        default=None,
        help='結束時間戳'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='輸出報告文件路徑'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='輸出目錄（用於 CSV、圖片等）'
    )
    parser.add_argument(
        '--no-csv',
        action='store_true',
        help='不導出 CSV 文件（默認會導出）'
    )
    parser.add_argument(
        '--no-plots',
        action='store_true',
        help='不導出圖表（默認會導出，需要 matplotlib）'
    )
    parser.add_argument(
        '--export-json',
        action='store_true',
        default=False,
        help='導出 JSON 文件'
    )
    parser.add_argument(
        '--tick-lower',
        type=int,
        default=None,
        help='LP 價格區間下界 tick（如果不指定則自動計算）'
    )
    parser.add_argument(
        '--tick-upper',
        type=int,
        default=None,
        help='LP 價格區間上界 tick（如果未指定，則根據 --price-range 計算）'
    )
    parser.add_argument(
        '--price-range-pct',
        type=float,
        default=0.10,
        help='價格範圍百分比（例如 0.10 表示 ±10%%，默認 0.10）'
    )
    parser.add_argument(
        '--use-atr',
        action='store_true',
        help='使用 ATR 策略進行動態 rebalancing'
    )
    parser.add_argument(
        '--atr-period',
        type=int,
        default=14,
        help='ATR 計算週期（默認 14）'
    )
    parser.add_argument(
        '--atr-multiplier',
        type=float,
        default=2.0,
        help='ATR 倍數，用於計算價格區間（默認 2.0，即 ±2*ATR）'
    )
    parser.add_argument(
        '--rebalance-interval',
        type=int,
        default=180,
        help='Rebalance 檢查間隔（秒，默認 180 = 3分鐘）'
    )
    
    args = parser.parse_args()
    
    # 設置默認值：CSV 和圖表默認啟用（除非明確禁用）
    args.export_csv = not args.no_csv
    args.export_plots = not args.no_plots
    
    # 檢查文件是否存在
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"錯誤：數據文件不存在: {args.data}")
        sys.exit(1)
    
    print("=" * 60)
    print("AMM 回測系統")
    print("=" * 60)
    print(f"數據文件: {args.data}")
    print(f"初始資金: {args.capital:,.2f} USDC")
    print()
    
    # 創建回測引擎
    engine = BacktestEngine(
        data_file=str(data_path.absolute()),
        initial_capital=args.capital
    )
    
    # 執行回測
    try:
        metrics = engine.run_backtest(
            start_block=args.start_block,
            end_block=args.end_block,
            start_timestamp=args.start_timestamp,
            end_timestamp=args.end_timestamp,
            tick_lower=args.tick_lower,
            tick_upper=args.tick_upper,
            price_range_pct=args.price_range_pct,
            use_atr_strategy=args.use_atr,
            atr_period=args.atr_period,
            atr_multiplier=args.atr_multiplier,
            rebalance_interval=args.rebalance_interval
        )
        
        # 生成報告
        analyzer = PerformanceAnalyzer()
        report = analyzer.generate_report(metrics)
        
        print(report)
        
        # 保存報告
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n報告已保存至: {args.output}")
        
        # 導出其他格式（默認導出 CSV 和圖表）
        output_gen = OutputGenerator(output_dir=args.output_dir)
        exported_files = []
        
        # 確保默認值
        export_csv = getattr(args, 'export_csv', True)
        export_plots = getattr(args, 'export_plots', True)
        export_json = getattr(args, 'export_json', False)
        
        if export_csv or export_plots or export_json:
            print(f"\n導出文件到: {args.output_dir}/")
        
        if export_csv:
            value_csv = output_gen.export_value_history_csv(engine.get_value_history())
            price_csv = output_gen.export_price_history_csv(engine.get_price_history())
            metrics_csv = output_gen.export_metrics_csv(metrics)
            exported_files.extend([value_csv, price_csv, metrics_csv])
            print(f"  ✓ CSV 文件已導出 (3 個文件)")
        
        if export_json:
            metrics_json = output_gen.export_metrics_json(metrics)
            exported_files.append(metrics_json)
            print(f"  ✓ JSON 文件已導出")
        
        if export_plots:
            # 生成基本圖表
            plot_files = output_gen.export_plots(
                engine.get_value_history(),
                engine.get_price_history(),
                metrics
            )
            exported_files.extend(plot_files)
            
            # 如果使用 ATR 策略，生成帶有指標面板的 ATR 範圍圖
            if args.use_atr and hasattr(engine, 'atr_range_history') and engine.atr_range_history:
                try:
                    rebalance_history = None
                    if hasattr(engine, 'rebalance_history'):
                        rebalance_history = engine.rebalance_history
                    
                    atr_plot = output_gen.plot_price_with_atr_range(
                        price_history=engine.get_price_history(),
                        atr_range_history=engine.atr_range_history,
                        rebalance_history=rebalance_history,
                        metrics=metrics,
                        initial_capital=args.capital,
                        value_history=engine.get_value_history()
                    )
                    if atr_plot:
                        exported_files.append(atr_plot)
                        print(f"  ✓ 價格與 ATR 範圍圖（含指標面板）已導出")
                except Exception as e:
                    print(f"  ⚠ 生成 ATR 範圍圖時發生錯誤: {e}")
                    import traceback
                    traceback.print_exc()
            
            if plot_files:
                print(f"  ✓ 圖表已導出 ({len(plot_files)} 個)")
            else:
                print(f"  ⚠ 無法生成圖表（需要安裝 matplotlib: pip install matplotlib）")
        
        if exported_files:
            print(f"\n所有文件已保存到: {args.output_dir}/")
        
    except Exception as e:
        print(f"回測過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

