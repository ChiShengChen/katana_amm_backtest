"""
回測引擎：執行完整的回測流程

關鍵修復：
1. 正確處理 liquidity 單位
2. 防止負數 token 分配
3. 修復資金快速歸零問題
4. 統一 sqrt_price 處理
"""
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    from .amm_simulator import AMMSimulator, LiquidityPosition
    from .event_processor import EventProcessor
    from .performance_analyzer import PerformanceAnalyzer, PerformanceMetrics
    from .atr_strategy import ATRStrategy
    from .uniswap_v3_math import (
        tick_to_sqrt_price, sqrt_price_to_price,
        get_amounts_from_liquidity, get_liquidity_from_amounts,
        PRICE_SCALE, TOKEN0_DECIMALS, TOKEN1_DECIMALS
    )
except ImportError:
    from amm_simulator import AMMSimulator, LiquidityPosition
    from event_processor import EventProcessor
    from performance_analyzer import PerformanceAnalyzer, PerformanceMetrics
    from atr_strategy import ATRStrategy
    from uniswap_v3_math import (
        tick_to_sqrt_price, sqrt_price_to_price,
        get_amounts_from_liquidity, get_liquidity_from_amounts,
        PRICE_SCALE, TOKEN0_DECIMALS, TOKEN1_DECIMALS
    )


