# AMM 回測系統

基於 Uniswap V3 風格的 AMM（自動做市商）績效回測系統，使用 WBTC-USDC 池的歷史事件數據進行回測分析。

## 功能特點

- ✅ Uniswap V3 風格的集中流動性模擬
- ✅ 支持 Mint、Burn、Swap 事件處理
- ✅ **Omnis AI (ATR) 動態 Rebalancing 策略**
- ✅ **Steer Finance 策略** (Classic, Elastic, Fluid)
- ✅ **Charm Alpha Vault 策略** (被動再平衡)
- ✅ 完整的績效分析（收益率、夏普比率、最大回撤等）
- ✅ LP 特定指標（無常損失、手續費收入等）
- ✅ 多策略比較與視覺化圖表
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
│   ├── strategies/                    # 策略模組
│   │   ├── __init__.py
│   │   ├── base_strategy.py           # 策略基類
│   │   ├── uniswap_math.py            # V3 數學計算
│   │   ├── charm_strategy.py          # Charm Alpha Vault 策略
│   │   ├── steer_strategy.py          # Steer 策略 (Classic/Elastic/Fluid)
│   │   └── strategy_backtest.py       # 策略比較回測框架
│   └── output/                        # 輸出目錄
│       ├── marketing/                 # 行銷素材
│       └── all_compare/               # 所有策略比較
├── requirements.txt
├── README.md
└── run_example.sh
```

## 安裝

```bash
# 1. 確保 Python 3.8+ 已安裝
# 2. 安裝依賴
pip install -r requirements.txt
```

## 快速開始

### 基本回測

```bash
cd src
python main.py --data ../data/wbtc_usdc_pool_events.jsonl --capital 10000
```

### 使用 ATR 策略

```bash
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --use-atr \
  --atr-period 14 \
  --atr-multiplier 2.0
```

### 多策略比較

```bash
cd src
python -m strategies.strategy_backtest ../data/wbtc_usdc_pool_events.jsonl 10000
```

---

## 📊 支持的策略

### 1. Omnis AI (ATR Dynamic Range)

**核心理念**: 使用 ATR 指標動態調整 LP 區間

```
ATR = Average True Range（平均真實波動幅度）

區間設定:
├─ Upper = 當前價格 + (ATR × 乘數)
└─ Lower = 當前價格 - (ATR × 乘數)

特點:
✅ 動態適應市場波動
✅ 下跌時自動減少曝險
✅ 無協議費（自建策略）
```

**參數**:
| 參數 | 說明 | 預設值 |
|------|------|--------|
| `atr_period` | ATR 計算週期 | 14 |
| `atr_multiplier` | 區間寬度乘數 | 2.0 |
| `rebalance_interval` | 最小再平衡間隔 | 180 秒 |

---

### 2. Charm Alpha Vault (Passive Rebalancing)

**核心理念**: 完全被動再平衡，不執行 Swap

```
Base Order: 對稱區間，最大平衡流動性
Limit Order: 多餘資產設置為限價單，等待市場成交

特點:
✅ 零 Swap 成本
✅ 無滑點風險
✅ 協議費僅 2%
❌ 趨勢市場反應慢
```

**參數**:
| 參數 | 說明 | 預設值 |
|------|------|--------|
| `base_threshold` | Base Order 寬度 | 600 ticks |
| `limit_threshold` | Limit Order 寬度 | 1200 ticks |
| `rebalance_interval` | 再平衡間隔 | 48 小時 |

---

### 3. Steer Classic (Fixed Width)

**核心理念**: 固定區間寬度，價格觸發再平衡

```
固定區間: 600 ticks (~6%)
觸發條件: 價格偏離中心 > 5%

執行動作:
1. 撤出流動性
2. Swap 平衡資產
3. 重新部署

特點:
✅ 邏輯簡單透明
❌ 需要 Swap（有滑點）
❌ 協議費 15%
```

---

### 4. Steer Elastic (Bollinger Bands)

**核心理念**: 基於布林通道動態調整區間

```
Upper = SMA + 2σ
Lower = SMA - 2σ

高波動 → 區間擴大
低波動 → 區間收窄

