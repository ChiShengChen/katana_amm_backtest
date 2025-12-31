# All Strategies Comparison

## Market Conditions
- **Period**: 2025-07-18 to 2025-11-15
- **BTC Price**: $120,092.27 → $96,098.29 (**-19.98%**)
- **Initial Capital**: $10,000.00 (50% WBTC + 50% USDC)

---

## Performance Summary

| Strategy | Final Value | Return | Max Drawdown | Rebalances | Gas Cost |
|----------|-------------|--------|--------------|------------|----------|
| 🏆 **HODL 50/50** | $9,001 | -9.99% | 9.99% | 0 | $0 |
| Omnis AI (ATR) | $8,430 | -15.70% | 18.07% | 37 | $1,110 |
| Pure BTC | $8,002 | -19.98% | 9.99% | 0 | $0 |
| Charm Alpha Vault | $5,291 | -47.09% | 99.31% | 55 | $1,650 |
| ❌ **Steer Classic (±300 ticks)** | $100 | -99.00% | 100.00% | 44 | $1,320 |
| ❌ **Steer Elastic (BB 2.0σ)** | $100 | -99.00% | 100.00% | 698 | $20,940 |

---

## Strategy Details

### 1. Omnis AI (ATR Dynamic Range)

**Core Concept**: Use ATR (Average True Range) to dynamically adjust LP range

**Parameters**:
| Parameter | Value |
|-----------|-------|
| ATR Period | 14 |
| ATR Multiplier | 2.0 |
| Rebalance Interval | 180 seconds |
| Price Deviation Threshold | 3% |

**Key Feature**: Automatically widens range during high volatility, reducing IL

---

### 2. HODL 50/50 (Baseline)

Simple buy-and-hold strategy:
- 50% in WBTC
- 50% in USDC
- No rebalancing
- No fees

---

### 3. Pure BTC (Baseline)

100% exposure to BTC price movement:
- Full upside capture
- Full downside exposure

---

### 4. Charm Alpha Vault (Passive)

**Core Concept**: No swaps, only limit orders

**Parameters**:
| Parameter | Value |
|-----------|-------|
| Base Threshold | 600 ticks (~6%) |
| Limit Threshold | 1200 ticks (~12%) |
| Rebalance Interval | 48 hours |
| Protocol Fee | 2% |

---

### 5. Steer Classic (Fixed Width)

**Core Concept**: Fixed range width, price-triggered rebalance

**Parameters**:
| Parameter | Value |
|-----------|-------|
| Position Width | 600 ticks (~6%) |
| Rebalance Threshold | 500 bps (5%) |
| Protocol Fee | 15% |

---

### 6. Steer Elastic (Bollinger Bands)

**Core Concept**: Dynamic range based on Bollinger Bands

**Parameters**:
| Parameter | Value |
|-----------|-------|
| SMA Period | 20 |
| Std Multiplier | 2.0 |
| Min Width | 120 ticks |
| Protocol Fee | 15% |

⚠️ **Warning**: Frequent rebalancing leads to excessive gas costs!

---

## Strategy Comparison Matrix

| Feature | Omnis AI | Charm Alpha | Steer Classic | Steer Elastic |
|---------|----------|-------------|---------------|---------------|
| Range Type | Dynamic (ATR) | Fixed | Fixed | Dynamic (BB) |
| Swap Required | Yes | No | Yes | Yes |
| Protocol Fee | 0% | 2% | 15% | 15% |
| Gas Cost | Medium | Low | Medium | **High** ⚠️ |
| Best For | All markets | Ranging | Trending | (Avoid) |

---

## Key Findings

### 🏆 Winner: HODL 50/50
- **Return**: -9.99%
- **Max Drawdown**: 9.99%
- **Final Value**: $9,001.02

### Strategy Rankings
1. **HODL 50/50**: -9.99%
2. **Omnis AI (ATR)**: -15.70%
3. **Pure BTC**: -19.98%
4. **Charm Alpha Vault**: -47.09%
5. **Steer Classic (±300 ticks)**: -99.00%
6. **Steer Elastic (BB 2.0σ)**: -99.00%

### ⚠️ Critical Warning
**Steer Elastic (BB 2.0σ)** lost **99.0%** due to:
- 698 rebalances
- Gas costs: $20,940
- Over-trading in volatile market

---

## Charts

1. **strategy_comparison_value.png** - Portfolio value curves over time
2. **total_return_comparison.png** - Total return comparison bar chart
3. **crash_comparison_bar.png** - Maximum drawdown comparison
4. **drawdown_comparison.png** - Drawdown curves over time
5. **cost_efficiency.png** - Rebalance frequency & gas costs
6. **strategy_dashboard.png** - Comprehensive dashboard with all metrics

---

## Strategy Selection Guide

| Market Condition | Recommended | Reason |
|------------------|-------------|--------|
| Ranging/Sideways | Charm Alpha | Low cost, passive |
| Trending | Steer Classic | Quick following |
| High Volatility | Omnis AI (ATR) | Dynamic protection |
| Uncertain | Omnis AI (ATR) | Best risk-adjusted |
| **Avoid** | Steer Elastic | Gas destroys profits |

---

*Generated: 2026-01-01 05:05:32*
*Powered by Katana Backtest System*
