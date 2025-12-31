# AMM 回測系統

基於 Uniswap V3 風格的 AMM（自動做市商）績效回測系統，使用 WBTC-USDC 池的歷史事件數據進行回測分析。

## 功能特點

- ✅ Uniswap V3 風格的集中流動性模擬
- ✅ 支持 Mint、Burn、Swap 事件處理
- ✅ **ATR 動態 Rebalancing 策略**（基於 Average True Range 自動調整 LP 區間）
- ✅ 完整的績效分析（收益率、夏普比率、最大回撤等）
- ✅ LP 特定指標（無常損失、手續費收入等）
- ✅ 歷史價格和價值追蹤
- ✅ 自動導出 CSV 數據和圖表

## 項目結構

```
katana_backtest/
├── data/
│   ├── wbtc_usdc_pool_events.jsonl    # WBTC-USDC 池事件數據
│   └── usdc_eth_pool_events.jsonl     # USDC-ETH 池事件數據
├── src/
│   ├── __init__.py                    # 模組初始化
│   ├── amm_simulator.py               # AMM 模擬器核心
│   ├── atr_strategy.py                # ATR 策略（動態 LP 區間）
│   ├── backtest_engine.py             # 回測引擎
│   ├── event_processor.py             # 事件處理器
│   ├── output_generator.py            # 輸出生成器（CSV、圖表）
│   ├── performance_analyzer.py        # 績效分析器
│   ├── uniswap_v3_math.py             # Uniswap V3 數學計算
│   ├── main.py                        # 主程序入口
│   └── output/                        # 輸出目錄（自動生成）
│       ├── metrics.csv                # 績效指標 CSV
│       ├── price_history.csv          # 價格歷史 CSV
│       ├── value_history.csv          # 價值歷史 CSV
│       ├── backtest_price_history.png # 價格走勢圖
│       ├── backtest_value_history.png # 價值走勢圖
│       ├── backtest_return_distribution.png  # 收益分佈圖
│       └── backtest_price_atr_range.png      # ATR 區間圖（使用 ATR 策略時）
├── requirements.txt                   # 依賴列表
├── README.md                          # 本文件
├── QUICK_START.md                     # 快速開始指南
├── ATR_STRATEGY.md                    # ATR 策略說明
├── ATR_USAGE.md                       # ATR 使用指南
├── SIMULATION_VS_REAL.md              # 模擬與實盤差異說明
├── BUGFIX_SUMMARY.md                  # Bug 修復記錄
└── run_example.sh                     # 示例運行腳本
```

## 安裝

1. 確保 Python 3.8+ 已安裝

2. 安裝依賴：
```bash
pip install -r requirements.txt
```

## 使用方法

### 基本使用

```bash
# 從 src 目錄運行
cd src
python main.py --data ../data/wbtc_usdc_pool_events.jsonl --capital 10000
```

### 使用 ATR 動態 Rebalancing 策略

```bash
cd src
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --use-atr \
  --atr-period 14 \
  --atr-multiplier 2.0 \
  --rebalance-interval 180
```

### 命令行參數

```bash
python main.py [選項]

基本選項：
  --data PATH              數據文件路徑（默認：data/wbtc_usdc_pool_events.jsonl）
  --capital FLOAT          初始資金，單位 USDC（默認：10000.0）
  --start-block INT        起始區塊號（可選）
  --end-block INT          結束區塊號（可選）
  --start-timestamp INT    起始時間戳（可選）
  --end-timestamp INT      結束時間戳（可選）

LP 區間選項：
  --tick-lower INT         LP 價格區間下界 tick（可選，自動計算）
  --tick-upper INT         LP 價格區間上界 tick（可選，自動計算）
  --price-range-pct FLOAT  價格範圍百分比（默認：0.10，即 ±10%）

ATR 策略選項：
  --use-atr                啟用 ATR 動態 rebalancing 策略
  --atr-period INT         ATR 計算週期（默認：14）
  --atr-multiplier FLOAT   ATR 倍數，用於計算價格區間（默認：2.0，即 ±2*ATR）
  --rebalance-interval INT Rebalance 檢查間隔（秒，默認：180 = 3分鐘）

輸出選項：
  --output PATH            輸出報告文件路徑（可選）
  --output-dir PATH        輸出目錄，用於 CSV、圖片等（默認：output）
  --no-csv                 不導出 CSV 文件
  --no-plots               不導出圖表
  --export-json            導出 JSON 文件
```

### 使用示例

```bash
# 1. 基本回測（自動導出 CSV 和圖表到 output/ 目錄）
cd src
python main.py --data ../data/wbtc_usdc_pool_events.jsonl --capital 50000

# 2. 使用 ATR 策略進行動態 rebalancing
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --use-atr \
  --atr-period 14 \
  --atr-multiplier 2.0

# 3. 指定時間範圍
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --start-timestamp 1752790702 \
  --end-timestamp 1760000000

# 4. 自定義 LP 區間
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --price-range-pct 0.20  # ±20% 區間

# 5. 保存文字報告並自定義輸出目錄
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --output ../reports/backtest_report.txt \
  --output-dir ../reports
```

## ATR 策略說明

ATR (Average True Range) 策略是一種基於市場波動性的動態 LP 區間管理策略：

1. **ATR 計算**：使用過去 N 個週期的價格數據計算平均真實波動幅度
2. **區間設定**：LP 價格區間設定為 `當前價格 ± ATR * 倍數`
3. **自動 Rebalance**：當價格接近區間邊界（距離邊界 < 20% 範圍寬度）時，自動調整區間

### 策略參數

