from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.main import app


client = TestClient(app)
COMPARISON_ID = "a" * 32


def test_successful_impact_analysis():
    report = {
        "ai_status": "completed",
        "modified_rules_evaluated": 1,
    }

    output = Path("sample_phase4_impact.json")

    with patch(
        "app.api.impact_routes.assess",
        return_value=(report, output),
    ) as mocked_assess:
        response = client.post(
            f"/impact/{COMPARISON_ID}/analyze"
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "comparison_id": COMPARISON_ID,
        "ai_status": "completed",
        "modified_rules_evaluated": 1,
        "report_file": output.name,
        "review_required": True,
    }
    mocked_assess.assert_called_once_with(COMPARISON_ID)


def test_missing_comparison_returns_404():
    with patch(
        "app.api.impact_routes.assess",
        side_effect=FileNotFoundError,
    ):
        response = client.post(
            f"/impact/{COMPARISON_ID}/analyze"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Comparison files not found"
    )


def test_invalid_analysis_data_returns_422():
    with patch(
        "app.api.impact_routes.assess",
        side_effect=ValueError("Invalid comparison data"),
    ):
        response = client.post(
            f"/impact/{COMPARISON_ID}/analyze"
        )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Invalid comparison data"
    )


def test_unexpected_analysis_error_returns_500():
    with patch(
        "app.api.impact_routes.assess",
        side_effect=RuntimeError("Internal failure"),
    ):
        response = client.post(
            f"/impact/{COMPARISON_ID}/analyze"
        )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Impact analysis failed. Check server logs."
    )
