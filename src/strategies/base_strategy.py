"""
Base Strategy Interface for AMM Liquidity Provision Strategies

This module defines the abstract base class that all AMM strategies must implement,
ensuring compatibility with the backtesting framework.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from decimal import Decimal, getcontext
from enum import Enum

# Set high precision for financial calculations
getcontext().prec = 78


@dataclass
class Position:
    """
    Represents a concentrated liquidity position in Uniswap V3
    
    Attributes:
        lower_tick: Lower bound of the price range (tick)
        upper_tick: Upper bound of the price range (tick)
        liquidity: Amount of liquidity provided (L)
        amount0: Amount of token0 in the position
        amount1: Amount of token1 in the position
        entry_tick: Tick at which position was created
        entry_time: Timestamp when position was created
        fee_growth_inside0_last: Last recorded fee growth for token0
        fee_growth_inside1_last: Last recorded fee growth for token1
    """
    lower_tick: int
    upper_tick: int
    liquidity: Decimal
    amount0: Decimal
    amount1: Decimal
    entry_tick: int = 0
    entry_time: int = 0
    fee_growth_inside0_last: int = 0
    fee_growth_inside1_last: int = 0
    
    @property
    def tick_range(self) -> int:
        """Returns the width of the position in ticks"""
        return self.upper_tick - self.lower_tick
    
    @property
    def center_tick(self) -> int:
        """Returns the center tick of the position"""
        return (self.lower_tick + self.upper_tick) // 2
    
    def is_in_range(self, current_tick: int) -> bool:
        """Check if the current tick is within the position range"""
        return self.lower_tick <= current_tick < self.upper_tick


@dataclass
class RebalanceResult:
    """
    Result of a rebalance operation
    
    Attributes:
        timestamp: When the rebalance occurred
        old_positions: Positions before rebalance
        new_positions: Positions after rebalance
        swap_amount: Amount swapped (Charm should be 0)
        swap_fee_paid: Swap fees paid for rebalancing
        gas_cost: Gas cost in USD
        trigger_reason: Why the rebalance was triggered
    """
    timestamp: int
    old_positions: List[Position]
    new_positions: List[Position]
    swap_amount: Decimal = Decimal('0')
    swap_fee_paid: Decimal = Decimal('0')
    gas_cost: Decimal = Decimal('0')
    trigger_reason: str = ""
    
    @property
    def total_cost(self) -> Decimal:
        """Total cost of the rebalance operation"""
        return self.swap_fee_paid + self.gas_cost


class RebalanceTriggerType(Enum):
    """Types of rebalance triggers"""
    PRICE_GAP = "price_gap"
    RANGE_INACTIVE = "range_inactive"
    PRICE_PERCENTAGE_DRIFT = "price_percentage_drift"
    ONE_WAY_EXIT = "one_way_exit"
    TIME_BASED = "time_based"
    MANUAL = "manual"


@dataclass
class StrategyMetrics:
    """
    Metrics for strategy performance evaluation
    """
    total_fees_earned: Decimal = Decimal('0')
    total_rebalance_count: int = 0
    total_gas_cost: Decimal = Decimal('0')
    total_swap_cost: Decimal = Decimal('0')
    time_in_range_seconds: int = 0
    total_time_seconds: int = 0
    
    @property
    def time_in_range_pct(self) -> float:
        if self.total_time_seconds == 0:
            return 0.0
        return (self.time_in_range_seconds / self.total_time_seconds) * 100


class BaseAMMStrategy(ABC):
    """
    Abstract base class for all AMM liquidity provision strategies
    
    All strategies (ATR, Steer, Charm) must inherit from this class
    and implement the required methods.
    """
    
    def __init__(
        self,
        pool_fee: int = 3000,  # Fee tier: 500, 3000, 10000
        tick_spacing: int = 60,
        protocol_fee_rate: float = 0.0,
        gas_price_gwei: float = 30.0,
        rebalance_gas_limit: int = 500000
    ):
        """
        Initialize the base strategy
        
        Args:
            pool_fee: Uniswap V3 pool fee tier (500=0.05%, 3000=0.3%, 10000=1%)
            tick_spacing: Pool tick spacing (10, 60, or 200 depending on fee tier)
            protocol_fee_rate: Protocol's performance fee rate (e.g., 0.15 for Steer)
            gas_price_gwei: Gas price in Gwei
            rebalance_gas_limit: Estimated gas for rebalance transaction
        """
        self.pool_fee = pool_fee
        self.tick_spacing = tick_spacing
        self.protocol_fee_rate = protocol_fee_rate
        self.gas_price_gwei = gas_price_gwei
        self.rebalance_gas_limit = rebalance_gas_limit
        
        # State
        self.positions: List[Position] = []
        self.last_rebalance_time: int = 0
        self.rebalance_history: List[RebalanceResult] = []
        self.metrics = StrategyMetrics()
        
        # Price history for calculations
        self.price_history: List[Tuple[int, int]] = []  # [(timestamp, tick), ...]
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for reporting"""
        pass
    
    @abstractmethod
    def initialize(
        self,
        initial_tick: int,
        amount0: Decimal,
        amount1: Decimal,
        timestamp: int
    ) -> List[Position]:
        """
        Initialize the strategy with initial capital
        
        Args:
            initial_tick: Current pool tick
            amount0: Initial amount of token0
            amount1: Initial amount of token1
            timestamp: Current timestamp
            
        Returns:
            List of initial positions
        """
        pass
    
    @abstractmethod
    def check_rebalance(
        self,
        current_tick: int,
        current_time: int
    ) -> Tuple[bool, str]:
        """
        Check if rebalance is needed
        
        Args:
            current_tick: Current pool tick
            current_time: Current timestamp
            
        Returns:
            Tuple of (should_rebalance, reason)
        """
        pass
    
    @abstractmethod
    def execute_rebalance(
        self,
        current_tick: int,
        current_time: int,
        amount0_available: Decimal,
        amount1_available: Decimal
    ) -> RebalanceResult:
        """
        Execute rebalance and return new positions
        
        Args:
            current_tick: Current pool tick
            current_time: Current timestamp
            amount0_available: Available token0 after withdrawing old positions
            amount1_available: Available token1 after withdrawing old positions
            
        Returns:
            RebalanceResult with old and new positions
        """
        pass
    
    @abstractmethod
    def calculate_fees_earned(
        self,
        fee_growth_global0: int,
        fee_growth_global1: int,
        current_tick: int
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate fees earned by current positions
        
        Args:
            fee_growth_global0: Global fee growth for token0
            fee_growth_global1: Global fee growth for token1
            current_tick: Current pool tick
            
        Returns:
            Tuple of (fees_token0, fees_token1)
        """
        pass
    
    def calculate_net_fees(self, gross_fees: Decimal) -> Decimal:
        """
        Calculate net fees after protocol fee deduction
        
        Args:
            gross_fees: Gross fee income
            
        Returns:
            Net fees after protocol fee
        """
        return gross_fees * (Decimal('1') - Decimal(str(self.protocol_fee_rate)))
    
    def calculate_gas_cost_usd(self, eth_price_usd: float = 2000.0) -> Decimal:
        """
        Calculate gas cost for rebalance in USD
        
        Args:
            eth_price_usd: Current ETH price in USD
            
        Returns:
            Gas cost in USD
        """
        gas_cost_eth = (self.gas_price_gwei * self.rebalance_gas_limit) / 1e9
        return Decimal(str(gas_cost_eth * eth_price_usd))
    
    def align_tick_to_spacing(self, tick: int) -> int:
        """
        Align tick to the pool's tick spacing
        
        Args:
            tick: Raw tick value
            
        Returns:
            Tick aligned to tick_spacing
        """
        return (tick // self.tick_spacing) * self.tick_spacing
    
    def update_price_history(self, timestamp: int, tick: int):
        """Add a new price point to history"""
        self.price_history.append((timestamp, tick))
    
    def get_recent_ticks(self, n: int) -> List[int]:
        """Get the n most recent ticks"""
        return [tick for _, tick in self.price_history[-n:]]
    
    def get_position_value(
        self,
        position: Position,
        current_tick: int,
        token0_price: Decimal,
        token1_price: Decimal = Decimal('1')
    ) -> Decimal:
        """
        Calculate the current value of a position
        
        Args:
            position: The position to value
            current_tick: Current pool tick
            token0_price: Price of token0 in terms of token1
            token1_price: Price of token1 (default 1 for stablecoins)
            
        Returns:
            Position value in token1 terms
        """
        return position.amount0 * token0_price + position.amount1 * token1_price
    
    def get_total_value(
        self,
        current_tick: int,
        token0_price: Decimal
    ) -> Decimal:
        """Get total value of all positions"""
        return sum(
            self.get_position_value(pos, current_tick, token0_price)
            for pos in self.positions
        )

