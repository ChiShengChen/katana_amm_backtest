#!/bin/bash
# AMM 回測系統使用示例腳本

echo "=========================================="
echo "AMM 回測系統 - 使用示例"
echo "=========================================="
echo ""

# 進入 src 目錄
cd src || exit 1

# 檢查數據文件是否存在
if [ ! -f "../data/wbtc_usdc_pool_events.jsonl" ]; then
    echo "錯誤：數據文件不存在: ../data/wbtc_usdc_pool_events.jsonl"
    exit 1
fi

# 示例 1: 基本回測（固定區間策略）
echo "示例 1: 基本回測（固定區間策略，±10%）"
echo "----------------------------------------"
echo "策略：在指定價格區間提供流動性，持有到結束"
echo ""
python3 main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --price-range-pct 0.10 \
  --output-dir output

echo ""
echo "=========================================="
echo ""

# 示例 2: ATR 動態區間回測（推薦）
echo "示例 2: ATR 動態區間回測（定期再平衡）"
echo "----------------------------------------"
echo "策略：使用 ATR 計算動態價格區間，每 3 分鐘檢查是否需要 rebalance"
echo "參數："
echo "  - ATR 週期: 14"
echo "  - ATR 倍數: 2.0（±2*ATR）"
echo "  - 再平衡間隔: 180 秒（3 分鐘）"
echo ""
python3 main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --use-atr \
  --atr-period 14 \
  --atr-multiplier 2.0 \
  --rebalance-interval 180 \
  --output-dir output

echo ""
echo "=========================================="
echo ""

# 示例 3: 自定義 ATR 參數
echo "示例 3: 自定義 ATR 參數（更頻繁的 rebalance）"
echo "----------------------------------------"
echo "策略：使用較短的 ATR 週期和更頻繁的 rebalance"
echo "參數："
echo "  - ATR 週期: 7"
echo "  - ATR 倍數: 1.5（±1.5*ATR，更窄的區間）"
echo "  - 再平衡間隔: 60 秒（1 分鐘）"
echo ""
echo "取消註釋以下行以運行："
# python3 main.py \
#   --data ../data/wbtc_usdc_pool_events.jsonl \
#   --capital 10000 \
#   --use-atr \
#   --atr-period 7 \
#   --atr-multiplier 1.5 \
#   --rebalance-interval 60 \
#   --output-dir output

echo ""
echo "=========================================="
echo ""

# 示例 4: 固定區間策略（自定義範圍）
echo "示例 4: 固定區間策略（自定義價格範圍）"
echo "----------------------------------------"
echo "策略：使用自定義的價格區間（±5%）"
echo ""
echo "取消註釋以下行以運行："
# python3 main.py \
#   --data ../data/wbtc_usdc_pool_events.jsonl \
#   --capital 10000 \
#   --price-range-pct 0.05 \
#   --output-dir output

echo ""
echo "=========================================="
echo ""

# 示例 5: 指定時間範圍回測
echo "示例 5: 指定時間範圍回測"
echo "----------------------------------------"
echo "策略：只回測指定時間範圍內的數據"
echo ""
echo "取消註釋以下行以運行（需要替換為實際的時間戳）："
# python3 main.py \
#   --data ../data/wbtc_usdc_pool_events.jsonl \
#   --capital 10000 \
#   --use-atr \
#   --start-timestamp 1700000000 \
#   --end-timestamp 1701000000 \
#   --output-dir output

echo ""
echo "=========================================="
echo ""

# 輸出說明
echo "輸出文件說明："
echo "----------------------------------------"
echo "所有輸出文件保存在 output/ 目錄中："
echo "  - backtest_*.csv: CSV 格式的數據文件"
echo "    * backtest_value_history.csv: 價值歷史"
echo "    * backtest_price_history.csv: 價格歷史"
echo "    * backtest_metrics.csv: 績效指標"
echo ""
echo "  - backtest_*.png: 圖表文件"
echo "    * backtest_value_history.png: 價值走勢圖"
echo "    * backtest_price_history.png: 價格走勢圖"
echo "    * backtest_return_distribution.png: 收益率分佈圖"
echo "    * backtest_price_atr_range.png: 價格與 ATR 範圍圖（僅 ATR 策略）"
echo ""
echo "  - backtest_metrics.json: JSON 格式的績效指標"
echo ""
echo "注意："
echo "  - CSV 和圖表默認啟用（除非使用 --no-csv 或 --no-plots）"
echo "  - 需要安裝 matplotlib 才能生成圖表：pip install matplotlib"
echo "  - ATR 策略會生成額外的價格與 ATR 範圍圖"
echo ""
echo "完成！檢查 output/ 目錄查看結果"

