"""
績效分析器：計算回測結果和各種指標
"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import statistics


@dataclass
class PerformanceMetrics:
    """績效指標"""
    # 基本指標
    total_return: float = 0.0  # 總收益率 (%)
    annualized_return: float = 0.0  # 年化收益率 (%)
    max_drawdown: float = 0.0  # 最大回撤 (%)
    sharpe_ratio: float = 0.0  # 夏普比率
    volatility: float = 0.0  # 波動率
    
    # LP 特定指標
    total_fees_earned: float = 0.0  # 總手續費收入 (USDC)
    impermanent_loss: float = 0.0  # 無常損失 (%)
    liquidity_efficiency: float = 0.0  # 流動性效率
    
    # 時間序列數據
    value_history: List[Tuple[int, float]] = field(default_factory=list)  # (timestamp, value)
    return_history: List[float] = field(default_factory=list)
    
    # 統計信息
    num_swaps: int = 0
    num_mints: int = 0
    num_burns: int = 0
    avg_position_size: float = 0.0


class PerformanceAnalyzer:
    """績效分析器"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
    
    def calculate_returns(
        self,
        initial_value: float,
        final_value: float,
        days: float
    ) -> Tuple[float, float]:
        """計算總收益率和年化收益率"""
        if initial_value <= 0:
            return (0.0, 0.0)
        
        total_return = ((final_value - initial_value) / initial_value) * 100
        
        if days > 0:
            annualized_return = ((final_value / initial_value) ** (365 / days) - 1) * 100
        else:
            annualized_return = 0.0
        
        return (total_return, annualized_return)
    
    def calculate_max_drawdown(self, value_history: List[float]) -> float:
        """計算最大回撤"""
        if len(value_history) < 2:
            return 0.0
        
        peak = value_history[0]
        max_dd = 0.0
        
        for value in value_history:
            if value > peak:
                peak = value
            
            drawdown = ((peak - value) / peak) * 100 if peak > 0 else 0.0
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.0
    ) -> float:
        """計算夏普比率"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0.0
        
        if std_return == 0:
            return 0.0
        
        # 假設日收益率，年化
        sharpe = (mean_return - risk_free_rate) / std_return * (365 ** 0.5)
        return sharpe
    
    def calculate_volatility(self, returns: List[float]) -> float:
        """計算波動率（年化）"""
        if len(returns) < 2:
            return 0.0
        
        std_return = statistics.stdev(returns)
        # 年化波動率
        volatility = std_return * (365 ** 0.5)
        return volatility
    
    def analyze_performance(
        self,
        initial_value: float,
        final_value: float,
        value_history: List[Tuple[int, float]],
        start_timestamp: int,
        end_timestamp: int,
        num_swaps: int = 0,
        num_mints: int = 0,
        num_burns: int = 0,
        total_fees_earned: float = 0.0,
        impermanent_loss: float = 0.0
    ) -> PerformanceMetrics:
        """分析整體績效"""
        self.metrics = PerformanceMetrics()
        
        # 計算時間跨度（天）
        days = (end_timestamp - start_timestamp) / 86400 if end_timestamp > start_timestamp else 1
        
        # 計算收益率
        total_return, annualized_return = self.calculate_returns(
            initial_value, final_value, days
        )
        self.metrics.total_return = total_return
        self.metrics.annualized_return = annualized_return
        
        # 提取價值序列
        values = [v for _, v in value_history]
        self.metrics.value_history = value_history
        
        # 計算收益率序列
        if len(values) > 1:
            returns = []
            for i in range(1, len(values)):
                if values[i-1] > 0:
                    ret = ((values[i] - values[i-1]) / values[i-1]) * 100
                    returns.append(ret)
            self.metrics.return_history = returns
            
            # 計算最大回撤
            self.metrics.max_drawdown = self.calculate_max_drawdown(values)
            
            # 計算夏普比率
            if returns:
                self.metrics.sharpe_ratio = self.calculate_sharpe_ratio(returns)
                self.metrics.volatility = self.calculate_volatility(returns)
        
        # 統計信息
        self.metrics.num_swaps = num_swaps
        self.metrics.num_mints = num_mints
        self.metrics.num_burns = num_burns
        
        # LP 特定指標
        self.metrics.total_fees_earned = total_fees_earned
        self.metrics.impermanent_loss = impermanent_loss
        
        # 計算手續費收入佔總收益的比例
        if final_value > initial_value:
            total_return_value = final_value - initial_value
            if total_return_value > 0:
                self.metrics.liquidity_efficiency = (total_fees_earned / total_return_value) * 100 if total_return_value > 0 else 0.0
        
        return self.metrics
    
    def generate_report(self, metrics: PerformanceMetrics) -> str:
        """生成績效報告"""
        report = []
        report.append("=" * 60)
        report.append("AMM 回測績效報告")
        report.append("=" * 60)
        report.append("")
        
        report.append("【基本指標】")
        report.append(f"  總收益率: {metrics.total_return:.2f}%")
        report.append(f"  年化收益率: {metrics.annualized_return:.2f}%")
        report.append(f"  最大回撤: {metrics.max_drawdown:.2f}%")
        report.append(f"  夏普比率: {metrics.sharpe_ratio:.2f}")
        report.append(f"  波動率: {metrics.volatility:.2f}%")
        report.append("")
        
        report.append("【LP 特定指標】")
        report.append(f"  總手續費收入: {metrics.total_fees_earned:.2f} USDC")
        report.append(f"  無常損失: {metrics.impermanent_loss:.2f}%")
        report.append(f"  流動性效率: {metrics.liquidity_efficiency:.2f}")
        report.append("")
        
        report.append("【交易統計】")
        report.append(f"  Swap 次數: {metrics.num_swaps:,}")
        report.append(f"  Mint 次數: {metrics.num_mints:,}")
        report.append(f"  Burn 次數: {metrics.num_burns:,}")
        report.append("")
        
        return "\n".join(report)

