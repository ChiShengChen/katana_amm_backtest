# 回測邏輯問題修復總結

## 問題 1：手續費收入異常高（782254422.90 USDC）

### 根本原因
- `_get_fee_growth_inside` 返回的是 `fee_growth_global`（所有歷史累積的手續費）
- 當新位置創建時，如果價格在範圍內，`fee_growth_inside` 被設置為當前的 `fee_growth_global`
- 這意味著新位置會立即獲得所有歷史手續費，這是錯誤的

### 修復方案
1. **修改 `_get_fee_growth_inside`**：
   - 添加 `fee_growth_global_at_creation` 參數
   - 只計算從位置創建開始累積的手續費（增量）

2. **修改 `add_liquidity`**：
   - 記錄位置創建時的 `fee_growth_global`（作為基準）
   - 新位置的 `fee_growth_inside0` 和 `fee_growth_inside1` 設置為創建時的 `fee_growth_global`

3. **修改 `_update_position_fees`**：
   - 使用位置創建時的 `fee_growth_global` 作為基準
   - 只計算從創建開始的增量手續費

### 預期效果
- 手續費收入應該大幅降低，只反映策略位置實際賺取的手續費
- 第一次 rebalance 時的手續費應該接近 0（因為位置剛創建）

## 問題 2：無常損失（IL）為 0

### 根本原因
- `performance_analyzer.py` 中沒有計算 IL
- 沒有記錄初始投入的 token 數量和價格

### 修復方案
1. **在 `BacktestEngine` 中記錄初始投入信息**：
   - `initial_price`：初始價格
   - `initial_wbtc_amount`：初始 WBTC 數量
   - `initial_usdc_amount`：初始 USDC 數量

2. **在回測結束時計算 IL**：
   - 計算 HODL 價值：`initial_wbtc_amount * final_price + initial_usdc_amount`
   - 計算 LP 價值：`final_value - total_fees`（只計算 token 價值，不包括手續費）
   - IL = `(LP價值 - HODL價值) / HODL價值 * 100`

3. **傳遞 IL 到 `PerformanceAnalyzer`**：
   - 在 `analyze_performance` 中添加 `impermanent_loss` 參數

### 預期效果
- IL 應該顯示負值（因為價格從 120094.15 降到 96105.64）
- IL 應該反映相對於 HODL 的損失

## 問題 3：數據是否足夠模擬用戶與LP的互動

### 當前狀態
- ✅ 處理 Swap、Mint、Burn 事件
- ✅ 從 Swap 事件中提取真實的價格和交易量
- ✅ 計算手續費並分配到 LP 位置

### 潛在問題
1. **手續費分配邏輯**：
   - 簡化的 `_get_fee_growth_inside` 實現
   - 沒有考慮 tick 範圍外的 feeGrowthOutside
   - 只有當價格在範圍內時才累積手續費

2. **流動性深度**：
   - 使用事件中的 `liquidity` 字段
   - 但可能不完整或不準確

3. **Slippage**：
   - 目前未模擬
   - 假設按當前價格成交

### 建議
- 重新運行回測，驗證修復效果
- 如果手續費仍然異常，需要進一步檢查 `_update_position_fees` 的邏輯
- 考慮實現更完整的 Uniswap V3 fee growth 計算（包括 tick 範圍外的處理）

## 修復的文件

1. `src/amm_simulator.py`：
   - `_get_fee_growth_inside`：添加 `fee_growth_global_at_creation` 參數
   - `add_liquidity`：記錄位置創建時的 `fee_growth_global`
   - `_update_position_fees`：修復手續費累積邏輯

2. `src/backtest_engine.py`：
   - 添加初始投入信息記錄（`initial_price`, `initial_wbtc_amount`, `initial_usdc_amount`）
   - 在回測結束時計算 IL
   - 傳遞 IL 到 `PerformanceAnalyzer`

3. `src/performance_analyzer.py`：
   - `analyze_performance`：添加 `impermanent_loss` 參數
   - 保存 IL 到 metrics

## 下一步

1. 重新運行回測，查看修復效果
2. 如果手續費仍然異常，需要進一步調試 `_update_position_fees` 的邏輯
3. 驗證 IL 計算是否正確（應該為負值）