⚠️ 警告: 頻繁 Rebalance 導致高 Gas 成本
```

---

## 📈 策略比較結果

基於 BTC 下跌 20% 的市場環境:

| 策略 | 收益率 | 最大回撤 | Rebalance | 評價 |
|------|--------|----------|-----------|------|
| 🏆 **Omnis AI (ATR)** | **-9.5%** | **-12.6%** | 37 | 最佳保護 |
| HODL 50/50 | -9.9% | -12.5% | 0 | 基準線 |
| Charm Alpha | -15.0% | -18.8% | 55 | 穩定但慢 |
| Steer Classic | -19.3% | -22.4% | 44 | 跟隨市場 |
| Pure BTC | -19.8% | -24.5% | 0 | 完全暴露 |
| ❌ Steer Elastic | -69.6% | -70.0% | 200 | 過度交易 |

詳細比較報告: `src/output/all_compare/README.md`

---

## 命令行參數

```bash
python main.py [選項]

基本選項：
  --data PATH              數據文件路徑
  --capital FLOAT          初始資金 (USDC)
  --start-timestamp INT    起始時間戳
  --end-timestamp INT      結束時間戳

LP 區間選項：
  --tick-lower INT         LP 區間下界
  --tick-upper INT         LP 區間上界
  --price-range-pct FLOAT  價格範圍百分比（默認 10%）

ATR 策略選項：
  --use-atr                啟用 ATR 策略
  --atr-period INT         ATR 週期（默認 14）
  --atr-multiplier FLOAT   ATR 乘數（默認 2.0）
  --rebalance-interval INT 再平衡間隔（秒）

輸出選項：
  --output-dir PATH        輸出目錄
  --no-csv                 不導出 CSV
  --no-plots               不導出圖表
```

---

## Python API 使用

### 單策略回測

```python
from src.backtest_engine import BacktestEngine

engine = BacktestEngine(
    data_file='data/wbtc_usdc_pool_events.jsonl',
    initial_capital=10000.0
)

metrics = engine.run_backtest(
    use_atr_strategy=True,
    atr_period=14,
    atr_multiplier=2.0
)
```

### 多策略比較

```python
from strategies import CharmAlphaVaultStrategy, SteerClassicStrategy
from strategies.strategy_backtest import StrategyBacktester, BacktestConfig
from decimal import Decimal

config = BacktestConfig(
    initial_amount0=Decimal('0.05'),
    initial_amount1=Decimal('5000'),
    pool_fee=3000
)

backtester = StrategyBacktester(config)
backtester.load_tick_data("../data/wbtc_usdc_pool_events.jsonl")

# 創建策略
charm = CharmAlphaVaultStrategy(base_threshold=600)
steer = SteerClassicStrategy(position_width_ticks=600)

# 運行回測
charm_result = backtester.run_backtest(charm)
steer_result = backtester.run_backtest(steer)

print(f"Charm Return: {charm_result.total_return_pct:.2f}%")
print(f"Steer Return: {steer_result.total_return_pct:.2f}%")
```

---

## 輸出文件

| 目錄 | 文件 | 說明 |
|------|------|------|
| `output/` | `metrics.csv` | 績效指標 |
| | `price_history.csv` | 價格歷史 |
| | `value_history.csv` | 價值歷史 |
| | `backtest_*.png` | 各類圖表 |
| `output/all_compare/` | `strategy_comparison_value.png` | 策略價值對比 |
| | `drawdown_comparison.png` | 回撤曲線 |
| | `crash_comparison_bar.png` | 崩盤損失對比 |
| | `README.md` | 詳細策略說明 |
| `output/marketing/` | 各類行銷素材圖表 | |

---

## 績效指標說明

### 基本指標
- **總收益率**: 回測期間總收益
- **年化收益率**: 按年計算的收益率
- **最大回撤**: 峰值到谷值的最大跌幅
- **夏普比率**: 風險調整後收益

### LP 特定指標
- **手續費收入**: 累積的交易手續費
- **無常損失 (IL)**: 相對於 HODL 的損失
- **區間內時間**: 價格在 LP 區間內的時間比例

---

## ⚠️ 注意事項

本系統為模擬系統，與實盤存在差異：

- Gas 費用為估算值
- 手續費計算基於簡化模型
- 未完全模擬滑點和 MEV
- 假設完美執行時機

詳見 `SIMULATION_VS_REAL.md`

---

## 相關文檔

- [快速開始](QUICK_START.md)
- [ATR 策略詳解](ATR_STRATEGY.md)
- [模擬與實盤差異](SIMULATION_VS_REAL.md)
- [策略比較報告](src/output/all_compare/README.md)

---

## 許可證

MIT License

## 貢獻

歡迎提交 Issue 和 Pull Request！
