# sqrt_price 統一修復方案

## 核心原則

在 Uniswap V3 中：
- `price = 1.0001^tick`（不考慮 decimals）
- `sqrtPriceX96 = sqrt(price) * 2^96`
- 對於顯示：`display_price = price * PRICE_SCALE`

所以：
- `sqrt_price = sqrtPriceX96 / 2^96 = sqrt(1.0001^tick)`
- `tick_to_sqrt_price(tick)` 應該返回 `sqrt(1.0001^tick)`

## 所有使用 sqrt_price 的地方必須統一

### 1. 從 sqrtPriceX96 計算
```python
sqrt_price = float(sqrtPriceX96) / (2 ** 96)
```

### 2. 從 tick 計算
```python
sqrt_price = tick_to_sqrt_price(tick)  # 已經返回 sqrt(1.0001^tick)
```

### 3. 從價格計算（用於驗證）
```python
price_ratio = display_price / PRICE_SCALE
sqrt_price = math.sqrt(price_ratio)
```

## 禁止的操作

❌ **不要** 乘以 `sqrt(PRICE_SCALE)`
❌ **不要** 除以 `sqrt(PRICE_SCALE)`
❌ **不要** 在 `tick_to_sqrt_price` 中乘以 `PRICE_SCALE`

## 驗證方法

```python
# 這三個值應該相等（誤差 < 0.01）
sqrt_price_from_x96 = float(sqrtPriceX96) / (2 ** 96)
sqrt_price_from_tick = tick_to_sqrt_price(current_tick)
sqrt_price_from_price = math.sqrt(current_price / PRICE_SCALE)

assert abs(sqrt_price_from_x96 - sqrt_price_from_tick) < 0.01
assert abs(sqrt_price_from_x96 - sqrt_price_from_price) < 0.01
```

