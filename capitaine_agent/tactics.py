"""Tactics engine — strategy selection and decision-making."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StrategyType(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DELEGATE = "delegate"
    ADAPTIVE = "adaptive"
    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"


@dataclass
class Strategy:
    """A tactical strategy with conditions for when it's appropriate."""
    name: str
    strategy_type: StrategyType
    description: str = ""
    suitability_fn: str = "default"  # named suitability function
    priority_boost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TacticalContext:
    """Snapshot of the operational context used for strategy selection."""
    time_pressure: float = 0.0  # 0=none, 1=critical
    resource_availability: float = 1.0  # 0=depleted, 1=full
    risk_level: float = 0.0  # 0=safe, 1=dangerous
    crew_size: int = 0
    objective_count: int = 0
    completed_ratio: float = 0.0
    failure_count: int = 0
    custom_factors: dict[str, float] = field(default_factory=dict)


class TacticsEngine:
    """Selects and evaluates strategies based on tactical context."""

    def __init__(self) -> None:
        self.strategies: dict[str, Strategy] = {}
        self._builtin_strategies()

    def _builtin_strategies(self) -> None:
        """Register built-in strategies."""
        builtins = [
            Strategy("full_parallel", StrategyType.PARALLEL,
                     "Execute all independent objectives simultaneously",
                     suitability_fn="parallel_default"),
            Strategy("sequential_careful", StrategyType.SEQUENTIAL,
                     "Execute objectives one at a time with validation",
                     suitability_fn="sequential_default"),
            Strategy("delegate_all", StrategyType.DELEGATE,
                     "Delegate objectives to specialized crew members",
                     suitability_fn="delegate_default"),
            Strategy("adaptive_hybrid", StrategyType.ADAPTIVE,
                     "Mix strategies based on per-objective analysis",
                     suitability_fn="adaptive_default"),
            Strategy("conservative_hold", StrategyType.CONSERVATIVE,
                     "Pause and reassess; only proceed with safe bets",
                     suitability_fn="conservative_default"),
            Strategy("aggressive_push", StrategyType.AGGRESSIVE,
                     "Push through remaining objectives at maximum speed",
                     suitability_fn="aggressive_default"),
        ]
        for s in builtins:
            self.strategies[s.name] = s

    # ── Strategy registration ──

    def register_strategy(self, strategy: Strategy) -> None:
        self.strategies[strategy.name] = strategy

    def remove_strategy(self, name: str) -> bool:
        return self.strategies.pop(name, None) is not None

    def get_strategy(self, name: str) -> Strategy | None:
        return self.strategies.get(name)

    # ── Suitability scoring ──

    def _score_sequential(self, ctx: TacticalContext) -> float:
        """Sequential is good when risk is high or resources are low."""
        score = 0.3
        score += ctx.risk_level * 0.3
        score += (1.0 - ctx.resource_availability) * 0.2
        score += (1.0 - ctx.completed_ratio) * 0.1
        if ctx.crew_size <= 2:
            score += 0.2
        return min(score, 1.0)

    def _score_parallel(self, ctx: TacticalContext) -> float:
        """Parallel is good when resources and crew are available, risk is low."""
        score = 0.1
        score += ctx.resource_availability * 0.3
        score += (1.0 - ctx.risk_level) * 0.2
        if ctx.crew_size >= 3:
            score += 0.2
        if ctx.time_pressure > 0.6:
            score += 0.2
        return min(score, 1.0)

    def _score_delegate(self, ctx: TacticalContext) -> float:
        """Delegate when crew is available and specialized."""
        score = 0.2
        if ctx.crew_size >= 2:
            score += 0.3
        score += ctx.resource_availability * 0.2
        score += (1.0 - ctx.time_pressure) * 0.15
        if ctx.objective_count >= 3:
            score += 0.15
        return min(score, 1.0)

    def _score_adaptive(self, ctx: TacticalContext) -> float:
        """Adaptive is a good default; thrives on complexity."""
        score = 0.4
        score += min(ctx.objective_count / 10, 0.2)
        if 0.3 <= ctx.risk_level <= 0.7:
            score += 0.2
        if ctx.failure_count > 0:
            score += 0.2
        return min(score, 1.0)

    def _score_conservative(self, ctx: TacticalContext) -> float:
        """Conservative when things are going badly."""
        score = 0.1
        score += ctx.risk_level * 0.3
        score += min(ctx.failure_count / 3, 0.3)
        score += (1.0 - ctx.resource_availability) * 0.2
        if ctx.completed_ratio < 0.3 and ctx.failure_count > 1:
            score += 0.2
        return min(score, 1.0)

    def _score_aggressive(self, ctx: TacticalContext) -> float:
        """Aggressive when time pressure is critical and we have resources."""
        score = 0.1
        score += ctx.time_pressure * 0.4
        score += ctx.resource_availability * 0.2
        score += (1.0 - ctx.risk_level) * 0.1
        if ctx.completed_ratio > 0.7:
            score += 0.2
        return min(score, 1.0)

    def score_strategies(self, ctx: TacticalContext) -> list[tuple[Strategy, float]]:
        """Score all registered strategies against the context.

        Returns list of (strategy, score) sorted by score descending.
        """
        scorers = {
            "parallel_default": self._score_parallel,
            "sequential_default": self._score_sequential,
            "delegate_default": self._score_delegate,
            "adaptive_default": self._score_adaptive,
            "conservative_default": self._score_conservative,
            "aggressive_default": self._score_aggressive,
        }
        results: list[tuple[Strategy, float]] = []
        for s in self.strategies.values():
            scorer = scorers.get(s.suitability_fn)
            score = scorer(ctx) if scorer else 0.5
            score += s.priority_boost
            results.append((s, round(min(score, 1.0), 3)))
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def recommend(self, ctx: TacticalContext) -> Strategy:
        """Return the best strategy for the given context."""
        scored = self.score_strategies(ctx)
        return scored[0][0] if scored else Strategy("sequential_careful", StrategyType.SEQUENTIAL)

    def recommend_with_score(self, ctx: TacticalContext) -> tuple[Strategy, float]:
        scored = self.score_strategies(ctx)
        return scored[0] if scored else (Strategy("sequential_careful", StrategyType.SEQUENTIAL), 0.5)
