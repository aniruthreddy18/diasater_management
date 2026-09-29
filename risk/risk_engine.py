"""
Risk Engine & Severity Classification
Multi-Disaster Early Warning System
"""

from typing import Tuple
from config.settings import settings
from core.models import RiskLevel


class RiskEngine:
    """
    Evaluates and classifies risk scores into qualitative RiskLevel categories.
    Implements configurable threshold boundaries.
    """

    def __init__(self, thresholds=None):
        self.thresholds = thresholds or settings.risk

    def classify_risk_score(self, score: float) -> RiskLevel:
        """
        Map a continuous risk score (0.0 - 100.0) to a categorized RiskLevel.
        """
        score = max(0.0, min(100.0, score))

        if score <= self.thresholds.normal_max:
            return RiskLevel.NORMAL
        elif score <= self.thresholds.low_max:
            return RiskLevel.LOW
        elif score <= self.thresholds.medium_max:
            return RiskLevel.MEDIUM
        elif score <= self.thresholds.high_max:
            return RiskLevel.HIGH
        else:
            return RiskLevel.EXTREME

    def should_trigger_alert(
        self,
        risk_level: RiskLevel,
        risk_score: float,
        min_level: str = "HIGH",
    ) -> bool:
        """
        Determine if an evaluated risk event warrants an outbound alert.
        """
        level_order = [
            RiskLevel.NORMAL,
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.EXTREME,
        ]

        try:
            min_target = RiskLevel(min_level.upper())
            min_idx = level_order.index(min_target)
        except ValueError:
            min_idx = level_order.index(RiskLevel.HIGH)

        current_idx = level_order.index(risk_level)
        return current_idx >= min_idx

    @staticmethod
    def clamp_score(score: float) -> float:
        """Ensure risk score stays within 0.0 to 100.0 bounds."""
        return max(0.0, min(100.0, round(score, 1)))

    @staticmethod
    def calculate_risk_radii_km(hazard_type: str, risk_score: float) -> dict:
        """
        Computes three concentric impact radii (in kilometers) around the disaster point
        based on the disaster type and calculated risk percentage.
        - Very Danger: Core evacuation zone
        - Danger: High warning zone
        - Moderate Danger: Advisory perimeter
        """
        pct = max(0.0, min(100.0, risk_score)) / 100.0
        ht = str(hazard_type).upper()

        if "WILD" in ht or "FIRE" in ht:
            r_very = round(max(0.2, pct * 1.5), 2)
            r_danger = round(max(0.5, pct * 3.5), 2)
            r_mod = round(max(1.0, pct * 6.0), 2)
        elif "FLOOD" in ht:
            r_very = round(max(0.15, pct * 0.8), 2)
            r_danger = round(max(0.4, pct * 2.0), 2)
            r_mod = round(max(0.8, pct * 4.0), 2)
        elif "LANDSLIDE" in ht:
            r_very = round(max(0.1, pct * 0.4), 2)
            r_danger = round(max(0.25, pct * 1.0), 2)
            r_mod = round(max(0.5, pct * 2.5), 2)
        else:
            r_very = round(max(0.2, pct * 1.0), 2)
            r_danger = round(max(0.5, pct * 2.5), 2)
            r_mod = round(max(1.0, pct * 5.0), 2)

        return {
            "very_danger_km": r_very,
            "danger_km": r_danger,
            "moderate_danger_km": r_mod,
        }


# Global risk engine instance
risk_engine = RiskEngine()
