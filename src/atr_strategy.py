"""
ATR (Average True Range) 策略模組
用於動態計算 LP 價格區間和 rebalancing
"""
import math
from typing import List, Tuple, Optional
from collections import deque


class ATRStrategy:
    """基於 ATR 的 LP 區間策略"""
    
    def __init__(
        self,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        rebalance_interval: int = 180  # Rebalance 檢查間隔（秒，默認 180 = 3分鐘）
    ):
        """
        Args:
            atr_period: ATR 計算週期（默認 14）
            atr_multiplier: ATR 倍數，用於計算價格區間（默認 2.0，即 ±2*ATR）
            rebalance_interval: Rebalance 檢查間隔（秒，默認 180 = 3分鐘）
        """
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.rebalance_interval = rebalance_interval
        
        # ATR 計算相關
        self.price_history: deque = deque(maxlen=atr_period + 1)
        self.high_history: deque = deque(maxlen=atr_period + 1)
        self.low_history: deque = deque(maxlen=atr_period + 1)
        self.true_ranges: deque = deque(maxlen=atr_period)
        self.atr: float = 0.0
        
        # Rebalance 追蹤
        self.last_rebalance_time: Optional[int] = None
        self.current_range_center: Optional[float] = None
        self.current_range_lower: Optional[float] = None
        self.current_range_upper: Optional[float] = None
        
    def update_price(self, price: float, high: Optional[float] = None, low: Optional[float] = None, timestamp: int = 0):
        """更新價格數據並計算 ATR"""
        if high is None:
            high = price
        if low is None:
            low = price
        
        self.price_history.append(price)
        self.high_history.append(high)
        self.low_history.append(low)
        
        # 計算 True Range
        if len(self.price_history) >= 2:
            prev_close = self.price_history[-2]
            tr = max(
                high - low,  # 當日高低差
                abs(high - prev_close),  # 當日高 - 前收
                abs(low - prev_close)  # 當日低 - 前收
            )
            self.true_ranges.append(tr)
        
        # 計算 ATR（簡單移動平均）
        if len(self.true_ranges) >= self.atr_period:
            self.atr = sum(self.true_ranges) / len(self.true_ranges)
    
    def calculate_range(self, current_price: float, tick_spacing: int = 60) -> Tuple[int, int, float, float]:
        """根據 ATR 計算 LP 價格區間
        
        返回: (tick_lower, tick_upper, price_lower, price_upper)
        """
        # 最小範圍：至少 ±2% 的價格範圍
        min_range_pct = 0.02
        min_range_size = current_price * min_range_pct
        
        if self.atr <= 0:
            # ATR 未就緒，使用默認範圍（±5%）
            range_pct = 0.05
            price_lower = current_price * (1 - range_pct)
            price_upper = current_price * (1 + range_pct)
        else:
            # 使用 ATR 計算範圍
            range_size = self.atr * self.atr_multiplier
            
            # 確保範圍不會太窄（至少 ±2%）
            range_size = max(range_size, min_range_size)
            
            price_lower = current_price - range_size
            price_upper = current_price + range_size
            
            # 確保價格為正
            price_lower = max(price_lower, current_price * 0.1)
        
        # 轉換為 tick
        tick_lower = self._price_to_tick(price_lower, tick_spacing)
        tick_upper = self._price_to_tick(price_upper, tick_spacing)
        
        # 更新當前範圍
        self.current_range_center = current_price
        self.current_range_lower = price_lower
        self.current_range_upper = price_upper
        
        return (tick_lower, tick_upper, price_lower, price_upper)
    
    def _price_to_tick(self, price: float, tick_spacing: int) -> int:
        """將價格轉換為 tick（對齊到 tick_spacing）"""
        # price = 1.0001^tick * (10^8 / 10^6) = 1.0001^tick * 10^2
        # 對於 WBTC/USDC，需要考慮小數位數
        # 簡化：tick = log(price / 10^2) / log(1.0001)
        try:
            tick = int(math.log(price / (10 ** 2)) / math.log(1.0001))
            # 對齊到 tick_spacing
            tick = (tick // tick_spacing) * tick_spacing
            return tick
        except (ValueError, OverflowError):
            return 0
    
    def should_rebalance(self, current_price: float, timestamp: int) -> bool:
        """判斷是否需要 rebalance
        
        條件（必須同時滿足）：
        1. ATR 已就緒 或 是第一次 rebalance
        2. 已經過了 rebalance 間隔
        3. 價格偏離範圍中心超過閾值（20% 的範圍寬度）
        """
        # 如果 ATR 未就緒，不應該 rebalance（除非是第一次）
        if self.atr <= 0 and self.last_rebalance_time is not None:
            return False
        
        # 如果還沒有 rebalance 過，需要初始化
        if self.last_rebalance_time is None:
            return True
        
        # 檢查是否達到 rebalance 間隔
        if timestamp - self.last_rebalance_time < self.rebalance_interval:
            return False
        
        # 檢查價格是否偏離範圍中心足夠多
        # 只有當價格接近或超出範圍邊界時才 rebalance
        if self.current_range_lower is not None and self.current_range_upper is not None:
            range_width = self.current_range_upper - self.current_range_lower
            if range_width > 0:
                # 計算價格距離最近邊界的距離
                dist_to_lower = current_price - self.current_range_lower
                dist_to_upper = self.current_range_upper - current_price
                min_dist = min(dist_to_lower, dist_to_upper)
                
                # 如果價格距離邊界小於範圍寬度的 20%，才 rebalance
                # 即價格接近邊界或已經超出範圍
                if min_dist > range_width * 0.2:
                    return False  # 價格在安全區域內，不需要 rebalance
        
        return True
    
    def record_rebalance(self, timestamp: int):
        """記錄 rebalance 時間"""
        self.last_rebalance_time = timestamp
    
    def get_atr(self) -> float:
        """獲取當前 ATR 值"""
        return self.atr
    
    def get_current_range(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """獲取當前價格區間"""
        return (self.current_range_lower, self.current_range_upper, self.current_range_center)
