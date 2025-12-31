# 快速開始指南

## 如何運行模擬

### 1. 基本回測（控制台輸出）

```bash
cd src
python main.py --data ../data/wbtc_usdc_pool_events.jsonl --capital 10000
```

**輸出**：
- 控制台顯示績效報告
- 包含收益率、手續費收入等指標

### 2. 導出 CSV 文件

```bash
cd src
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --export-csv \
  --output-dir ../output
```

**輸出文件**（在 `output/` 目錄）：
- `value_history.csv` - 投資組合價值歷史
- `price_history.csv` - 價格歷史
- `metrics.csv` - 績效指標摘要

### 3. 導出 JSON 文件

```bash
cd src
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --export-json \
  --output-dir ../output
```

**輸出文件**：
- `metrics.json` - 績效指標（JSON 格式）

### 4. 生成圖表（需要 matplotlib）

```bash
# 先安裝 matplotlib
pip install matplotlib

# 運行回測並生成圖表
cd src
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --export-plots \
  --output-dir ../output
```

**輸出圖片**（在 `output/` 目錄）：
- `backtest_value_history.png` - 價值變化圖
- `backtest_price_history.png` - 價格變化圖
- `backtest_return_distribution.png` - 收益率分佈圖

### 5. 完整輸出（所有格式）

```bash
cd src
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --export-csv \
  --export-json \
  --export-plots \
  --output-dir ../output \
  --output ../output/report.txt
```

## 輸出文件說明

### 控制台輸出（Log）

每次運行都會在控制台顯示：
- 回測進度信息
- 事件處理統計
- 完整的績效報告

### CSV 文件

#### value_history.csv
```csv
timestamp,datetime,value_usdc
1752790702,2025-07-18 06:18:22,10000.00
1752791702,2025-07-18 06:35:02,10045.23
...
```

#### price_history.csv
```csv
timestamp,datetime,price_usdc
1752790702,2025-07-18 06:18:22,120094.15
1752791702,2025-07-18 06:35:02,120125.32
...
```

#### metrics.csv
```csv
指標,數值,單位
總收益率,15.23,%
年化收益率,18.45,%
最大回撤,8.32,%
...
```

### JSON 文件

#### metrics.json
```json
{
  "basic_metrics": {
    "total_return": 15.23,
    "annualized_return": 18.45,
    ...
  },
  "lp_metrics": {
    "total_fees_earned": 234.56,
    ...
  }
}
```

### 圖片文件（PNG）

- **價值歷史圖**：顯示投資組合價值隨時間變化
- **價格歷史圖**：顯示 WBTC/USDC 價格變化
- **收益率分佈圖**：顯示收益率的分佈情況

## 輸出目錄結構

```
output/
├── report.txt                    # 文本報告（如果指定）
├── value_history.csv            # 價值歷史
├── price_history.csv             # 價格歷史
├── metrics.csv                   # 績效指標（CSV）
├── metrics.json                  # 績效指標（JSON）
├── backtest_value_history.png    # 價值圖表
├── backtest_price_history.png    # 價格圖表
└── backtest_return_distribution.png  # 收益率分佈圖
```

## 注意事項

1. **數據量大**：完整數據集有 25 萬+ 事件，處理可能需要一些時間
2. **內存使用**：可以通過 `--start-timestamp` 和 `--end-timestamp` 限制範圍
3. **圖表生成**：需要安裝 `matplotlib`：`pip install matplotlib`

## 示例輸出

運行後你會看到類似這樣的輸出：

```
============================================================
AMM 回測系統
============================================================
數據文件: ../data/wbtc_usdc_pool_events.jsonl
初始資金: 10,000.00 USDC

開始回測...
處理 254710 個事件...
回測完成！
  - 處理了 233794 個 Swap, 10286 個 Mint, 10630 個 Burn
  - 最終價格: 118325.03 USDC
  - 最終價值: 11523.45 USDC
  - 總收益率: 15.23%

============================================================
AMM 回測績效報告
============================================================
...
```

