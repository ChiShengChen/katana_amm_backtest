"""
Strategy Backtesting Framework

Unified framework for backtesting and comparing different AMM strategies:
- Omnis AI (ATR-based)
- Steer Finance (Classic, Elastic, Fluid)
- Charm Alpha Vault (Passive)
"""

import csv
from decimal import Decimal
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .base_strategy import BaseAMMStrategy, Position, StrategyMetrics
from .charm_strategy import CharmAlphaVaultStrategy
from .steer_strategy import SteerClassicStrategy, SteerElasticStrategy, SteerFluidStrategy


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    start_time: int = 0
    end_time: int = 0
    initial_amount0: Decimal = Decimal('0')
    initial_amount1: Decimal = Decimal('0')
    pool_fee: int = 3000
    tick_spacing: int = 60
    token0_decimals: int = 8  # WBTC
    token1_decimals: int = 6  # USDC
    gas_price_gwei: float = 30.0
    eth_price_usd: float = 2000.0


@dataclass
class BacktestResult:
    """Result of a single strategy backtest"""
    strategy_name: str
    initial_value: Decimal
    final_value: Decimal
    total_return_pct: float
    annualized_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    total_fees_earned: Decimal
    net_fees_earned: Decimal  # After protocol fees
    total_rebalance_count: int
    total_gas_cost: Decimal
    total_swap_cost: Decimal
    impermanent_loss_pct: float
    time_in_range_pct: float
    value_history: List[Tuple[int, Decimal]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'strategy': self.strategy_name,
            'initial_value': float(self.initial_value),
            'final_value': float(self.final_value),
            'total_return_pct': self.total_return_pct,
            'annualized_return_pct': self.annualized_return_pct,
            'max_drawdown_pct': self.max_drawdown_pct,
            'sharpe_ratio': self.sharpe_ratio,
            'total_fees_earned': float(self.total_fees_earned),
            'net_fees_earned': float(self.net_fees_earned),
            'rebalance_count': self.total_rebalance_count,
            'gas_cost': float(self.total_gas_cost),
            'swap_cost': float(self.total_swap_cost),
            'impermanent_loss_pct': self.impermanent_loss_pct,
            'time_in_range_pct': self.time_in_range_pct
        }