class BacktestEngine:
    """回測引擎"""
    
    def __init__(
        self,
        data_file: str,
        initial_capital: float = 10000.0,
        fee_tier: int = 3000
    ):
        self.data_file = data_file
        self.initial_capital = initial_capital
        self.event_processor = EventProcessor(data_file)
        self.amm = AMMSimulator(fee_tier=fee_tier)
        self.analyzer = PerformanceAnalyzer()
        
        # 回測狀態
        self.positions: List[LiquidityPosition] = []
        self.value_history: List[Tuple[int, float]] = []
        self.current_value: float = initial_capital
        self.total_fees_earned: float = 0.0
        
        # 用於 IL 計算
        self.initial_price: Optional[float] = None
        self.initial_wbtc_amount: float = 0.0
        self.initial_usdc_amount: float = 0.0
        
        # 策略配置
        self.initial_position_created: bool = False
        self.atr_strategy: Optional[ATRStrategy] = None
        self.rebalance_count: int = 0
        self.rebalance_history: List[Tuple[int, float, float, float]] = []
        self.use_atr_strategy: bool = False
        self.atr_range_history: List[Tuple[int, float, float, float, float]] = []
        
    def run_backtest(
        self,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        track_positions: bool = True,
        verbose: bool = True,
        tick_lower: Optional[int] = None,
        tick_upper: Optional[int] = None,
        price_range_pct: float = 0.10,
        use_atr_strategy: bool = False,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        rebalance_interval: int = 180
    ) -> PerformanceMetrics:
        """執行回測"""
        self.use_atr_strategy = use_atr_strategy
        
        if verbose:
            print("開始回測...")
            if use_atr_strategy:
                print("策略: ATR 動態區間回測（定期再平衡）")
                print(f"  - ATR 週期: {atr_period}")
                print(f"  - ATR 倍數: {atr_multiplier}")
                print(f"  - 再平衡間隔: {rebalance_interval} 秒 ({rebalance_interval // 60} 分鐘)")
            else:
                print("策略: LP 固定區間回測")
        
        if use_atr_strategy:
            self.atr_strategy = ATRStrategy(
                atr_period=atr_period,
                atr_multiplier=atr_multiplier,
                rebalance_interval=rebalance_interval
            )
        
        # 獲取事件
        events = list(self.event_processor.get_events_in_range(
            start_block=start_block,
            end_block=end_block,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp
        ))
        
        if not events:
            if verbose:
                print("警告：沒有找到符合條件的事件")
            return self.analyzer.metrics
        
        events.sort(key=lambda x: (
            x.get('blockTimestamp', 0),
            x.get('blockNumber', 0),
            x.get('logIndex', 0)
        ))
        
        if verbose:
            print(f"處理 {len(events)} 個事件...")
        
        first_event = events[0]
        start_ts = first_event.get('blockTimestamp', 0)
        end_ts = events[-1].get('blockTimestamp', start_ts)
        
        num_swaps = 0
        num_mints = 0
        num_burns = 0
        
        # 找第一個 Swap 來初始化
        for event in events:
            if event.get('eventType') == 'Swap':
                self._process_swap(event)
                break
        
        # 創建初始位置
        if self.amm.pool_state and not self.initial_position_created:
            current_price = self.amm.get_current_price()
            current_tick = self.amm.pool_state.tick
            
            if current_price > 0:
                if self.use_atr_strategy and self.atr_strategy:
                    self.atr_strategy.update_price(current_price, current_price, current_price, start_ts)
                    tick_spacing = 60
                    
                    # 使用較寬的初始範圍（±5%）
                    initial_range_pct = 0.05
                    tick_range = int(math.log(1 + initial_range_pct) / math.log(1.0001))
                    tick_range = max(tick_range, tick_spacing * 15)  # 至少 15 個 tick spacing
                    tick_range = (tick_range // tick_spacing) * tick_spacing
                    
                    tick_lower = current_tick - tick_range
                    tick_upper = current_tick + tick_range
                    
                    price_lower = self._tick_to_display_price(tick_lower)
                    price_upper = self._tick_to_display_price(tick_upper)
                    
                    self.atr_range_history.append((start_ts, current_price, 0.0, price_lower, price_upper))
                
                self._create_initial_position(
                    start_ts,
                    tick_lower=tick_lower,
                    tick_upper=tick_upper,
                    price_range_pct=price_range_pct,
                    verbose=verbose
                )
                
                if self.use_atr_strategy and self.atr_strategy:
                    self.atr_strategy.record_rebalance(start_ts)
        
        # 處理事件
        for i, event in enumerate(events):
            event_type = event.get('eventType')
            timestamp = event.get('blockTimestamp', 0)
            
            if event_type == 'Swap':
                num_swaps += 1
                self._process_swap(event)
                
                if self.use_atr_strategy and self.atr_strategy and self.initial_position_created:
                    current_price = self.amm.get_current_price()
                    if current_price > 0:
                        self.atr_strategy.update_price(current_price, current_price, current_price, timestamp)
                        
                        # 記錄 ATR 範圍
                        if i % 100 == 0:
                            atr_value = self.atr_strategy.get_atr()
                            tick_spacing = 60
                            if atr_value > 0:
                                _, _, price_lower, price_upper = self.atr_strategy.calculate_range(
                                    current_price, tick_spacing
                                )
                            else:
                                price_lower = current_price * 0.95
                                price_upper = current_price * 1.05
                            self.atr_range_history.append((timestamp, current_price, atr_value, price_lower, price_upper))
                        
                        # 檢查 rebalance
                        if self.atr_strategy.should_rebalance(current_price, timestamp):
                            self._rebalance_position(timestamp, verbose)
                            
            elif event_type == 'Mint':
                num_mints += 1
            elif event_type == 'Burn':
                num_burns += 1
            
            # 定期記錄價值
            if i % 100 == 0:
                current_price = self.amm.get_current_price()
                if current_price > 0:
                    value = self._calculate_portfolio_value(current_price)
                    self.value_history.append((timestamp, value))
                    self.current_value = value
        
        # 最終計算
        final_price = self.amm.get_current_price()
        final_value = self._calculate_portfolio_value(final_price)
        self.value_history.append((end_ts, final_value))
        
        if verbose:
            print(f"回測完成！")
            print(f"  - 處理了 {num_swaps} 個 Swap, {num_mints} 個 Mint, {num_burns} 個 Burn")
            print(f"  - 最終價格: {final_price:.2f} USDC")
            print(f"  - 最終價值: {final_value:.2f} USDC")
            print(f"  - 總收益率: {((final_value - self.initial_capital) / self.initial_capital * 100):.2f}%")
        
        # 計算 IL
        impermanent_loss = 0.0
        if self.initial_price and self.initial_price > 0 and final_price > 0:
            hodl_value = self.initial_wbtc_amount * final_price + self.initial_usdc_amount
            lp_value = final_value - self.total_fees_earned
            if hodl_value > 0:
                impermanent_loss = ((lp_value - hodl_value) / hodl_value) * 100
        
        metrics = self.analyzer.analyze_performance(
            initial_value=self.initial_capital,
            final_value=final_value,
            value_history=self.value_history,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            num_swaps=num_swaps,
            num_mints=num_mints,
            num_burns=num_burns,
            total_fees_earned=self.total_fees_earned,
            impermanent_loss=impermanent_loss
        )
        
        return metrics
    
    def _tick_to_display_price(self, tick: int) -> float:
        """將 tick 轉換為顯示價格"""
        try:
            raw_price = math.exp(tick * math.log(1.0001))
            return raw_price * PRICE_SCALE
        except (OverflowError, ValueError):
            return 0.0
    
    def _process_swap(self, event: Dict):
        """處理 Swap 事件"""
        sqrt_price_x96 = event.get('sqrtPriceX96')
        tick = event.get('tick')
        liquidity = event.get('liquidity', 0)
        timestamp = event.get('blockTimestamp', 0)
        
        if sqrt_price_x96 and tick is not None:
            self.amm.process_swap(
                amount0=event.get('amount0', 0),
                amount1=event.get('amount1', 0),
                sqrt_price_x96=sqrt_price_x96,
                tick=tick,
                liquidity=liquidity,
                timestamp=timestamp
            )
    
    def _calculate_portfolio_value(self, current_price: float) -> float:
        """計算投資組合價值
        
        注意：手續費會在 rebalance 時自動重新投入，所以這裡只需要計算
        位置價值 + 未提取的手續費
        """
        if not self.amm.pool_state:
            return self.initial_capital
        
        total_value = 0.0
        uncollected_fees = 0.0
        
        for position in self.positions:
            if position.liquidity > 0:
                _, value, fees = self.amm.calculate_position_value(position, current_price)
                total_value += value
                uncollected_fees += fees
        
        # 總價值 = 位置價值 + 未提取的手續費
        # 注意：已提取的手續費會在 rebalance 時重新投入，所以不需要單獨加
        return total_value + uncollected_fees
    
    def _rebalance_position(self, timestamp: int, verbose: bool = True):
        """執行 rebalance"""
        if not self.amm.pool_state or not self.positions:
            return
        
        current_price = self.amm.get_current_price()
        if current_price <= 0 or not self.atr_strategy:
            return
        
        atr_value = self.atr_strategy.get_atr()
        
        # ATR 未就緒時使用較寬的範圍
        tick_spacing = 60
        if atr_value <= 0:
            # 使用 ±3% 的範圍
            range_pct = 0.03
            tick_range = int(math.log(1 + range_pct) / math.log(1.0001))
            tick_range = max(tick_range, tick_spacing * 5)
            tick_range = (tick_range // tick_spacing) * tick_spacing
            
            current_tick = self.amm.pool_state.tick
            tick_lower = ((current_tick - tick_range) // tick_spacing) * tick_spacing
            tick_upper = ((current_tick + tick_range) // tick_spacing) * tick_spacing
            price_lower = self._tick_to_display_price(tick_lower)
            price_upper = self._tick_to_display_price(tick_upper)
        else:
            tick_lower, tick_upper, price_lower, price_upper = self.atr_strategy.calculate_range(
                current_price, tick_spacing
            )
        
        # 確保範圍不會太窄（至少 5 個 tick spacing）
        min_tick_range = tick_spacing * 5
        if tick_upper - tick_lower < min_tick_range:
            mid_tick = (tick_lower + tick_upper) // 2
            tick_lower = mid_tick - min_tick_range // 2
            tick_upper = mid_tick + min_tick_range // 2
            tick_lower = (tick_lower // tick_spacing) * tick_spacing
            tick_upper = (tick_upper // tick_spacing) * tick_spacing
            price_lower = self._tick_to_display_price(tick_lower)
            price_upper = self._tick_to_display_price(tick_upper)
        
        if verbose:
            print(f"\n[Rebalance #{self.rebalance_count + 1}] 時間: {timestamp}")
            print(f"  當前價格: {current_price:.2f} USDC")
            print(f"  ATR: {atr_value:.2f} USDC")
            print(f"  新區間: {price_lower:.2f} ~ {price_upper:.2f} USDC (tick: {tick_lower} ~ {tick_upper})")
        
        # 移除舊位置
        total_wbtc = 0.0
        total_usdc = 0.0
        total_fees_wbtc = 0.0
        total_fees_usdc = 0.0
        
        for position in list(self.positions):
            if position.liquidity > 0:
                amount0, amount1, fee0, fee1 = self.amm.remove_liquidity(
                    owner=position.owner,
                    tick_lower=position.tick_lower,
                    tick_upper=position.tick_upper,
                    liquidity=position.liquidity
                )
                
                total_wbtc += float(amount0) / (10 ** TOKEN0_DECIMALS)
                total_usdc += float(amount1) / (10 ** TOKEN1_DECIMALS)
                total_fees_wbtc += float(fee0) / (10 ** TOKEN0_DECIMALS)
                total_fees_usdc += float(fee1) / (10 ** TOKEN1_DECIMALS)
        
        self.positions.clear()
        
        # 計算可用資金（流動性 + 手續費）
        token_value = total_wbtc * current_price + total_usdc
        fees_value = total_fees_wbtc * current_price + total_fees_usdc
        total_value = token_value + fees_value  # 手續費也應該被重新投入
        
        # 追蹤累積手續費（僅用於報告）
        self.total_fees_earned += fees_value
        
        # 模擬 gas 費用 (0.01%)
        gas_fee = total_value * 0.0001
        available_capital = total_value - gas_fee
        
        if verbose:
            print(f"  提取: {total_wbtc:.6f} WBTC + {total_usdc:.2f} USDC")
            print(f"  Token 價值: {token_value:.2f} USDC")
            print(f"  手續費: {fees_value:.2f} USDC")
            print(f"  總價值: {total_value:.2f} USDC")
            print(f"  Gas 費用: {gas_fee:.4f} USDC (0.01%)")
            print(f"  可用資金: {available_capital:.2f} USDC")
        
        # 創建新位置
        if available_capital > 10:  # 最小資金閾值
            self._create_lp_position(
                timestamp=timestamp,
                tick_lower=tick_lower,
                tick_upper=tick_upper,
                capital=available_capital,
                verbose=False
            )
        
        self.atr_strategy.record_rebalance(timestamp)
        self.rebalance_count += 1
        self.rebalance_history.append((timestamp, current_price, price_lower, price_upper))
    
    def _create_lp_position(
        self,
        timestamp: int,
        tick_lower: int,
        tick_upper: int,
        capital: float,
        verbose: bool = True
    ):
        """創建 LP 位置"""
        if not self.amm.pool_state:
            return
        
        current_price = self.amm.get_current_price()
        current_tick = self.amm.pool_state.tick
        
        if current_price <= 0:
            return
        
        # 計算 sqrt prices
        sqrt_price_current = self.amm.get_sqrt_price()
        sqrt_price_lower = tick_to_sqrt_price(tick_lower)
        sqrt_price_upper = tick_to_sqrt_price(tick_upper)
        
        price_lower = self._tick_to_display_price(tick_lower)
        price_upper = self._tick_to_display_price(tick_upper)
        
        # 根據價格位置分配資金
        if current_price < price_lower:
            # 全部 WBTC
            wbtc_amount = capital / current_price
            usdc_amount = 0.0
        elif current_price > price_upper:
            # 全部 USDC
            wbtc_amount = 0.0
            usdc_amount = capital
        else:
            # 在範圍內，按比例分配
            # 計算最優比例
            price_ratio = (current_price - price_lower) / (price_upper - price_lower)
            usdc_ratio = price_ratio
            wbtc_ratio = 1 - price_ratio
            
            usdc_amount = capital * usdc_ratio
            wbtc_amount = (capital * wbtc_ratio) / current_price
        
        # 轉換為合約單位
        amount0 = int(wbtc_amount * (10 ** TOKEN0_DECIMALS))
        amount1 = int(usdc_amount * (10 ** TOKEN1_DECIMALS))
        
        # 計算流動性
        liquidity = get_liquidity_from_amounts(
            amount0=amount0,
            amount1=amount1,
            sqrt_price_current=sqrt_price_current,
            sqrt_price_lower=sqrt_price_lower,
            sqrt_price_upper=sqrt_price_upper,
            current_tick=current_tick,
            tick_lower=tick_lower,
            tick_upper=tick_upper
        )
        
        if liquidity > 0:
            position = self.amm.add_liquidity(
                owner="backtest_lp_strategy",
                tick_lower=tick_lower,
                tick_upper=tick_upper,
                amount0=amount0,
                amount1=amount1,
                liquidity=liquidity,
                timestamp=timestamp
            )
            self.positions.append(position)
    
    def _create_initial_position(
        self,
        timestamp: int,
        tick_lower: Optional[int] = None,
        tick_upper: Optional[int] = None,
        price_range_pct: float = 0.10,
        verbose: bool = True
    ):
        """創建初始 LP 位置"""
        if not self.amm.pool_state:
            return
        
        current_price = self.amm.get_current_price()
        current_tick = self.amm.pool_state.tick
        tick_spacing = 60
        
        if current_price <= 0:
            return
        
        # 計算 tick 範圍
        if tick_lower is None or tick_upper is None:
            tick_range = int(math.log(1 + price_range_pct) / math.log(1.0001))
            tick_range = max(tick_range, tick_spacing * 10)
            tick_range = (tick_range // tick_spacing) * tick_spacing
            
            if tick_lower is None:
                tick_lower = current_tick - tick_range
            if tick_upper is None:
                tick_upper = current_tick + tick_range
        
        tick_lower = (tick_lower // tick_spacing) * tick_spacing
        tick_upper = (tick_upper // tick_spacing) * tick_spacing
        
        # 計算價格範圍
        price_lower = self._tick_to_display_price(tick_lower)
        price_upper = self._tick_to_display_price(tick_upper)
        
        # 計算 sqrt prices
        sqrt_price_current = self.amm.get_sqrt_price()
        sqrt_price_lower = tick_to_sqrt_price(tick_lower)
        sqrt_price_upper = tick_to_sqrt_price(tick_upper)
        
        # 根據價格位置分配資金
        if current_price < price_lower:
            wbtc_amount = self.initial_capital / current_price
            usdc_amount = 0.0
        elif current_price > price_upper:
            wbtc_amount = 0.0
            usdc_amount = self.initial_capital
        else:
            # 計算最優比例
            price_ratio = (current_price - price_lower) / (price_upper - price_lower)
            usdc_ratio = min(max(price_ratio, 0.1), 0.9)  # 限制在 10%-90%
            wbtc_ratio = 1 - usdc_ratio
            
            usdc_amount = self.initial_capital * usdc_ratio
            wbtc_amount = (self.initial_capital * wbtc_ratio) / current_price
        
        amount0 = int(wbtc_amount * (10 ** TOKEN0_DECIMALS))
        amount1 = int(usdc_amount * (10 ** TOKEN1_DECIMALS))
        
        # 計算流動性
        liquidity = get_liquidity_from_amounts(
            amount0=amount0,
            amount1=amount1,
            sqrt_price_current=sqrt_price_current,
            sqrt_price_lower=sqrt_price_lower,
            sqrt_price_upper=sqrt_price_upper,
            current_tick=current_tick,
            tick_lower=tick_lower,
            tick_upper=tick_upper
        )
        
        if liquidity > 0:
            position = self.amm.add_liquidity(
                owner="backtest_lp_strategy",
                tick_lower=tick_lower,
                tick_upper=tick_upper,
                amount0=amount0,
                amount1=amount1,
                liquidity=liquidity,
                timestamp=timestamp
            )
            self.positions.append(position)
            self.initial_position_created = True
            
            # 記錄初始信息（用於 IL 計算）
            self.initial_price = current_price
            self.initial_wbtc_amount = wbtc_amount
            self.initial_usdc_amount = usdc_amount
            
            if verbose:
                print(f"✓ 創建初始 LP 位置:")
                print(f"  - 投入資金: {self.initial_capital:.2f} USDC")
                print(f"  - 分配: {wbtc_amount:.6f} WBTC + {usdc_amount:.2f} USDC")
                print(f"  - 價格區間: {price_lower:.2f} ~ {price_upper:.2f} USDC")
                print(f"  - Tick 範圍: {tick_lower} ~ {tick_upper}")
                print(f"  - 當前價格: {current_price:.2f} USDC (tick: {current_tick})")
                print(f"  - 流動性: {liquidity}")
                print(f"  - sqrt_price: {sqrt_price_current:.6f}")
        else:
            if verbose:
                print(f"⚠ 警告：無法創建初始位置（流動性為 0）")
    
    def get_total_fees_earned(self) -> float:
        """獲取累積的手續費收入"""
        current_price = self.amm.get_current_price()
        total = self.total_fees_earned
        
        for position in self.positions:
            if position.liquidity > 0:
                fee_wbtc, fee_usdc = self.amm.get_position_fees(position)
                total += fee_wbtc * current_price + fee_usdc
        
        return total
    
    def get_price_history(self) -> List[Tuple[int, float]]:
        return self.amm.price_history
    
    def get_value_history(self) -> List[Tuple[int, float]]:
        return self.value_history
