# 關鍵 Bug 分析

## 問題 1: sqrt_price 計算不一致（每次運行差 10 倍）

### 根本原因
- `tick_to_sqrt_price` 返回的是 `sqrt(1.0001^tick * PRICE_SCALE)` = 346.54
- 但從 `sqrtPriceX96` 計算的是 `sqrt(price * PRICE_SCALE)` = 3465.46
- 兩者差了 `sqrt(PRICE_SCALE)` = 10 倍

### 正確的理解
在 Uniswap V3 中：
- `price = 1.0001^tick`（對於 WBTC/USDC，需要考慮 decimals）
- 對於 WBTC/USDC: `price = 1.0001^tick * PRICE_SCALE`（因為 WBTC 8 decimals, USDC 6 decimals）
- `sqrtPriceX96 = sqrt(price * PRICE_SCALE) * 2^96`
- 所以 `sqrt_price = sqrtPriceX96 / 2^96 = sqrt(price * PRICE_SCALE)`

但 `tick_to_sqrt_price` 計算的是：
- `price_from_tick = 1.0001^tick`
- `sqrt_price = sqrt(price_from_tick * PRICE_SCALE) = sqrt(1.0001^tick * PRICE_SCALE)`

這與 `sqrt(price * PRICE_SCALE)` 不同，因為 `price = 1.0001^tick * PRICE_SCALE`，所以：
- `sqrt(price * PRICE_SCALE) = sqrt(1.0001^tick * PRICE_SCALE * PRICE_SCALE) = sqrt(1.0001^tick) * PRICE_SCALE`

### 修復方案
統一使用從 `sqrtPriceX96` 計算的值，或者修正 `tick_to_sqrt_price` 的實現。

## 問題 2: 手續費計算錯誤（從 $10,000 產生數十億美元）

### 根本原因
1. **使用事件中的 liquidity 值**：事件中的 `liquidity` 可能不準確或很小
2. **fee_growth_delta 計算**：`fee_growth_delta = (fee_amount * Q128) // liquidity`
   - 如果 `liquidity` 很小，`fee_growth_delta` 會非常大
   - 導致 `tokens_owed` 爆炸

### 正確的做法
- 使用池子的實際流動性（`pool_state.liquidity`），而不是事件中的值
- 如果池子流動性為 0 或太小，跳過手續費計算

### 修復方案
```python
# 使用池子的實際流動性
pool_liquidity = self.pool_state.liquidity if self.pool_state.liquidity > 0 else liquidity

# 如果池子流動性為 0 或太小，跳過手續費計算
if pool_liquidity > 0:
    fee_growth_delta = (fee_amount * Q128) // pool_liquidity
```

## 問題 3: 累積了所有歷史手續費

### 根本原因
- 雖然我們記錄了位置創建時的 `fee_growth_global`，但如果在位置創建時 `fee_growth_global` 已經很大，會導致問題
- 或者 `_update_position_fees` 被調用太頻繁，導致重複計算

### 修復方案
- 確保只在位置創建時記錄 `fee_growth_global`
- 確保 `_update_position_fees` 只計算增量，不重複累積

## 建議的修復順序

1. **先修復手續費計算**（最嚴重）
   - 使用池子的實際流動性
   - 添加保護：如果流動性太小，跳過計算

2. **統一 sqrt_price 計算**
   - 統一使用從 `sqrtPriceX96` 計算的值
   - 或者修正 `tick_to_sqrt_price` 的實現

3. **驗證手續費累積邏輯**
   - 確保只計算從位置創建開始的增量
   - 添加調試輸出，檢查手續費值是否合理

