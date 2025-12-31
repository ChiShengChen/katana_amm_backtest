"""
Uniswap V3 Mathematical Calculations

This module provides precise mathematical functions for Uniswap V3 concentrated
liquidity calculations, including tick-to-price conversions and liquidity math.

All calculations use high-precision Decimal arithmetic to match on-chain behavior.
"""

import math
from decimal import Decimal, getcontext, ROUND_DOWN
from typing import Tuple

# Set high precision for financial calculations
getcontext().prec = 78

# Uniswap V3 Constants
Q96 = Decimal(2 ** 96)
Q128 = Decimal(2 ** 128)
MIN_TICK = -887272
MAX_TICK = 887272
MIN_SQRT_RATIO = 4295128739
MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342


def tick_to_sqrt_price_x96(tick: int) -> int:
    """
    Convert tick to sqrtPriceX96 (Q64.96 format)
    
    Formula: sqrtPriceX96 = sqrt(1.0001^tick) * 2^96
    
    Args:
        tick: The tick value
        
    Returns:
        sqrtPriceX96 in Q64.96 format
    """
    if tick < MIN_TICK or tick > MAX_TICK:
        raise ValueError(f"Tick {tick} out of range [{MIN_TICK}, {MAX_TICK}]")
    
    # Use high precision decimal
    sqrt_ratio = Decimal('1.0001') ** (Decimal(tick) / Decimal('2'))
    return int(sqrt_ratio * Q96)


def sqrt_price_x96_to_tick(sqrt_price_x96: int) -> int:
    """
    Convert sqrtPriceX96 to tick
    
    Args:
        sqrt_price_x96: sqrtPriceX96 value
        
    Returns:
        Corresponding tick value
    """
    if sqrt_price_x96 < MIN_SQRT_RATIO or sqrt_price_x96 > MAX_SQRT_RATIO:
        sqrt_price_x96 = max(MIN_SQRT_RATIO, min(MAX_SQRT_RATIO, sqrt_price_x96))
    
    sqrt_price = Decimal(sqrt_price_x96) / Q96
    price = sqrt_price ** 2
    
    # tick = log_1.0001(price) = ln(price) / ln(1.0001)
    if price <= 0:
        return MIN_TICK
    
    tick = math.floor(math.log(float(price)) / math.log(1.0001))
    return max(MIN_TICK, min(MAX_TICK, tick))


def tick_to_price(tick: int, token0_decimals: int = 8, token1_decimals: int = 6) -> Decimal:
    """
    Convert tick to human-readable price
    
    Args:
        tick: The tick value
        token0_decimals: Decimals of token0 (e.g., 8 for WBTC)
        token1_decimals: Decimals of token1 (e.g., 6 for USDC)
        
    Returns:
        Price of token0 in terms of token1
    """
    price = Decimal('1.0001') ** Decimal(tick)
    decimal_adjustment = Decimal(10 ** (token0_decimals - token1_decimals))
    return price * decimal_adjustment


def price_to_tick(price: Decimal, token0_decimals: int = 8, token1_decimals: int = 6) -> int:
    """
    Convert price to tick
    
    Args:
        price: Price of token0 in terms of token1
        token0_decimals: Decimals of token0
        token1_decimals: Decimals of token1
        
    Returns:
        Corresponding tick value
    """
    decimal_adjustment = Decimal(10 ** (token0_decimals - token1_decimals))
    adjusted_price = price / decimal_adjustment
    
    if adjusted_price <= 0:
        return MIN_TICK
    
    tick = math.floor(math.log(float(adjusted_price)) / math.log(1.0001))
    return max(MIN_TICK, min(MAX_TICK, tick))


