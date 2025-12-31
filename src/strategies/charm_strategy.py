"""
Charm.fi Alpha Vault Strategy Implementation

Charm Alpha Vault uses a passive rebalancing approach that:
1. Never executes swaps - only uses limit orders
2. Maintains Base Order (symmetric) + Limit Order (one-sided)
3. Rebalances periodically (default 48 hours)

Key Features:
- Zero swap costs
- Lower gas costs
- Relies on market to fill limit orders
- Full Range Position (V2) for guaranteed liquidity
"""

from decimal import Decimal
from typing import List, Tuple, Optional
from dataclasses import dataclass

from .base_strategy import BaseAMMStrategy, Position, RebalanceResult
from .uniswap_math import (
    tick_to_sqrt_price_x96,
    get_liquidity_for_amounts,
    get_amounts_for_liquidity,
    align_tick_to_spacing
)


@dataclass
class CharmOrderConfig:
    """Configuration for Charm Alpha Vault orders"""
    base_threshold: int  # Ticks from current price for base order
    limit_threshold: int  # Ticks for limit order
    full_range_weight: float = 0.0  # Weight for full range position (V2)
    rebalance_interval: int = 172800  # 48 hours in seconds
    max_twap_deviation: int = 500  # Max allowed TWAP deviation in ticks


