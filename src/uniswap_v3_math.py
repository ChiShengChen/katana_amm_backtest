"""
Uniswap V3 數學計算模組
實現正確的流動性和 token 數量計算

關鍵概念：
- tick: Uniswap V3 的價格表示，price = 1.0001^tick
- sqrtPriceX96: sqrt(price) * 2^96，Uniswap V3 合約使用的價格表示
- liquidity: 流動性，以 Q64.96 格式存儲（大整數）

對於 WBTC/USDC 交易對：
- token0 = WBTC (8 decimals)
- token1 = USDC (6 decimals)
- price = token1 / token0 = USDC per WBTC
- 由於 decimals 差異，display_price = on_chain_price * 10^(8-6) = on_chain_price * 100
"""
import math
from decimal import Decimal, getcontext

# 設置高精度計算
getcontext().prec = 50

Q96 = 2 ** 96
Q128 = 2 ** 128

# Token decimals
TOKEN0_DECIMALS = 8  # WBTC
TOKEN1_DECIMALS = 6  # USDC
PRICE_SCALE = 10 ** (TOKEN0_DECIMALS - TOKEN1_DECIMALS)  # 10^2 = 100


def tick_to_sqrt_price(tick: int) -> float:
    """將 tick 轉換為 sqrt price（用於流動性計算）
    
    返回: sqrt(1.0001^tick)
    
    這與 sqrtPriceX96 / 2^96 的值一致
    """
    MAX_TICK = 887272
    MIN_TICK = -887272
    
    if tick > MAX_TICK:
        return 1e15
    elif tick < MIN_TICK:
        return 1e-15
    
    try:
        # 使用對數計算避免溢出
        # sqrt(1.0001^tick) = exp(tick * ln(1.0001) / 2)
        log_base = math.log(1.0001)
        half_tick_log = tick * log_base / 2.0
        
        if abs(half_tick_log) > 700:
            raise OverflowError("Tick too large")
        
        sqrt_price = math.exp(half_tick_log)
        
        if math.isinf(sqrt_price) or math.isnan(sqrt_price):
            raise OverflowError("Result is inf or nan")
        
        return sqrt_price
        
    except (OverflowError, ValueError):
        try:
            getcontext().Emax = 999999999
            getcontext().Emin = -999999999
            
            price_decimal = Decimal('1.0001') ** Decimal(tick)
            sqrt_price = float(price_decimal.sqrt())
            
            if math.isinf(sqrt_price) or math.isnan(sqrt_price):
                raise OverflowError("Decimal result is inf or nan")
            
            return sqrt_price
        except:
            return 1e15 if tick > 0 else 1e-15


def sqrt_price_to_price(sqrt_price: float) -> float:
    """將 sqrt price 轉換為顯示價格 (USDC per WBTC)
    
    display_price = (sqrt_price)^2 * PRICE_SCALE
    """
    return (sqrt_price ** 2) * PRICE_SCALE


