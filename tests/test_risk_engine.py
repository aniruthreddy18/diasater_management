"""
Test Risk Engine classification and configurable threshold behavior.
"""

import pytest
from core.models import RiskLevel
from risk.risk_engine import RiskEngine
from config.settings import RiskThresholds


def test_risk_level_boundaries():
    engine = RiskEngine()

    assert engine.classify_risk_score(0.0) == RiskLevel.NORMAL
    assert engine.classify_risk_score(20.0) == RiskLevel.NORMAL
    assert engine.classify_risk_score(25.0) == RiskLevel.LOW
    assert engine.classify_risk_score(45.0) == RiskLevel.LOW
    assert engine.classify_risk_score(50.0) == RiskLevel.MEDIUM
    assert engine.classify_risk_score(68.0) == RiskLevel.MEDIUM
    assert engine.classify_risk_score(70.0) == RiskLevel.HIGH
    assert engine.classify_risk_score(80.0) == RiskLevel.HIGH
    assert engine.classify_risk_score(85.0) == RiskLevel.EXTREME
    assert engine.classify_risk_score(100.0) == RiskLevel.EXTREME


def test_risk_score_clamping():
    engine = RiskEngine()
    assert engine.clamp_score(-10.5) == 0.0
    assert engine.clamp_score(125.8) == 100.0
    assert engine.clamp_score(55.432) == 55.4


def test_alert_trigger_criteria():
    engine = RiskEngine()

    # If min level is HIGH:
    assert engine.should_trigger_alert(RiskLevel.NORMAL, 15.0, min_level="HIGH") is False
    assert engine.should_trigger_alert(RiskLevel.LOW, 35.0, min_level="HIGH") is False
    assert engine.should_trigger_alert(RiskLevel.MEDIUM, 60.0, min_level="HIGH") is False
    assert engine.should_trigger_alert(RiskLevel.HIGH, 75.0, min_level="HIGH") is True
    assert engine.should_trigger_alert(RiskLevel.EXTREME, 92.0, min_level="HIGH") is True

    # If min level is lowered to MEDIUM:
    assert engine.should_trigger_alert(RiskLevel.MEDIUM, 55.0, min_level="MEDIUM") is True


def test_risk_radii_calculation():
    engine = RiskEngine()
    
    # Test Wildfire at 85% risk
    wf_radii = engine.calculate_risk_radii_km("WILDFIRE", 85.0)
    assert wf_radii["very_danger_km"] == 1.27
    assert wf_radii["danger_km"] == 2.98
    assert wf_radii["moderate_danger_km"] == 5.10
    assert wf_radii["very_danger_km"] < wf_radii["danger_km"] < wf_radii["moderate_danger_km"]

    # Test Flood at 60% risk
    fl_radii = engine.calculate_risk_radii_km("FLASH_FLOOD", 60.0)
    assert fl_radii["very_danger_km"] == 0.48
    assert fl_radii["danger_km"] == 1.20
    assert fl_radii["moderate_danger_km"] == 2.40
