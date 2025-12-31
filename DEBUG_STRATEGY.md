# 回測策略調試說明

## 當前問題分析

從回測結果看到異常數據：
- **最終價值**: 416,898,260,082.97 USDC（從 10,000 開始）
- **總收益率**: 4,168,982,500.83%（異常高）
- **總手續費收入**: -2,417,487.08 USDC（負數，異常）
- **最大回撤**: 4,464.67%（異常高）

## 當前回測策略

### 問題：追蹤所有歷史 LP 位置

目前的代碼在 `backtest_engine.py` 中：

```python
def _process_mint(self, event: Dict):
    # ...
    if position.owner:
        self.positions.append(position)  # 追蹤所有歷史位置
```

**這意味著**：
1. 系統追蹤了池子中**所有歷史上的 Mint 事件**
2. 將所有這些 LP 位置都加入到投資組合中
3. 計算所有這些位置的總價值

**這不是一個合理的回測策略**，因為：
- 它累積了所有歷史 LP 的總價值，而不是模擬一個特定策略
- 初始資金只有 10,000 USDC，但計算了數百萬個歷史位置的價值
- 導致價值異常膨脹

## 應該實現的策略

### 策略 1：被動持有策略（Passive Hold）
- 在回測開始時，用初始資金創建一個 LP 位置
- 持有到回測結束
- 計算這個單一位置的收益

### 策略 2：跟隨策略（Follow Strategy）
- 選擇一個特定的 LP 地址
- 跟隨這個地址的所有 Mint/Burn 操作
- 計算這個地址的收益

### 策略 3：時間加權策略（Time-Weighted）
- 在特定時間點添加流動性
- 在特定條件下移除流動性
- 模擬實際的 LP 管理策略

## 修復建議

需要修改 `backtest_engine.py` 來實現一個合理的策略：

1. **不要追蹤所有歷史位置**，而是：
   - 在回測開始時創建一個初始 LP 位置
   - 或者選擇一個特定的地址/策略來跟隨

2. **初始資金分配**：
   - 用初始資金（10,000 USDC）創建 LP 位置
   - 根據當前價格計算應該投入的 WBTC 和 USDC 數量

3. **位置管理**：
   - 只在策略明確的時機添加/移除流動性
   - 不要自動追蹤所有歷史事件

## 當前代碼的問題

```python
# 問題代碼：追蹤所有歷史位置
def _process_mint(self, event: Dict):
    # ...
    if position.owner:
        self.positions.append(position)  # ❌ 這會累積所有歷史位置
```

應該改為：
```python
# 正確做法：只追蹤策略相關的位置
def _process_mint(self, event: Dict):
    # 只處理符合策略條件的 Mint
    if self._should_track_position(event):
        position = self.amm.add_liquidity(...)
        self.positions.append(position)
```

## 下一步

需要實現一個明確的回測策略，例如：
- 在回測開始時用初始資金創建 LP 位置
- 選擇合適的價格範圍（tick range）
- 持有到結束或特定退出條件