def get_amount0_for_liquidity(
    sqrt_price_x96: int,
    sqrt_price_lower_x96: int,
    sqrt_price_upper_x96: int,
    liquidity: int
) -> int:
    """
    Calculate token0 amount for given liquidity in a price range
    
    When current_price >= upper_price: amount0 = 0
    When current_price <= lower_price: use lower and upper
    Otherwise: use current and upper
    
    Args:
        sqrt_price_x96: Current sqrtPriceX96
        sqrt_price_lower_x96: Lower bound sqrtPriceX96
        sqrt_price_upper_x96: Upper bound sqrtPriceX96
        liquidity: Liquidity amount
        
    Returns:
        Amount of token0
    """
    if liquidity == 0:
        return 0
        
    if sqrt_price_x96 >= sqrt_price_upper_x96:
        return 0
    
    if sqrt_price_x96 <= sqrt_price_lower_x96:
        sqrt_a = sqrt_price_lower_x96
        sqrt_b = sqrt_price_upper_x96
    else:
        sqrt_a = sqrt_price_x96
        sqrt_b = sqrt_price_upper_x96
    
    # amount0 = L * (sqrt_b - sqrt_a) / (sqrt_a * sqrt_b) * Q96
    numerator = liquidity * (sqrt_b - sqrt_a) * int(Q96)
    denominator = sqrt_a * sqrt_b
    
    if denominator == 0:
        return 0
    
    return int(numerator // denominator)


def get_amount1_for_liquidity(
    sqrt_price_x96: int,
    sqrt_price_lower_x96: int,
    sqrt_price_upper_x96: int,
    liquidity: int
) -> int:
    """
    Calculate token1 amount for given liquidity in a price range
    
    When current_price <= lower_price: amount1 = 0
    When current_price >= upper_price: use lower and upper
    Otherwise: use lower and current
    
    Args:
        sqrt_price_x96: Current sqrtPriceX96
        sqrt_price_lower_x96: Lower bound sqrtPriceX96
        sqrt_price_upper_x96: Upper bound sqrtPriceX96
        liquidity: Liquidity amount
        
    Returns:
        Amount of token1
    """
    if liquidity == 0:
        return 0
        
    if sqrt_price_x96 <= sqrt_price_lower_x96:
        return 0
    
    if sqrt_price_x96 >= sqrt_price_upper_x96:
        sqrt_a = sqrt_price_lower_x96
        sqrt_b = sqrt_price_upper_x96
    else:
        sqrt_a = sqrt_price_lower_x96
        sqrt_b = sqrt_price_x96
    
    # amount1 = L * (sqrt_b - sqrt_a) / Q96
    return int(liquidity * (sqrt_b - sqrt_a) // int(Q96))


def get_liquidity_for_amounts(
    sqrt_price_x96: int,
    sqrt_price_lower_x96: int,
    sqrt_price_upper_x96: int,
    amount0: int,
    amount1: int
) -> int:
    """
    Calculate liquidity from token amounts
    
    This is the core function for calculating max balanced liquidity,
    used by Charm Alpha Vault for Base Order calculations.
    
    Args:
        sqrt_price_x96: Current sqrtPriceX96
        sqrt_price_lower_x96: Lower bound sqrtPriceX96
        sqrt_price_upper_x96: Upper bound sqrtPriceX96
        amount0: Amount of token0
        amount1: Amount of token1
        
    Returns:
        Liquidity that can be provided with given amounts
    """
    if sqrt_price_lower_x96 >= sqrt_price_upper_x96:
        return 0
    
    Q96_int = int(Q96)
    
    if sqrt_price_x96 <= sqrt_price_lower_x96:
        # Only token0, price below range
        if amount0 == 0:
            return 0
        numerator = amount0 * sqrt_price_lower_x96 * sqrt_price_upper_x96
        denominator = (sqrt_price_upper_x96 - sqrt_price_lower_x96) * Q96_int
        liquidity = numerator // denominator if denominator > 0 else 0
        
    elif sqrt_price_x96 >= sqrt_price_upper_x96:
        # Only token1, price above range
        if amount1 == 0:
            return 0
        liquidity = (amount1 * Q96_int) // (sqrt_price_upper_x96 - sqrt_price_lower_x96)
        
    else:
        # Both tokens, price in range - take minimum
        # Liquidity from amount0
        if sqrt_price_upper_x96 > sqrt_price_x96:
            numerator0 = amount0 * sqrt_price_x96 * sqrt_price_upper_x96
            denominator0 = (sqrt_price_upper_x96 - sqrt_price_x96) * Q96_int
            liquidity0 = numerator0 // denominator0 if denominator0 > 0 else 0
        else:
            liquidity0 = 0
        
        # Liquidity from amount1
        if sqrt_price_x96 > sqrt_price_lower_x96:
            liquidity1 = (amount1 * Q96_int) // (sqrt_price_x96 - sqrt_price_lower_x96)
        else:
            liquidity1 = 0
        
        liquidity = min(liquidity0, liquidity1) if liquidity0 > 0 and liquidity1 > 0 else max(liquidity0, liquidity1)
    
    return int(liquidity)


def get_amounts_for_liquidity(
    sqrt_price_x96: int,
    sqrt_price_lower_x96: int,
    sqrt_price_upper_x96: int,
    liquidity: int
) -> Tuple[int, int]:
    """
    Get both token amounts for given liquidity
    
    Args:
        sqrt_price_x96: Current sqrtPriceX96
        sqrt_price_lower_x96: Lower bound sqrtPriceX96
        sqrt_price_upper_x96: Upper bound sqrtPriceX96
        liquidity: Liquidity amount
        
    Returns:
        Tuple of (amount0, amount1)
    """
    amount0 = get_amount0_for_liquidity(
        sqrt_price_x96, sqrt_price_lower_x96, sqrt_price_upper_x96, liquidity
    )
    amount1 = get_amount1_for_liquidity(
        sqrt_price_x96, sqrt_price_lower_x96, sqrt_price_upper_x96, liquidity
    )
    return amount0, amount1


def calculate_fee_growth_inside(
    fee_growth_global_0: int,
    fee_growth_global_1: int,
    fee_growth_outside_lower_0: int,
    fee_growth_outside_lower_1: int,
    fee_growth_outside_upper_0: int,
    fee_growth_outside_upper_1: int,
    current_tick: int,
    lower_tick: int,
    upper_tick: int
) -> Tuple[int, int]:
    """
    Calculate fee growth inside a tick range
    
    This is critical for accurate LP fee calculations.
    
    Args:
        fee_growth_global_0: Global fee growth for token0
        fee_growth_global_1: Global fee growth for token1
        fee_growth_outside_lower_0: Fee growth outside lower tick for token0
        fee_growth_outside_lower_1: Fee growth outside lower tick for token1
        fee_growth_outside_upper_0: Fee growth outside upper tick for token0
        fee_growth_outside_upper_1: Fee growth outside upper tick for token1
        current_tick: Current pool tick
        lower_tick: Position lower tick
        upper_tick: Position upper tick
        
    Returns:
        Tuple of (fee_growth_inside_0, fee_growth_inside_1)
    """
    Q128_int = int(Q128)
    
    # Fee growth below lower tick
    if current_tick >= lower_tick:
        fee_growth_below_0 = fee_growth_outside_lower_0
        fee_growth_below_1 = fee_growth_outside_lower_1
    else:
        fee_growth_below_0 = fee_growth_global_0 - fee_growth_outside_lower_0
        fee_growth_below_1 = fee_growth_global_1 - fee_growth_outside_lower_1
    
    # Fee growth above upper tick
    if current_tick < upper_tick:
        fee_growth_above_0 = fee_growth_outside_upper_0
        fee_growth_above_1 = fee_growth_outside_upper_1
    else:
        fee_growth_above_0 = fee_growth_global_0 - fee_growth_outside_upper_0
        fee_growth_above_1 = fee_growth_global_1 - fee_growth_outside_upper_1
    
    # Fee growth inside (handling underflow with modulo)
    fee_growth_inside_0 = (fee_growth_global_0 - fee_growth_below_0 - fee_growth_above_0) % Q128_int
    fee_growth_inside_1 = (fee_growth_global_1 - fee_growth_below_1 - fee_growth_above_1) % Q128_int
    
    return int(fee_growth_inside_0), int(fee_growth_inside_1)


def calculate_tokens_owed(
    liquidity: int,
    fee_growth_inside_0: int,
    fee_growth_inside_1: int,
    fee_growth_inside_0_last: int,
    fee_growth_inside_1_last: int
) -> Tuple[int, int]:
    """
    Calculate tokens owed from fee growth
    
    Args:
        liquidity: Position liquidity
        fee_growth_inside_0: Current fee growth inside for token0
        fee_growth_inside_1: Current fee growth inside for token1
        fee_growth_inside_0_last: Last recorded fee growth for token0
        fee_growth_inside_1_last: Last recorded fee growth for token1
        
    Returns:
        Tuple of (tokens_owed_0, tokens_owed_1)
    """
    Q128_int = int(Q128)
    
    # Handle underflow
    delta_0 = (fee_growth_inside_0 - fee_growth_inside_0_last) % Q128_int
    delta_1 = (fee_growth_inside_1 - fee_growth_inside_1_last) % Q128_int
    
    tokens_owed_0 = (liquidity * delta_0) // Q128_int
    tokens_owed_1 = (liquidity * delta_1) // Q128_int
    
    return int(tokens_owed_0), int(tokens_owed_1)


def calculate_swap_amount_for_ratio(
    amount0: int,
    amount1: int,
    sqrt_price_x96: int,
    target_ratio: float = 0.5
) -> Tuple[int, bool]:
    """
    Calculate swap amount needed to achieve target token ratio
    
    Args:
        amount0: Current amount of token0
        amount1: Current amount of token1
        sqrt_price_x96: Current sqrtPriceX96
        target_ratio: Target ratio of token0 value to total (0.5 = 50/50)
        
    Returns:
        Tuple of (swap_amount, swap_0_to_1)
        swap_0_to_1: True if swapping token0 for token1
    """
    price = (Decimal(sqrt_price_x96) / Q96) ** 2
    
    total_value_in_token1 = Decimal(amount0) * price + Decimal(amount1)
    
    if total_value_in_token1 == 0:
        return 0, True
    
    target_value0_in_token1 = total_value_in_token1 * Decimal(str(target_ratio))
    current_value0_in_token1 = Decimal(amount0) * price
    
    if current_value0_in_token1 > target_value0_in_token1:
        # Too much token0, swap to token1
        excess_value = current_value0_in_token1 - target_value0_in_token1
        swap_amount = int(excess_value / price)
        return swap_amount, True
    else:
        # Too much token1, swap to token0
        deficit_value = target_value0_in_token1 - current_value0_in_token1
        swap_amount = int(deficit_value)
        return swap_amount, False


def align_tick_to_spacing(tick: int, tick_spacing: int) -> int:
    """
    Align tick to the nearest tick spacing boundary (floor)
    
    Args:
        tick: Raw tick value
        tick_spacing: Pool tick spacing
        
    Returns:
        Aligned tick
    """
    return (tick // tick_spacing) * tick_spacing


def get_tick_spacing_for_fee(fee: int) -> int:
    """
    Get tick spacing for a given fee tier
    
    Args:
        fee: Fee tier (500, 3000, 10000)
        
    Returns:
        Tick spacing
    """
    spacing_map = {
        100: 1,
        500: 10,
        3000: 60,
        10000: 200
    }
    return spacing_map.get(fee, 60)