class CharmAlphaVaultStrategy(BaseAMMStrategy):
    """
    Charm Alpha Vault Passive Rebalancing Strategy
    
    Core Concepts:
    - Base Order: Symmetric range around current price, uses max balanced liquidity
    - Limit Order: One-sided order using surplus tokens
    - Full Range: V2-style position ensuring always-active liquidity (optional)
    
    Key Advantage:
    - NO SWAPS: Rebalances by adjusting positions, not trading
    - Limit orders passively wait for market to fill them
    """
    
    # Charm charges 2-5% protocol fee on earned swap fees
    PROTOCOL_FEE_MIN = 0.02
    PROTOCOL_FEE_MAX = 0.05
    
    def __init__(
        self,
        base_threshold: int = 600,  # ±600 ticks ≈ ±6%
        limit_threshold: int = 1200,  # 1200 ticks ≈ 12%
        full_range_weight: float = 0.0,
        rebalance_interval: int = 172800,  # 48 hours
        max_twap_deviation: int = 500,
        pool_fee: int = 3000,
        tick_spacing: int = 60,
        protocol_fee_rate: float = 0.02
    ):
        super().__init__(
            pool_fee=pool_fee,
            tick_spacing=tick_spacing,
            protocol_fee_rate=protocol_fee_rate
        )
        
        self.config = CharmOrderConfig(
            base_threshold=base_threshold,
            limit_threshold=limit_threshold,
            full_range_weight=full_range_weight,
            rebalance_interval=rebalance_interval,
            max_twap_deviation=max_twap_deviation
        )
        
        # Track limit order state
        self.limit_order_direction: Optional[str] = None  # 'buy' or 'sell'
        self.limit_order_filled: Decimal = Decimal('0')
        
        # TWAP tracking (simplified)
        self.twap_tick: int = 0
        self.twap_samples: List[int] = []
    
    @property
    def name(self) -> str:
        return "Charm Alpha Vault"
    
    def _update_twap(self, current_tick: int):
        """Update TWAP with new tick sample"""
        self.twap_samples.append(current_tick)
        # Keep last 12 samples (for ~1 hour TWAP with 5-min intervals)
        if len(self.twap_samples) > 12:
            self.twap_samples = self.twap_samples[-12:]
        self.twap_tick = sum(self.twap_samples) // len(self.twap_samples)
    
    def _calculate_base_order(
        self,
        current_tick: int,
        amount0: int,
        amount1: int
    ) -> Tuple[Position, int, int]:
        """
        Calculate Base Order (symmetric range around current price)
        
        Returns:
            Tuple of (position, remaining_amount0, remaining_amount1)
        """
        # Calculate range
        lower_tick = align_tick_to_spacing(
            current_tick - self.config.base_threshold,
            self.tick_spacing
        )
        upper_tick = align_tick_to_spacing(
            current_tick + self.config.base_threshold,
            self.tick_spacing
        )
        
        # Get sqrt prices
        sqrt_price_current = tick_to_sqrt_price_x96(current_tick)
        sqrt_price_lower = tick_to_sqrt_price_x96(lower_tick)
        sqrt_price_upper = tick_to_sqrt_price_x96(upper_tick)
        
        # Calculate max balanced liquidity
        liquidity = get_liquidity_for_amounts(
            sqrt_price_current,
            sqrt_price_lower,
            sqrt_price_upper,
            amount0,
            amount1
        )
        
        if liquidity == 0:
            return None, amount0, amount1
        
        # Calculate actual amounts used
        used_amount0, used_amount1 = get_amounts_for_liquidity(
            sqrt_price_current,
            sqrt_price_lower,
            sqrt_price_upper,
            liquidity
        )
        
        position = Position(
            lower_tick=lower_tick,
            upper_tick=upper_tick,
            liquidity=Decimal(liquidity),
            amount0=Decimal(used_amount0),
            amount1=Decimal(used_amount1),
            entry_tick=current_tick
        )
        
        remaining0 = amount0 - used_amount0
        remaining1 = amount1 - used_amount1
        
        return position, max(0, remaining0), max(0, remaining1)
    
    def _calculate_limit_order(
        self,
        current_tick: int,
        surplus0: int,
        surplus1: int
    ) -> Optional[Position]:
        """
        Calculate Limit Order using surplus tokens
        
        If surplus token0: Create sell order above current price
        If surplus token1: Create buy order below current price
        
        Returns:
            Limit order position or None
        """
        if surplus0 > 0 and surplus0 > surplus1:
            # Surplus token0 → sell order (above current price)
            lower_tick = align_tick_to_spacing(current_tick, self.tick_spacing)
            upper_tick = align_tick_to_spacing(
                current_tick + self.config.limit_threshold,
                self.tick_spacing
            )
            
            sqrt_price_lower = tick_to_sqrt_price_x96(lower_tick)
            sqrt_price_upper = tick_to_sqrt_price_x96(upper_tick)
            
            # For sell order (token0 only), calculate liquidity
            # When price is at lower bound, we only have token0
            liquidity = get_liquidity_for_amounts(
                sqrt_price_lower,  # Use lower price since we're selling
                sqrt_price_lower,
                sqrt_price_upper,
                surplus0,
                0
            )
            
            if liquidity > 0:
                self.limit_order_direction = 'sell'
                return Position(
                    lower_tick=lower_tick,
                    upper_tick=upper_tick,
                    liquidity=Decimal(liquidity),
                    amount0=Decimal(surplus0),
                    amount1=Decimal('0'),
                    entry_tick=current_tick
                )
        
        elif surplus1 > 0:
            # Surplus token1 → buy order (below current price)
            lower_tick = align_tick_to_spacing(
                current_tick - self.config.limit_threshold,
                self.tick_spacing
            )
            upper_tick = align_tick_to_spacing(current_tick, self.tick_spacing)
            
            sqrt_price_lower = tick_to_sqrt_price_x96(lower_tick)
            sqrt_price_upper = tick_to_sqrt_price_x96(upper_tick)
            
            # For buy order (token1 only), calculate liquidity
            liquidity = get_liquidity_for_amounts(
                sqrt_price_upper,  # Use upper price since we're buying
                sqrt_price_lower,
                sqrt_price_upper,
                0,
                surplus1
            )
            
            if liquidity > 0:
                self.limit_order_direction = 'buy'
                return Position(
                    lower_tick=lower_tick,
                    upper_tick=upper_tick,
                    liquidity=Decimal(liquidity),
                    amount0=Decimal('0'),
                    amount1=Decimal(surplus1),
                    entry_tick=current_tick
                )
        
        return None
    
    def initialize(
        self,
        initial_tick: int,
        amount0: Decimal,
        amount1: Decimal,
        timestamp: int
    ) -> List[Position]:
        """
        Initialize Charm Alpha Vault positions
        """
        self.last_rebalance_time = timestamp
        self._update_twap(initial_tick)
        
        positions = []
        remaining0 = int(amount0)
        remaining1 = int(amount1)
        
        # Full Range Position (if enabled)
        if self.config.full_range_weight > 0:
            fr_amount0 = int(remaining0 * self.config.full_range_weight)
            fr_amount1 = int(remaining1 * self.config.full_range_weight)
            
            # Full range position uses MIN_TICK to MAX_TICK
            # Simplified: use very wide range
            from .uniswap_math import MIN_TICK, MAX_TICK
            
            lower_tick = align_tick_to_spacing(MIN_TICK + 1000, self.tick_spacing)
            upper_tick = align_tick_to_spacing(MAX_TICK - 1000, self.tick_spacing)
            
            sqrt_price_current = tick_to_sqrt_price_x96(initial_tick)
            sqrt_price_lower = tick_to_sqrt_price_x96(lower_tick)
            sqrt_price_upper = tick_to_sqrt_price_x96(upper_tick)
            
            fr_liquidity = get_liquidity_for_amounts(
                sqrt_price_current, sqrt_price_lower, sqrt_price_upper,
                fr_amount0, fr_amount1
            )
            
            if fr_liquidity > 0:
                used0, used1 = get_amounts_for_liquidity(
                    sqrt_price_current, sqrt_price_lower, sqrt_price_upper,
                    fr_liquidity
                )
                positions.append(Position(
                    lower_tick=lower_tick,
                    upper_tick=upper_tick,
                    liquidity=Decimal(fr_liquidity),
                    amount0=Decimal(used0),
                    amount1=Decimal(used1),
                    entry_tick=initial_tick
                ))
                remaining0 -= used0
                remaining1 -= used1
        
        # Base Order
        base_position, remaining0, remaining1 = self._calculate_base_order(
            initial_tick, remaining0, remaining1
        )
        if base_position:
            positions.append(base_position)
        
        # Limit Order
        limit_position = self._calculate_limit_order(
            initial_tick, remaining0, remaining1
        )
        if limit_position:
            positions.append(limit_position)
        
        self.positions = positions
        return positions
    
    def check_rebalance(
        self,
        current_tick: int,
        current_time: int
    ) -> Tuple[bool, str]:
        """
        Check if rebalance should be triggered
        
        Charm uses time-based rebalancing with TWAP protection
        """
        self._update_twap(current_tick)
        
        # Check 1: Time elapsed
        time_elapsed = current_time - self.last_rebalance_time
        if time_elapsed < self.config.rebalance_interval:
            return False, ""
        
        # Check 2: TWAP deviation (prevent manipulation)
        twap_deviation = abs(current_tick - self.twap_tick)
        if twap_deviation > self.config.max_twap_deviation:
            return False, "TWAP deviation too high"
        
        # Check 3: Optional - check if positions are still effective
        # If all positions are in range and balanced, skip rebalance
        all_in_range = all(
            pos.is_in_range(current_tick) for pos in self.positions
        )
        
        if all_in_range and len(self.positions) >= 2:
            # Check if limit order is being utilized
            # If price moved significantly, rebalance might help
            if len(self.positions) > 0:
                center_tick = self.positions[0].center_tick
                if abs(current_tick - center_tick) < self.config.base_threshold // 2:
                    return False, "Positions still optimal"
        
        return True, "Time-based rebalance"
    
    def execute_rebalance(
        self,
        current_tick: int,
        current_time: int,
        amount0_available: Decimal,
        amount1_available: Decimal
    ) -> RebalanceResult:
        """
        Execute Charm's passive rebalance
        
        Key: NO SWAPS - only position adjustments
        """
        old_positions = self.positions.copy()
        
        # Calculate new positions
        new_positions = []
        remaining0 = int(amount0_available)
        remaining1 = int(amount1_available)
        
        # Full Range (if applicable)
        if self.config.full_range_weight > 0:
            fr_amount0 = int(remaining0 * self.config.full_range_weight)
            fr_amount1 = int(remaining1 * self.config.full_range_weight)
            remaining0 -= fr_amount0
            remaining1 -= fr_amount1
            
            from .uniswap_math import MIN_TICK, MAX_TICK
            lower_tick = align_tick_to_spacing(MIN_TICK + 1000, self.tick_spacing)
            upper_tick = align_tick_to_spacing(MAX_TICK - 1000, self.tick_spacing)
            
            sqrt_price_current = tick_to_sqrt_price_x96(current_tick)
            sqrt_price_lower = tick_to_sqrt_price_x96(lower_tick)
            sqrt_price_upper = tick_to_sqrt_price_x96(upper_tick)
            
            fr_liquidity = get_liquidity_for_amounts(
                sqrt_price_current, sqrt_price_lower, sqrt_price_upper,
                fr_amount0, fr_amount1
            )
            
            if fr_liquidity > 0:
                used0, used1 = get_amounts_for_liquidity(
                    sqrt_price_current, sqrt_price_lower, sqrt_price_upper,
                    fr_liquidity
                )
                new_positions.append(Position(
                    lower_tick=lower_tick,
                    upper_tick=upper_tick,
                    liquidity=Decimal(fr_liquidity),
                    amount0=Decimal(used0),
                    amount1=Decimal(used1),
                    entry_tick=current_tick,
                    entry_time=current_time
                ))
        
        # Base Order
        base_position, remaining0, remaining1 = self._calculate_base_order(
            current_tick, remaining0, remaining1
        )
        if base_position:
            base_position.entry_time = current_time
            new_positions.append(base_position)
        
        # Limit Order
        limit_position = self._calculate_limit_order(
            current_tick, remaining0, remaining1
        )
        if limit_position:
            limit_position.entry_time = current_time
            new_positions.append(limit_position)
        
        self.positions = new_positions
        self.last_rebalance_time = current_time
        self.metrics.total_rebalance_count += 1
        
        # Calculate gas cost (Charm has lower gas since no swap)
        gas_cost = self.calculate_gas_cost_usd()
        self.metrics.total_gas_cost += gas_cost
        
        result = RebalanceResult(
            timestamp=current_time,
            old_positions=old_positions,
            new_positions=new_positions,
            swap_amount=Decimal('0'),  # Charm never swaps!
            swap_fee_paid=Decimal('0'),
            gas_cost=gas_cost,
            trigger_reason="Time-based passive rebalance"
        )
        
        self.rebalance_history.append(result)
        return result
    
    def calculate_fees_earned(
        self,
        fee_growth_global0: int,
        fee_growth_global1: int,
        current_tick: int
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate fees earned by Charm positions
        
        Note: Fees are subject to protocol fee deduction
        """
        total_fees0 = Decimal('0')
        total_fees1 = Decimal('0')
        
        # Simplified fee calculation (full implementation would use fee_growth_inside)
        for position in self.positions:
            if position.is_in_range(current_tick):
                # Rough fee estimation based on liquidity and time in range
                # In real implementation, use calculate_tokens_owed
                pass
        
        # Apply Charm protocol fee
        net_fees0 = self.calculate_net_fees(total_fees0)
        net_fees1 = self.calculate_net_fees(total_fees1)
        
        return net_fees0, net_fees1
    
    def simulate_limit_order_fill(
        self,
        tick_history: List[Tuple[int, int]],
        volume_history: List[Tuple[int, Decimal]]
    ) -> Decimal:
        """
        Simulate limit order fill based on price movement
        
        For backtesting: estimate how much of the limit order got filled
        based on whether price moved through the limit order range
        """
        filled_value = Decimal('0')
        
        # Find limit order position
        limit_pos = None
        for pos in self.positions:
            if self.limit_order_direction and pos.amount0 == 0 or pos.amount1 == 0:
                limit_pos = pos
                break
        
        if not limit_pos:
            return filled_value
        
        # Check if price moved through limit order range
        for timestamp, tick in tick_history:
            if limit_pos.is_in_range(tick):
                # Partial fill simulation
                # In reality, depends on volume and liquidity
                fill_ratio = Decimal('0.1')  # 10% per tick-in-range event
                
                if self.limit_order_direction == 'sell':
                    filled = limit_pos.amount0 * fill_ratio
                    filled_value += filled
                else:
                    filled = limit_pos.amount1 * fill_ratio
                    filled_value += filled
        
        return filled_value