| 參數 | 說明 | 默認值 | 建議範圍 |
|------|------|--------|----------|
| `atr-period` | ATR 計算週期 | 14 | 7-21 |
| `atr-multiplier` | ATR 倍數 | 2.0 | 1.5-3.0 |
| `rebalance-interval` | 檢查間隔（秒） | 180 | 60-600 |

### ATR 策略輸出

使用 ATR 策略時，會額外生成：
- `backtest_price_atr_range.png`：價格走勢與 ATR 動態區間的可視化圖表
- 包含 ATR 值、rebalance 次數等額外指標

## 作為 Python 模組使用

```python
from src.backtest_engine import BacktestEngine
from src.performance_analyzer import PerformanceAnalyzer
from src.output_generator import OutputGenerator

# 創建回測引擎
engine = BacktestEngine(
    data_file='data/wbtc_usdc_pool_events.jsonl',
    initial_capital=10000.0
)

# 執行回測（使用 ATR 策略）
metrics = engine.run_backtest(
    start_timestamp=1752790702,
    end_timestamp=1760000000,
    use_atr_strategy=True,
    atr_period=14,
    atr_multiplier=2.0,
    rebalance_interval=180
)

# 分析結果
analyzer = PerformanceAnalyzer()
report = analyzer.generate_report(metrics)
print(report)

# 導出數據
output_gen = OutputGenerator(output_dir='output')
output_gen.export_value_history_csv(engine.get_value_history())
output_gen.export_price_history_csv(engine.get_price_history())
output_gen.export_plots(
    engine.get_value_history(),
    engine.get_price_history(),
    metrics
)
```

## 數據格式

輸入數據應為 JSONL 格式，每行一個 JSON 對象，包含以下事件類型：

### Mint 事件
```json
{
  "eventType": "Mint",
  "blockNumber": 6045392,
  "blockTimestamp": 1752790702,
  "transactionHash": "...",
  "owner": "0x...",
  "tickLower": 65940,
  "tickUpper": 76010,
  "liquidity": 48887979,
  "amount0": 313043,
  "amount1": 378146271,
  "amount0_wbtc": 0.00313043,
  "amount1_usdc": 378.146271
}
```

### Burn 事件
```json
{
  "eventType": "Burn",
  "blockNumber": 6045392,
  "blockTimestamp": 1752790702,
  "owner": "0x...",
  "tickLower": 65940,
  "tickUpper": 76010,
  "liquidity": 48887979
}
```

### Swap 事件
```json
{
  "eventType": "Swap",
  "blockNumber": 6049908,
  "blockTimestamp": 1752790702,
  "amount0": 30370,
  "amount1": -36566073,
  "sqrtPriceX96": 2745620485994069963109933671105,
  "price": 120094.14807813264,
  "liquidity": 340723611,
  "tick": 70912
}
```

## 績效指標說明

### 基本指標
- **總收益率**：整個回測期間的總收益率
- **年化收益率**：按年化計算的收益率
- **最大回撤**：從峰值到谷值的最大跌幅
- **夏普比率**：風險調整後的收益指標
- **波動率**：收益率的年化標準差

### LP 特定指標
- **總手續費收入**：累積的手續費收入（USDC）
- **無常損失 (IL)**：由於價格變化導致的損失百分比（相對於 HODL）
- **流動性效率**：流動性使用效率指標

### ATR 策略指標
- **ATR 值**：當前計算的 ATR 值
- **Rebalance 次數**：策略調整區間的次數
- **區間覆蓋率**：價格在 LP 區間內的時間比例

## 輸出文件說明

| 文件 | 說明 |
|------|------|
| `metrics.csv` | 所有績效指標的 CSV 格式 |
| `price_history.csv` | 每個時間點的價格記錄 |
| `value_history.csv` | 每個時間點的組合價值記錄 |
| `backtest_price_history.png` | 價格走勢圖 |
| `backtest_value_history.png` | 組合價值走勢圖 |
| `backtest_return_distribution.png` | 收益分佈直方圖 |
| `backtest_price_atr_range.png` | 價格與 ATR 動態區間圖（ATR 策略專用） |

## 注意事項

⚠️ **重要**：本系統是模擬系統，與真實實盤存在差異。請參考 `SIMULATION_VS_REAL.md` 了解詳細差異。

主要限制：
- 未考慮 Gas 費用
- 手續費計算基於簡化模型
- 未模擬滑點和 MEV 攻擊
- 假設完美執行時機
- Rebalance 成本未完全計入

## 開發

### 運行測試

```bash
# 運行基本回測測試
python test_backtest.py

# 檢查代碼語法
python -m py_compile src/*.py
```

### 模組說明

| 模組 | 說明 |
|------|------|
| `amm_simulator.py` | 核心 AMM 邏輯，包含流動性計算、手續費分配 |
| `atr_strategy.py` | ATR 策略實現，動態 LP 區間計算 |
| `backtest_engine.py` | 回測流程控制，事件處理 |
| `event_processor.py` | JSONL 數據解析和事件處理 |
| `output_generator.py` | CSV、JSON、圖表生成 |
| `performance_analyzer.py` | 績效指標計算和報告生成 |
| `uniswap_v3_math.py` | Uniswap V3 數學公式實現 |

## 相關文檔

- [快速開始](QUICK_START.md)
- [ATR 策略詳解](ATR_STRATEGY.md)
- [ATR 使用指南](ATR_USAGE.md)
- [模擬與實盤差異](SIMULATION_VS_REAL.md)
- [回測方法論](BACKTEST_METHODOLOGY.md)
- [Bug 修復記錄](BUGFIX_SUMMARY.md)

## 許可證

MIT License

## 貢獻

歡迎提交 Issue 和 Pull Request！

## 聯繫

如有問題或建議，請開 Issue。
