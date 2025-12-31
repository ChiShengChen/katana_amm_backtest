# ATR 策略回測使用指南

## 概述

ATR (Average True Range) 策略是一個動態 LP 管理策略，根據市場波動性自動調整 LP 價格區間並進行 rebalancing。

## 策略原理

1. **ATR 計算**：計算價格的平均真實波動範圍
2. **動態區間**：根據 ATR 和當前價格動態設置 LP 價格區間（±ATR * multiplier）
3. **自動 Rebalancing**：當價格偏離區間中心超過閾值時，自動移除舊位置並創建新位置

## 使用方法

### 基本使用（ATR 策略）

```bash
cd src
python main.py --data ../data/wbtc_usdc_pool_events.jsonl --capital 10000 --use-atr
```

### 自定義參數

```bash
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --use-atr \
  --atr-period 14 \
  --atr-multiplier 2.0 \
  --rebalance-threshold 0.5 \
  --min-rebalance-interval 3600
```

## 參數說明

- `--use-atr`: 啟用 ATR 策略
- `--atr-period`: ATR 計算週期（默認 14）
- `--atr-multiplier`: ATR 倍數，用於計算價格區間（默認 2.0，即 ±2*ATR）
- `--rebalance-threshold`: Rebalance 觸發閾值（0.5 = 50%，即價格偏離中心超過區間大小的 50% 時觸發）
- `--min-rebalance-interval`: 最小 rebalance 間隔（秒，默認 3600 = 1小時）

## 策略行為

### 初始位置創建
- 等待 ATR 計算足夠的數據（至少 `atr_period` 個價格點）
- 使用 ATR 計算初始價格區間
- 在該區間內創建 LP 位置

### Rebalancing 觸發條件
1. 價格超出當前區間範圍
2. 價格偏離區間中心超過 `rebalance_threshold`
3. 距離上次 rebalance 超過 `min_rebalance_interval`

### Rebalancing 過程
1. 移除當前 LP 位置（提取流動性和累積的手續費）
2. 根據當前價格和 ATR 計算新區間
3. 在新區間內創建新的 LP 位置

## 輸出信息

運行時會顯示：
- ATR 值
- 每次 rebalance 的時間和原因
- Rebalance 次數統計
- 最終績效報告

## 示例輸出

```
策略: ATR 動態區間回測（自動 rebalancing）
  - ATR 週期: 14
  - ATR 倍數: 2.0
  - Rebalance 閾值: 0.5

✓ 使用 ATR 策略計算區間:
  - ATR: 1234.56
  - 價格區間: 118859.70 ~ 121328.82 USDC

[Rebalance #1] 時間: 1752791702
  當前價格: 122000.00 USDC
  ATR: 1250.00
  新區間: 119500.00 ~ 124500.00 USDC

回測完成！
  - Rebalance 次數: 15
  - 總收益率: 12.34%
```

## 注意事項

1. **ATR 初始化**：需要至少 `atr_period` 個價格點才能計算 ATR
2. **Rebalance 成本**：每次 rebalance 會產生 Gas 費用（模擬中未考慮）
3. **參數調優**：根據市場情況調整 `atr_multiplier` 和 `rebalance_threshold`

