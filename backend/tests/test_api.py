from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "wind-ai-backend"}


def test_metrics_returns_both_turbines() -> None:
    body = client.get("/api/metrics").json()
    assert {model["turbine_id"] for model in body["models"]} == {1, 2}
    assert body["source"] in {"demo", "file"}


def test_forecast_48h_both_turbines() -> None:
    response = client.post(
        "/api/forecast",
        json={"forecast_date": "2026-02-01", "horizon_hours": 48, "turbine_ids": [2, 1]},
    )
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "completed"
    assert [t["turbine_id"] for t in body["turbines"]] == [1, 2]
    for turbine in body["turbines"]:
        assert len(turbine["points"]) == 48
        assert turbine["points"][0]["timestamp"] == "2026-02-01T00:00:00"
        assert all(0.0 <= p["predicted_power"] <= 1.0 for p in turbine["points"])

    assert [s["id"] for s in body["agent_steps"]] == [
        "fetch_weather",
        "validate_weather",
        "prepare_features",
        "run_model",
        "validate_prediction",
        "generate_explanation",
    ]
    assert all(s["status"] == "completed" for s in body["agent_steps"])
    assert body["summary"]["min_power"] <= body["summary"]["average_power"] <= body["summary"]["max_power"]
    assert body["explanation"]
    assert body["generated_at"].endswith("Z")


def test_forecast_is_deterministic() -> None:
    payload = {"forecast_date": "2026-02-14", "horizon_hours": 24, "turbine_ids": [1]}
    first = client.post("/api/forecast", json=payload).json()
    second = client.post("/api/forecast", json=payload).json()
    assert first["turbines"] == second["turbines"]


def test_forecast_rejects_date_outside_february() -> None:
    response = client.post(
        "/api/forecast",
        json={"forecast_date": "2026-03-01", "horizon_hours": 24, "turbine_ids": [1]},
    )
    assert response.status_code == 422
    assert "forecast_date must be between 2026-02-01 and 2026-02-28" in response.json()["detail"]


def test_forecast_rejects_invalid_horizon_and_turbines() -> None:
    response = client.post(
        "/api/forecast",
        json={"forecast_date": "2026-02-01", "horizon_hours": 12, "turbine_ids": [3]},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "horizon_hours" in detail
    assert "turbine_ids" in detail
