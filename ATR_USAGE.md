# ATR 策略使用說明（已修復）

## 修復內容

1. **定期 Rebalance**：改為每 3 分鐘（180秒）定期檢查並 rebalance，而不是基於價格偏離
2. **手續費模擬**：每次 rebalance 扣除 0.1% 的手續費（模擬 Gas 費用）
3. **流動性計算**：修正了流動性計算公式，使用正確的 Uniswap V3 公式
4. **價格範圍顯示**：修正了價格範圍的計算和顯示

## 使用方法

### 基本使用（每 3 分鐘 rebalance）

```bash
cd src
python main.py --data ../data/wbtc_usdc_pool_events.jsonl --capital 10000 --use-atr
```

### 自定義 rebalance 間隔

```bash
# 每 5 分鐘 rebalance
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --use-atr \
  --rebalance-interval 300

# 每 1 分鐘 rebalance（更頻繁）
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --use-atr \
  --rebalance-interval 60
```

### 自定義 ATR 參數

```bash
python main.py \
  --data ../data/wbtc_usdc_pool_events.jsonl \
  --capital 10000 \
  --use-atr \
  --atr-period 20 \
  --atr-multiplier 1.5 \
  --rebalance-interval 180
```

## 策略行為

1. **初始位置**：等待 ATR 數據足夠後，使用 ATR 計算初始價格區間並創建 LP 位置
2. **定期檢查**：每 3 分鐘（或指定間隔）檢查是否需要 rebalance
3. **Rebalance 過程**：
   - 移除當前 LP 位置
   - 提取累積的手續費
   - 扣除 rebalance 手續費（0.1%）
   - 根據當前價格和 ATR 計算新區間
   - 在新區間內創建新的 LP 位置

## 輸出示例

```
策略: ATR 動態區間回測（定期再平衡）
  - ATR 週期: 14
  - ATR 倍數: 2.0
  - 再平衡間隔: 180 秒 (3 分鐘)

✓ 創建初始 LP 位置:
  - 投入資金: 10000.00 USDC
  - 分配: 0.041234 WBTC + 5000.00 USDC
  - 價格區間: 118859.70 ~ 121328.82 USDC
  - Tick 範圍: 70380 ~ 71400
  - 當前價格: 120094.26 USDC (tick: 70912)
  - ATR: 1234.56 USDC

[Rebalance #1] 時間: 1752790882
  當前價格: 120125.32 USDC
  ATR: 1250.00
  新區間: 117625.32 ~ 122625.32 USDC (tick: 70320 ~ 71520)
  提取價值: 10045.23 USDC
  累積手續費: 12.34 USDC
  Rebalance 手續費: 10.06 USDC (0.1%)
  可用資金: 10047.51 USDC

回測完成！
  - Rebalance 次數: 15
  - 總收益率: 12.34%
```

## 注意事項

1. **Rebalance 手續費**：每次 rebalance 會扣除 0.1% 的手續費（模擬 Gas 費用）
2. **ATR 初始化**：需要至少 `atr_period` 個價格點才能計算 ATR
3. **頻繁 Rebalance**：更頻繁的 rebalance 會產生更多手續費成本，需要平衡收益和成本