class StrategyBacktester:
    """
    Unified backtesting engine for AMM strategies
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.tick_history: List[Tuple[int, int]] = []  # [(timestamp, tick), ...]
        self.price_history: List[Tuple[int, float]] = []  # [(timestamp, price), ...]
        self.volume_history: List[Tuple[int, Decimal]] = []  # [(timestamp, volume), ...]
    
    def load_tick_data(self, data_file: str):
        """Load historical tick data from file"""
        self.tick_history = []
        self.price_history = []
        
        import json
        
        with open(data_file, 'r') as f:
            for line in f:
                try:
                    event = json.loads(line)
                    
                    # Support both formats: 'type'/'eventType' and 'timestamp'/'blockTimestamp'
                    event_type = event.get('eventType') or event.get('type')
                    
                    if event_type == 'Swap':
                        timestamp = event.get('blockTimestamp') or event.get('timestamp', 0)
                        tick = event.get('tick', 0)
                        
                        # Handle tick from sqrtPriceX96 if tick not available
                        if tick == 0 and 'sqrtPriceX96' in event:
                            sqrt_price_x96 = int(event['sqrtPriceX96'])
                            from .uniswap_math import sqrt_price_x96_to_tick
                            tick = sqrt_price_x96_to_tick(sqrt_price_x96)
                        
                        if timestamp > 0 and tick != 0:
                            self.tick_history.append((timestamp, tick))
                            
                            # Calculate approximate price from tick
                            price = (1.0001 ** tick) * (10 ** 2)  # WBTC/USDC adjustment
                            self.price_history.append((timestamp, price))
                except Exception as e:
                    continue
        
        if self.tick_history:
            self.config.start_time = self.tick_history[0][0]
            self.config.end_time = self.tick_history[-1][0]
        
        print(f"Loaded {len(self.tick_history)} tick data points")
    
    def run_backtest(self, strategy: BaseAMMStrategy) -> BacktestResult:
        """Run backtest for a single strategy"""
        if not self.tick_history:
            raise ValueError("No tick data loaded. Call load_tick_data first.")
        
        # Initialize strategy
        initial_tick = self.tick_history[0][1]
        initial_time = self.tick_history[0][0]
        
        amount0 = self.config.initial_amount0
        amount1 = self.config.initial_amount1
        
        positions = strategy.initialize(initial_tick, amount0, amount1, initial_time)
        
        # Calculate initial value
        initial_price = self.price_history[0][1]
        initial_value = amount0 * Decimal(str(initial_price)) + amount1
        
        # Track value history
        value_history: List[Tuple[int, Decimal]] = [(initial_time, initial_value)]
        peak_value = initial_value
        max_drawdown = Decimal('0')
        
        # Simulate through tick history
        time_in_range = 0
        total_time = 0
        last_timestamp = initial_time
        
        for i, (timestamp, tick) in enumerate(self.tick_history[1:], 1):
            # Update time tracking
            time_delta = timestamp - last_timestamp
            total_time += time_delta
            
            # Check if in range
            in_range = any(pos.is_in_range(tick) for pos in strategy.positions)
            if in_range:
                time_in_range += time_delta
            
            # Update strategy's price history
            strategy.update_price_history(timestamp, tick)
            
            # Check for rebalance
            should_rebalance, reason = strategy.check_rebalance(tick, timestamp)
            
            if should_rebalance:
                # Calculate current amounts from positions
                current_amount0 = sum(pos.amount0 for pos in strategy.positions)
                current_amount1 = sum(pos.amount1 for pos in strategy.positions)
                
                # Execute rebalance
                strategy.execute_rebalance(
                    tick, timestamp,
                    current_amount0, current_amount1
                )
            
            # Calculate current value periodically
            if i % 100 == 0:
                price = self.price_history[i][1] if i < len(self.price_history) else initial_price
                
                # Recalculate position amounts based on current tick
                current_value = Decimal('0')
                for pos in strategy.positions:
                    # Use Uniswap V3 math to get current amounts
                    from .uniswap_math import (
                        tick_to_sqrt_price_x96,
                        get_amounts_for_liquidity
                    )
                    sqrt_price_current = tick_to_sqrt_price_x96(tick)
                    sqrt_price_lower = tick_to_sqrt_price_x96(pos.lower_tick)
                    sqrt_price_upper = tick_to_sqrt_price_x96(pos.upper_tick)
                    
                    amt0, amt1 = get_amounts_for_liquidity(
                        sqrt_price_current,
                        sqrt_price_lower,
                        sqrt_price_upper,
                        int(pos.liquidity)
                    )
                    
                    pos_value = Decimal(amt0) * Decimal(str(price)) + Decimal(amt1)
                    current_value += pos_value
                
                if current_value > 0:
                    value_history.append((timestamp, current_value))
                
                # Track max drawdown
                if current_value > peak_value:
                    peak_value = current_value
                drawdown = (peak_value - current_value) / peak_value * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            last_timestamp = timestamp
        
        # Final calculations
        final_price = self.price_history[-1][1] if self.price_history else initial_price
        final_tick = self.tick_history[-1][1] if self.tick_history else initial_tick
        
        # Calculate final value using proper Uniswap V3 math
        from .uniswap_math import tick_to_sqrt_price_x96, get_amounts_for_liquidity
        
        final_value = Decimal('0')
        for pos in strategy.positions:
            sqrt_price_current = tick_to_sqrt_price_x96(final_tick)
            sqrt_price_lower = tick_to_sqrt_price_x96(pos.lower_tick)
            sqrt_price_upper = tick_to_sqrt_price_x96(pos.upper_tick)
            
            amt0, amt1 = get_amounts_for_liquidity(
                sqrt_price_current,
                sqrt_price_lower,
                sqrt_price_upper,
                int(pos.liquidity)
            )
            
            pos_value = Decimal(amt0) * Decimal(str(final_price)) + Decimal(amt1)
            final_value += pos_value
        
        # Fallback if no positions
        if final_value == 0:
            final_value = initial_value * Decimal('0.01')  # Assume 99% loss
        
        # Calculate returns
        total_return = float((final_value - initial_value) / initial_value * 100)
        
        # Annualized return
        days = (self.config.end_time - self.config.start_time) / 86400
        if days > 0:
            annualized_return = ((float(final_value / initial_value) ** (365 / days)) - 1) * 100
        else:
            annualized_return = 0.0
        
        # Calculate Sharpe ratio (simplified)
        sharpe = 0.0
        if len(value_history) > 1:
            returns = []
            for i in range(1, len(value_history)):
                prev_val = value_history[i-1][1]
                if prev_val > 0:
                    r = float((value_history[i][1] - prev_val) / prev_val)
                    returns.append(r)
            
            if len(returns) > 1:
                import statistics
                avg_return = statistics.mean(returns)
                std_return = statistics.stdev(returns) if len(returns) > 1 else 0.001
                sharpe = (avg_return / std_return) * (365 ** 0.5) if std_return > 0 else 0
        
        # Calculate IL
        hodl_value = (self.config.initial_amount0 * Decimal(str(final_price)) + 
                     self.config.initial_amount1)
        il_pct = float((final_value - hodl_value) / hodl_value * 100) if hodl_value > 0 else 0
        
        # Time in range percentage
        time_in_range_pct = (time_in_range / total_time * 100) if total_time > 0 else 0
        
        return BacktestResult(
            strategy_name=strategy.name,
            initial_value=initial_value,
            final_value=final_value,
            total_return_pct=total_return,
            annualized_return_pct=annualized_return,
            max_drawdown_pct=float(max_drawdown),
            sharpe_ratio=sharpe,
            total_fees_earned=strategy.metrics.total_fees_earned,
            net_fees_earned=strategy.calculate_net_fees(strategy.metrics.total_fees_earned),
            total_rebalance_count=strategy.metrics.total_rebalance_count,
            total_gas_cost=strategy.metrics.total_gas_cost,
            total_swap_cost=strategy.metrics.total_swap_cost,
            impermanent_loss_pct=il_pct,
            time_in_range_pct=time_in_range_pct,
            value_history=value_history
        )
    
    def compare_strategies(
        self,
        strategies: List[BaseAMMStrategy]
    ) -> Dict[str, BacktestResult]:
        """Run backtests on multiple strategies and compare"""
        results = {}
        
        for strategy in strategies:
            result = self.run_backtest(strategy)
            results[strategy.name] = result
        
        return results
    
    def generate_comparison_report(
        self,
        results: Dict[str, BacktestResult],
        output_file: str = "strategy_comparison.csv"
    ):
        """Generate comparison report as CSV"""
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            headers = [
                'Strategy', 'Final Value', 'Total Return %', 'Annual Return %',
                'Max Drawdown %', 'Sharpe Ratio', 'Fees Earned', 'Net Fees',
                'Rebalances', 'Gas Cost', 'Swap Cost', 'IL %', 'Time in Range %'
            ]
            writer.writerow(headers)
            
            # Data rows
            for name, result in results.items():
                row = [
                    name,
                    f"${float(result.final_value):,.2f}",
                    f"{result.total_return_pct:.2f}%",
                    f"{result.annualized_return_pct:.2f}%",
                    f"{result.max_drawdown_pct:.2f}%",
                    f"{result.sharpe_ratio:.2f}",
                    f"${float(result.total_fees_earned):,.2f}",
                    f"${float(result.net_fees_earned):,.2f}",
                    result.total_rebalance_count,
                    f"${float(result.total_gas_cost):,.2f}",
                    f"${float(result.total_swap_cost):,.2f}",
                    f"{result.impermanent_loss_pct:.2f}%",
                    f"{result.time_in_range_pct:.1f}%"
                ]
                writer.writerow(row)
        
        print(f"Comparison report saved to: {output_file}")


def run_strategy_comparison(
    data_file: str,
    initial_capital_usdc: float = 10000.0,
    output_dir: str = "output/marketing"
):
    """
    Run comparison of all strategies
    
    Args:
        data_file: Path to JSONL file with swap events
        initial_capital_usdc: Initial capital in USDC
        output_dir: Output directory for reports
    """
    # Configure backtest
    config = BacktestConfig(
        initial_amount0=Decimal('0'),  # Will be set based on initial price
        initial_amount1=Decimal(str(initial_capital_usdc / 2)),  # 50% USDC
        pool_fee=3000,
        tick_spacing=60
    )
    
    # Initialize backtester
    backtester = StrategyBacktester(config)
    backtester.load_tick_data(data_file)
    
    # Set initial amounts based on first price
    if backtester.price_history:
        initial_price = backtester.price_history[0][1]
        config.initial_amount0 = Decimal(str((initial_capital_usdc / 2) / initial_price))
    
    # Create strategies to compare
    strategies = [
        # Charm Alpha Vault (Passive)
        CharmAlphaVaultStrategy(
            base_threshold=600,
            limit_threshold=1200,
            rebalance_interval=172800,  # 48 hours
            pool_fee=3000,
            tick_spacing=60
        ),
        
        # Steer Classic (Fixed Width)
        SteerClassicStrategy(
            position_width_ticks=600,
            rebalance_threshold_bps=500,
            pool_fee=3000,
            tick_spacing=60
        ),
        
        # Steer Elastic (Bollinger)
        SteerElasticStrategy(
            sma_period=20,
            std_multiplier=2.0,
            min_width_ticks=120,
            pool_fee=3000,
            tick_spacing=60
        ),
        
        # Steer Fluid (Three-State)
        SteerFluidStrategy(
            ideal_ratio=0.5,
            acceptable_ratio_magnitude=0.1,
            pool_fee=3000,
            tick_spacing=60
        ),
    ]
    
    # Run comparisons
    results = backtester.compare_strategies(strategies)
    
    # Generate report
    import os
    os.makedirs(output_dir, exist_ok=True)
    backtester.generate_comparison_report(
        results,
        f"{output_dir}/strategy_comparison.csv"
    )
    
    # Print summary
    print("\n" + "=" * 70)
    print("Strategy Comparison Results")
    print("=" * 70)
    
    for name, result in sorted(results.items(), key=lambda x: x[1].total_return_pct, reverse=True):
        print(f"\n{name}:")
        print(f"  Total Return: {result.total_return_pct:+.2f}%")
        print(f"  Max Drawdown: {result.max_drawdown_pct:.2f}%")
        print(f"  Rebalances: {result.total_rebalance_count}")
        print(f"  Gas + Swap Cost: ${float(result.total_gas_cost + result.total_swap_cost):,.2f}")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python strategy_backtest.py <data_file.jsonl> [initial_capital]")
        sys.exit(1)
    
    data_file = sys.argv[1]
    initial_capital = float(sys.argv[2]) if len(sys.argv) > 2 else 10000.0
    
    run_strategy_comparison(data_file, initial_capital)

