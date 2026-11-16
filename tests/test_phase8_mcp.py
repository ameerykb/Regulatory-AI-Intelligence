import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app import mcp_server


COMPARISON_ID = "a" * 32


def test_valid_comparison_id():
    assert mcp_server.validate_id(COMPARISON_ID) == COMPARISON_ID


def test_invalid_comparison_id():
    with pytest.raises(ValueError):
        mcp_server.validate_id("invalid-id")


def test_get_regulatory_comparison(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mcp_server, "COMPARISONS", tmp_path
    )

    expected = {
        "comparison_id": COMPARISON_ID,
        "changes": [],
    }

    path = tmp_path / f"{COMPARISON_ID}_changes.json"
    path.write_text(json.dumps(expected), encoding="utf-8")

    result = mcp_server.get_regulatory_comparison(
        COMPARISON_ID
    )

    assert result == expected


def test_missing_regulatory_comparison(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mcp_server, "COMPARISONS", tmp_path
    )

    with pytest.raises(FileNotFoundError):
        mcp_server.get_regulatory_comparison(
            COMPARISON_ID
        )


def test_get_policy_impact_report(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mcp_server, "COMPARISONS", tmp_path
    )

    expected = {
        "comparison_id": COMPARISON_ID,
        "ai_status": "completed",
        "review_required": True,
    }

    path = tmp_path / (
        f"{COMPARISON_ID}_phase4_impact.json"
    )

    path.write_text(json.dumps(expected), encoding="utf-8")

    result = mcp_server.get_policy_impact_report(
        COMPARISON_ID
    )

    assert result == expected


def test_missing_policy_impact_report(tmp_path, monkeypatch):
    monkeypatch.setattr(
        mcp_server, "COMPARISONS", tmp_path
    )

    with pytest.raises(FileNotFoundError):
        mcp_server.get_policy_impact_report(
            COMPARISON_ID
        )


def test_successful_mcp_impact_analysis():
    report = {
        "ai_status": "completed",
        "modified_rules_evaluated": 1,
        "policy_sections_checked": 8,
    }

    output = Path("sample_phase4_impact.json")

    with patch(
        "app.mcp_server.assess",
        return_value=(report, output),
    ) as mocked_assess:
        result = asyncio.run(
            mcp_server.analyze_policy_impact(
                COMPARISON_ID
            )
        )

    assert result == {
        "comparison_id": COMPARISON_ID,
        "ai_status": "completed",
        "modified_rules_evaluated": 1,
        "policy_sections_checked": 8,
        "report_file": output.name,
        "review_required": True,
    }

    mocked_assess.assert_called_once_with(COMPARISON_ID)


def test_invalid_mcp_analysis_id():
    with patch("app.mcp_server.assess") as mocked_assess:
        with pytest.raises(ValueError):
            asyncio.run(
                mcp_server.analyze_policy_impact(
                    "invalid-id"
                )
            )

    mocked_assess.assert_not_called()
