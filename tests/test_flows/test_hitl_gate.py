# tests/test_flows/test_hitl_gate.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from csqaq.main import run_query, RunQueryResult


class TestRunQueryResult:
    def test_low_risk_no_confirmation(self):
        r = RunQueryResult(
            summary="大盘平稳", action_detail="可以建仓",
            risk_level="low", requires_confirmation=False,
        )
        assert r.requires_confirmation is False
        assert r.full_text() == "大盘平稳\n\n可以建仓"

    def test_high_risk_needs_confirmation(self):
        r = RunQueryResult(
            summary="大盘暴跌", action_detail="建议清仓",
            risk_level="high", requires_confirmation=True,
        )
        assert r.requires_confirmation is True
        assert r.summary_text() == "大盘暴跌"
