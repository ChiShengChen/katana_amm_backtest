# 完整修復指南

## 問題總結

1. **sqrt_price 每次運行差 10 倍** - 單位不一致
2. **手續費收入為 0** - 手續費累積邏輯有問題
3. **最終價值回到 10000** - 已部分修復，但需要確保 available_capital 正確更新

## 核心原則

### sqrt_price 計算（必須統一）

```python
# ✅ 正確的方式
sqrt_price = float(sqrtPriceX96) / (2 ** 96)  # 從 sqrtPriceX96
sqrt_price = tick_to_sqrt_price(tick)          # 從 tick
sqrt_price = math.sqrt(display_price / PRICE_SCALE)  # 從價格（驗證用）

# ❌ 錯誤的方式
sqrt_price = tick_to_sqrt_price(tick) * math.sqrt(PRICE_SCALE)  # 不要！
sqrt_price = sqrt_price * 10  # 不要！
```

### 驗證 sqrt_price 一致性

在所有關鍵位置添加驗證：

```python
if self.amm.pool_state:
    sqrt_price_from_x96 = float(self.amm.pool_state.sqrt_price_x96) / (2 ** 96)
    sqrt_price_from_tick = tick_to_sqrt_price(current_tick)
    
    if abs(sqrt_price_from_x96 - sqrt_price_from_tick) > 0.1:
        print(f"⚠️ sqrt_price 不一致!")
        print(f"  從 sqrtPriceX96: {sqrt_price_from_x96:.6f}")
        print(f"  從 tick: {sqrt_price_from_tick:.6f}")
        print(f"  差異: {abs(sqrt_price_from_x96 - sqrt_price_from_tick):.6f}")
    
    sqrt_price_current = sqrt_price_from_x96  # 優先使用從 sqrtPriceX96 計算的值
else:
    sqrt_price_current = tick_to_sqrt_price(current_tick)
```

## 關鍵函數修正

### 1. `_create_initial_position` - 添加驗證

在計算 sqrt_price 後立即驗證：

```python
# 計算 sqrt prices
if self.amm.pool_state:
    sqrt_price_from_x96 = float(self.amm.pool_state.sqrt_price_x96) / (2 ** 96)
    sqrt_price_from_tick = tick_to_sqrt_price(current_tick)
    
    # 驗證一致性
    if verbose and abs(sqrt_price_from_x96 - sqrt_price_from_tick) > 0.1:
        print(f"⚠️ DEBUG: sqrt_price 不一致!")
        print(f"  - 從 sqrtPriceX96: {sqrt_price_from_x96:.6f}")
        print(f"  - 從 tick: {sqrt_price_from_tick:.6f}")
        print(f"  - 差異: {abs(sqrt_price_from_x96 - sqrt_price_from_tick):.6f}")
    
    sqrt_price_current = sqrt_price_from_x96  # 優先使用從 sqrtPriceX96 計算的值
else:
    sqrt_price_current = tick_to_sqrt_price(current_tick)

sqrt_price_lower = tick_to_sqrt_price(tick_lower)
sqrt_price_upper = tick_to_sqrt_price(tick_upper)
```

### 2. `_rebalance_position` - 確保 available_capital 正確更新

```python
# 在 rebalance 結束時，確保 available_capital 正確更新
self.available_capital = available_capital_after_fee

# 如果創建位置失敗，available_capital 應該保持為 available_capital_after_fee
# 如果創建位置成功，available_capital 應該在 _create_lp_position 中設為 0
```

### 3. `_create_lp_position` - 添加驗證並確保 available_capital 更新

```python
# 計算 sqrt prices
if self.amm.pool_state:
    sqrt_price_from_x96 = float(self.amm.pool_state.sqrt_price_x96) / (2 ** 96)
    sqrt_price_from_tick = tick_to_sqrt_price(current_tick)
    
    # 驗證一致性
    if abs(sqrt_price_from_x96 - sqrt_price_from_tick) > 0.1:
        if verbose:
            print(f"⚠️ DEBUG: sqrt_price 不一致!")
            print(f"  - 從 sqrtPriceX96: {sqrt_price_from_x96:.6f}")
            print(f"  - 從 tick: {sqrt_price_from_tick:.6f}")
    
    sqrt_price_current = sqrt_price_from_x96
else:
    sqrt_price_current = tick_to_sqrt_price(current_tick)

sqrt_price_lower = tick_to_sqrt_price(tick_lower)
sqrt_price_upper = tick_to_sqrt_price(tick_upper)

# ... 創建位置 ...

if liquidity > 0:
    position = self.amm.add_liquidity(...)
    self.positions.append(position)
    self.available_capital = 0.0  # 資金已投入位置
else:
    # 如果創建失敗，available_capital 保持不變（已在 _rebalance_position 中設置）
    if verbose:
        print(f"⚠️ 警告：無法創建位置（流動性為 0）")
```

### 4. 手續費累積調試

在 `_update_position_fees` 中添加調試輸出：

```python
def _update_position_fees(self):
    """更新所有 LP 位置的累積手續費"""
    if not self.pool_state:
        return
    
    for owner, positions in self.pool_state.positions.items():
        for pos in positions:
            if pos.liquidity > 0:
                current_tick = self.pool_state.tick
                if pos.tick_lower <= current_tick < pos.tick_upper:
                    # 價格在範圍內
                    current_global0 = self.pool_state.fee_growth_global0
                    current_global1 = self.pool_state.fee_growth_global1
                    
                    fee_growth_delta0 = current_global0 - pos.fee_growth_inside0
                    fee_growth_delta1 = current_global1 - pos.fee_growth_inside1
                    
                    # DEBUG: 添加調試輸出（只在第一次或重要變化時）
                    if fee_growth_delta0 > 0 or fee_growth_delta1 > 0:
                        Q128 = 2 ** 128
                        tokens_owed0_delta = (pos.liquidity * fee_growth_delta0) // Q128
                        tokens_owed1_delta = (pos.liquidity * fee_growth_delta1) // Q128
                        
                        # 只在有明顯變化時輸出
                        if tokens_owed0_delta > 1000 or tokens_owed1_delta > 1000:
                            print(f"DEBUG: 手續費累積")
                            print(f"  fee_growth_delta0: {fee_growth_delta0}")
                            print(f"  fee_growth_delta1: {fee_growth_delta1}")
                            print(f"  tokens_owed0_delta: {tokens_owed0_delta}")
                            print(f"  tokens_owed1_delta: {tokens_owed1_delta}")
                        
                        pos.tokens_owed0 += tokens_owed0_delta
                        pos.tokens_owed1 += tokens_owed1_delta
                        
                        pos.fee_growth_inside0 = current_global0
                        pos.fee_growth_inside1 = current_global1
                else:
                    # 價格在範圍外，不累積手續費
                    # DEBUG: 可以添加輸出說明為什麼沒有累積手續費
                    pass
```

## 檢查清單

- [ ] 所有 `sqrt_price` 計算都使用統一的方式
- [ ] 在所有關鍵位置添加 `sqrt_price` 一致性驗證
- [ ] 確保 `available_capital` 在所有路徑都正確更新
- [ ] 添加手續費累積的調試輸出
- [ ] 驗證 `fee_growth_delta` 計算正確（pool_liquidity 單位問題）

## 測試方法

運行回測後檢查：
1. `sqrt_price_current` 應該穩定在 ~34.65（不再每次運行變 10 倍）
2. 手續費收入應該 > 0（有實際的手續費累積）
3. 最終價值應該反映實際的可用資金（不是 10000）

