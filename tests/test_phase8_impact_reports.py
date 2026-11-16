import json

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.api import impact_routes


client = TestClient(app)

COMPARISON_ID = "a" * 32


@pytest.fixture
def temporary_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(
        impact_routes,
        "REPORT_DIR",
        tmp_path,
    )

    report = {
        "comparison_id": COMPARISON_ID,
        "ai_status": "completed",
        "policy_sections_checked": 8,
        "modified_rules_evaluated": 1,
        "review_required": True,
        "findings": [],
        "disclaimer": "Human legal review required.",
    }

    path = tmp_path / (
        f"{COMPARISON_ID}_phase4_impact.json"
    )

    path.write_text(
        json.dumps(report),
        encoding="utf-8",
    )

    return report, path


def test_successful_report_retrieval(temporary_reports):
    report, _ = temporary_reports

    response = client.get(
        f"/impact/{COMPARISON_ID}"
    )

    assert response.status_code == 200
    assert response.json() == report


def test_successful_json_download(temporary_reports):
    report, _ = temporary_reports

    response = client.get(
        f"/impact/{COMPARISON_ID}/download?format=json"
    )

    assert response.status_code == 200
    assert response.json() == report
    assert "application/json" in response.headers["content-type"]


def test_successful_markdown_download(temporary_reports):
    report, _ = temporary_reports

    response = client.get(
        f"/impact/{COMPARISON_ID}/download?format=md"
    )

    assert response.status_code == 200
    assert "text/markdown" in response.headers["content-type"]
    assert "# Regulatory Policy Impact Assessment" in response.text
    assert COMPARISON_ID in response.text
    assert report["disclaimer"] in response.text


def test_missing_report_returns_404(tmp_path, monkeypatch):
    monkeypatch.setattr(
        impact_routes,
        "REPORT_DIR",
        tmp_path,
    )

    response = client.get(
        f"/impact/{COMPARISON_ID}"
    )

    assert response.status_code == 404
    assert "Impact report not found" in response.json()["detail"]


def test_corrupted_report_returns_500(temporary_reports):
    _, path = temporary_reports

    path.write_text(
        "{invalid json",
        encoding="utf-8",
    )

    response = client.get(
        f"/impact/{COMPARISON_ID}"
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Saved report could not be read."
    )


def test_unsupported_download_format(temporary_reports):
    response = client.get(
        f"/impact/{COMPARISON_ID}/download?format=pdf"
    )

    assert response.status_code == 422
