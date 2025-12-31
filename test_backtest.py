#!/usr/bin/env python3
"""
簡單的測試腳本來驗證回測系統
"""
import sys
from pathlib import Path

# 添加 src 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from backtest_engine import BacktestEngine
from performance_analyzer import PerformanceAnalyzer

def main():
    data_file = Path(__file__).parent / 'data' / 'wbtc_usdc_pool_events.jsonl'
    
    if not data_file.exists():
        print(f"錯誤：數據文件不存在: {data_file}")
        return
    
    print("=" * 60)
    print("測試回測系統")
    print("=" * 60)
    print(f"數據文件: {data_file}")
    print()
    
    try:
        # 創建回測引擎
        engine = BacktestEngine(
            data_file=str(data_file),
            initial_capital=10000.0
        )
        
        # 執行回測（只處理前 1000 個事件作為測試）
        print("執行回測（測試模式：處理前 1000 個事件）...")
        
        # 讀取前幾個事件來測試
        from event_processor import EventProcessor
        processor = EventProcessor(str(data_file))
        events = []
        for i, event in enumerate(processor.read_events()):
            if i >= 1000:
                break
            events.append(event)
        
        if not events:
            print("錯誤：沒有找到事件數據")
            return
        
        # 手動處理事件
        num_swaps = 0
        num_mints = 0
        num_burns = 0
        
        for event in events:
            event_type = event.get('eventType')
            if event_type == 'Swap':
                num_swaps += 1
                engine._process_swap(event)
            elif event_type == 'Mint':
                num_mints += 1
                engine._process_mint(event)
            elif event_type == 'Burn':
                num_burns += 1
                engine._process_burn(event)
        
        # 計算最終價值
        current_price = engine.amm.get_current_price()
        final_value = engine._calculate_portfolio_value(current_price)
        
        print(f"\n處理完成：")
        print(f"  - Swap: {num_swaps}")
        print(f"  - Mint: {num_mints}")
        print(f"  - Burn: {num_burns}")
        print(f"  - 當前價格: {current_price:.2f}")
        print(f"  - 初始資金: {engine.initial_capital:.2f} USDC")
        print(f"  - 最終價值: {final_value:.2f} USDC")
        print(f"  - 收益率: {((final_value - engine.initial_capital) / engine.initial_capital * 100):.2f}%")
        
        print("\n✅ 系統運行正常！")
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