def get_amounts_from_liquidity(
    liquidity: int,
    sqrt_price_current: float,
    sqrt_price_lower: float,
    sqrt_price_upper: float,
    current_tick: int,
    tick_lower: int,
    tick_upper: int
) -> tuple:
    """從流動性計算 token 數量（Uniswap V3 公式）
    
    Args:
        liquidity: 流動性（整數，不需要預先縮放）
        sqrt_price_*: sqrt(1.0001^tick) 格式的價格
        
    返回: (amount0, amount1) 以合約原始單位
          amount0 需要除以 10^8 得到 WBTC
          amount1 需要除以 10^6 得到 USDC
    
    關鍵公式（Uniswap V3 白皮書）：
    - 如果 current_tick < tick_lower（價格在範圍下方）：
        amount0 = L * (1/√P_lower - 1/√P_upper)
        amount1 = 0
    - 如果 current_tick >= tick_upper（價格在範圍上方）：
        amount0 = 0
        amount1 = L * (√P_upper - √P_lower)
    - 如果 tick_lower <= current_tick < tick_upper（價格在範圍內）：
        amount0 = L * (1/√P - 1/√P_upper)
        amount1 = L * (√P - √P_lower)
    """
    if liquidity <= 0:
        return (0, 0)
    
    # 保護性檢查
    if sqrt_price_current <= 0 or sqrt_price_lower <= 0 or sqrt_price_upper <= 0:
        return (0, 0)
    if sqrt_price_lower >= sqrt_price_upper:
        return (0, 0)
    
    # 使用浮點數計算（liquidity 很大，但結果需要精確）
    L = float(liquidity)
    
    if current_tick < tick_lower:
        # 價格在範圍下方，全部是 token0
        amount0 = L * (1.0 / sqrt_price_lower - 1.0 / sqrt_price_upper)
        amount1 = 0.0
    elif current_tick >= tick_upper:
        # 價格在範圍上方，全部是 token1
        amount0 = 0.0
        amount1 = L * (sqrt_price_upper - sqrt_price_lower)
    else:
        # 價格在範圍內
        amount0 = L * (1.0 / sqrt_price_current - 1.0 / sqrt_price_upper)
        amount1 = L * (sqrt_price_current - sqrt_price_lower)
    
    # 確保非負
    amount0 = max(0.0, amount0)
    amount1 = max(0.0, amount1)
    
    # 注意：這裡返回的是"虛擬"單位，需要乘以 token decimals
    # 但在 Uniswap V3 中，liquidity 的定義使得這些值可以直接作為合約單位
    # 我們需要根據 token decimals 進行調整
    
    # 轉換為合約單位
    # 對於 Uniswap V3，公式假設價格是 token1/token0 的比值
    # 但合約中存儲的是帶 decimals 的值
    # 所以 amount0（WBTC）需要乘以 10^8 的某個因子，amount1（USDC）需要乘以 10^6 的某個因子
    # 
    # 實際上，Uniswap V3 的 liquidity 定義使得：
    # - 當 L = 1 時，amount0 的單位是 1 個 token0 的最小單位（satoshi for WBTC）
    # - 當 L = 1 時，amount1 的單位是 1 個 token1 的最小單位（微 USDC）
    #
    # 但由於 sqrt_price 是原始的 1.0001^tick，沒有考慮 decimals，
    # 我們需要調整結果
    
    # 實際公式（考慮 decimals）：
    # 如果 price = (token1 * 10^d1) / (token0 * 10^d0) = token1/token0 * 10^(d1-d0)
    # 那麼 sqrt_price = sqrt(price) = sqrt(token1/token0) * 10^((d1-d0)/2)
    #
    # 但我們的 sqrt_price 是 sqrt(1.0001^tick)，這是"原始"價格
    # 需要通過 PRICE_SCALE 來轉換
    #
    # 簡化處理：直接使用公式計算，然後根據需要轉換
    
    return (int(amount0), int(amount1))


def get_liquidity_from_amounts(
    amount0: int,
    amount1: int,
    sqrt_price_current: float,
    sqrt_price_lower: float,
    sqrt_price_upper: float,
    current_tick: int,
    tick_lower: int,
    tick_upper: int
) -> int:
    """從 token 數量計算流動性（Uniswap V3 公式）
    
    Args:
        amount0: WBTC 數量（合約原始單位，需要除以 10^8 得到實際值）
        amount1: USDC 數量（合約原始單位，需要除以 10^6 得到實際值）
        sqrt_price_*: sqrt(1.0001^tick) 格式的價格
        
    返回: liquidity（整數）
    
    關鍵公式：
    - L0 = amount0 / (1/√P - 1/√P_upper)  # 從 token0 計算
    - L1 = amount1 / (√P - √P_lower)       # 從 token1 計算
    - L = min(L0, L1)  # 取較小值
    """
    # 保護性檢查
    if sqrt_price_current <= 0 or sqrt_price_lower <= 0 or sqrt_price_upper <= 0:
        return 0
    if sqrt_price_lower >= sqrt_price_upper:
        return 0
    
    if current_tick < tick_lower:
        # 價格在範圍下方，只有 token0
        denominator = (1.0 / sqrt_price_lower - 1.0 / sqrt_price_upper)
        if denominator > 0 and amount0 > 0:
            return int(float(amount0) / denominator)
        return 0
    elif current_tick >= tick_upper:
        # 價格在範圍上方，只有 token1
        denominator = sqrt_price_upper - sqrt_price_lower
        if denominator > 0 and amount1 > 0:
            return int(float(amount1) / denominator)
        return 0
    else:
        # 價格在範圍內，需要兩種 token
        L0 = 0
        L1 = 0
        
        denom0 = (1.0 / sqrt_price_current - 1.0 / sqrt_price_upper)
        if denom0 > 0 and amount0 > 0:
            L0 = float(amount0) / denom0
        
        denom1 = sqrt_price_current - sqrt_price_lower
        if denom1 > 0 and amount1 > 0:
            L1 = float(amount1) / denom1
        
        # 取較小值（確保兩種 token 都足夠）
        if L0 > 0 and L1 > 0:
            return int(min(L0, L1))
        elif L0 > 0:
            return int(L0)
        elif L1 > 0:
            return int(L1)
        return 0
