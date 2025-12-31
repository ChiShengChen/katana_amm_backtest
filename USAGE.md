# AMM 回測系統使用指南

## 快速開始

### 基本回測（僅控制台輸出）

```bash
cd src
python main.py --data ../data/wbtc_usdc_pool_events.jsonl --capital 10000
```

### 完整回測（導出所有格式）

```bash
cd src
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --export-csv \
  --export-json \
  --export-plots \
  --output-dir ../output
```

## 命令行參數

### 基本參數

- `--data PATH`: 數據文件路徑（默認：`data/wbtc_usdc_pool_events.jsonl`）
- `--capital FLOAT`: 初始資金，單位 USDC（默認：10000.0）
- `--output PATH`: 輸出文本報告文件路徑（可選）

### 時間範圍過濾

- `--start-block INT`: 起始區塊號
- `--end-block INT`: 結束區塊號
- `--start-timestamp INT`: 起始時間戳（Unix timestamp）
- `--end-timestamp INT`: 結束時間戳（Unix timestamp）

### 導出選項

- `--export-csv`: 導出 CSV 文件（價值歷史、價格歷史、績效指標）
- `--export-json`: 導出 JSON 文件（績效指標）
- `--export-plots`: 導出圖表（需要 matplotlib）
- `--output-dir PATH`: 輸出目錄（默認：`output`）

## 輸出文件說明

### 1. 控制台輸出（Log）

運行回測時，控制台會顯示：

```
============================================================
AMM 回測系統
============================================================
數據文件: data/wbtc_usdc_pool_events.jsonl
初始資金: 10,000.00 USDC

開始回測...
處理 254710 個事件...
回測完成！
  - 處理了 233794 個 Swap, 10286 個 Mint, 10630 個 Burn

============================================================
AMM 回測績效報告
============================================================

【基本指標】
  總收益率: 15.23%
  年化收益率: 18.45%
  最大回撤: 8.32%
  夏普比率: 1.25
  波動率: 12.34%

【LP 特定指標】
  總手續費收入: 234.56 USDC
  無常損失: -2.15%
  流動性效率: 15.42

【交易統計】
  Swap 次數: 233,794
  Mint 次數: 10,286
  Burn 次數: 10,630
```

### 2. CSV 文件

使用 `--export-csv` 會生成以下 CSV 文件：

#### `value_history.csv`
投資組合價值歷史記錄

| timestamp | datetime | value_usdc |
|-----------|----------|------------|
| 1752790702 | 2025-07-18 06:18:22 | 10000.00 |
| 1752791702 | 2025-07-18 06:35:02 | 10045.23 |
| ... | ... | ... |

#### `price_history.csv`
WBTC/USDC 價格歷史記錄

| timestamp | datetime | price_usdc |
|-----------|----------|------------|
| 1752790702 | 2025-07-18 06:18:22 | 120094.15 |
| 1752791702 | 2025-07-18 06:35:02 | 120125.32 |
| ... | ... | ... |

#### `metrics.csv`
績效指標摘要

| 指標 | 數值 | 單位 |
|------|------|------|
| 總收益率 | 15.23 | % |
| 年化收益率 | 18.45 | % |
| 最大回撤 | 8.32 | % |
| 夏普比率 | 1.25 | |
| 波動率 | 12.34 | % |
| 總手續費收入 | 234.56 | USDC |
| ... | ... | ... |

### 3. JSON 文件

使用 `--export-json` 會生成 `metrics.json`：

```json
{
  "basic_metrics": {
    "total_return": 15.23,
    "annualized_return": 18.45,
    "max_drawdown": 8.32,
    "sharpe_ratio": 1.25,
    "volatility": 12.34
  },
  "lp_metrics": {
    "total_fees_earned": 234.56,
    "impermanent_loss": -2.15,
    "liquidity_efficiency": 15.42
  },
  "trading_stats": {
    "num_swaps": 233794,
    "num_mints": 10286,
    "num_burns": 10630
  }
}
```

### 4. 圖表（PNG 圖片）

使用 `--export-plots` 會生成以下圖表（需要安裝 matplotlib）：

#### `backtest_value_history.png`
投資組合價值隨時間變化圖

- X 軸：時間（日期）
- Y 軸：價值（USDC）
- 包含初始資金參考線

#### `backtest_price_history.png`
WBTC/USDC 價格隨時間變化圖

- X 軸：時間（日期）
- Y 軸：價格（USDC）

#### `backtest_return_distribution.png`
收益率分佈直方圖

- X 軸：收益率（%）
- Y 軸：頻率

## 使用示例

### 示例 1：基本回測

```bash
cd src
python main.py --data ../data/wbtc_usdc_pool_events.jsonl --capital 50000
```

### 示例 2：指定時間範圍

```bash
cd src
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --start-timestamp 1752790702 \
  --end-timestamp 1760000000
```

### 示例 3：導出所有格式

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

### 示例 4：只導出 CSV 和 JSON

```bash
cd src
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --export-csv \
  --export-json \
  --output-dir ../output
```

## 輸出目錄結構

運行完整回測後，`output/` 目錄結構如下：

```
output/
├── report.txt                    # 文本報告（如果指定 --output）
├── value_history.csv             # 價值歷史
├── price_history.csv             # 價格歷史
├── metrics.csv                   # 績效指標
├── metrics.json                  # 績效指標（JSON）
├── backtest_value_history.png    # 價值圖表
├── backtest_price_history.png    # 價格圖表
└── backtest_return_distribution.png  # 收益率分佈圖
```

## 安裝可選依賴

### 生成圖表需要 matplotlib

```bash
pip install matplotlib
```

或者安裝所有可選依賴：

```bash
pip install matplotlib numpy pandas
```

## 日誌輸出

系統會在控制台輸出以下信息：

1. **初始化信息**：數據文件路徑、初始資金
2. **處理進度**：事件處理數量
3. **完成信息**：處理的事件統計（Swap、Mint、Burn 數量）
4. **績效報告**：完整的績效指標報告
5. **導出信息**：導出的文件列表和路徑

## 注意事項

1. **數據文件路徑**：可以使用相對路徑或絕對路徑
2. **輸出目錄**：如果不存在會自動創建
3. **圖表生成**：如果未安裝 matplotlib，會跳過圖表生成並顯示警告
4. **時間戳格式**：CSV 和圖表中的時間戳會自動轉換為可讀的日期時間格式

## 故障排除

### 問題：找不到數據文件

```
錯誤：數據文件不存在: data/wbtc_usdc_pool_events.jsonl
```

**解決方案**：檢查文件路徑，使用絕對路徑或確保相對路徑正確。

### 問題：無法生成圖表

```
⚠ 無法生成圖表（需要安裝 matplotlib）
```

**解決方案**：
```bash
pip install matplotlib
```

### 問題：內存不足

如果處理大量數據時內存不足，可以：
1. 使用 `--start-timestamp` 和 `--end-timestamp` 限制數據範圍
2. 使用 `--start-block` 和 `--end-block` 限制區塊範圍

