"""
End-to-End API and Integration Tests
"""

import pytest
from fastapi.testclient import TestClient
from api.app import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_serve_dashboard_index(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "MULTI-DISASTER EARLY WARNING SYSTEM" in resp.text
    assert "Leaflet" in resp.text


def test_telemetry_ingestion_and_multi_disaster_api(client):
    # 1. Reset states
    reset_resp = client.post("/api/v1/reset")
    assert reset_resp.status_code == 200

    # 2. Check initial status
    status_resp = client.get("/api/v1/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["active_hazard_count"] == 0

    # 3. Ingest Landslide critical packet
    ls_payload = {
        "device_id": "LANDSLIDE_001",
        "hazard_type": "LANDSLIDE",
        "latitude": 17.3920,
        "longitude": 78.4720,
        "sensor_data": {
            "tilt_angle": 28.5,
            "soil_moisture": 91.0,
            "vibration_intensity": 0.88,
        },
    }
    ls_resp = client.post("/api/v1/telemetry", json=ls_payload)
    assert ls_resp.status_code == 200
    ls_event = ls_resp.json()
    assert ls_event["detected"] is True
    assert ls_event["hazard_type"] == "LANDSLIDE"

    # 4. Ingest Wildfire critical packet (should corroborate with FIRMS +15%)
    wf_payload = {
        "device_id": "FIRE_001",
        "hazard_type": "WILDFIRE",
        "latitude": 17.3850,
        "longitude": 78.4867,
        "sensor_data": {
            "temperature": 55.0,
            "humidity": 12.0,
            "smoke": 800.0,
            "flame_detected": True,
        },
    }
    wf_resp = client.post("/api/v1/telemetry", json=wf_payload)
    assert wf_resp.status_code == 200
    wf_event = wf_resp.json()
    assert wf_event["detected"] is True
    assert wf_event["hazard_type"] == "WILDFIRE"
    assert wf_event["firms_confirmed"] is True
    assert wf_event["firms_adjustment"] == 15.0

    # 5. Verify simultaneous status has BOTH Landslide and Wildfire active!
    status_2 = client.get("/api/v1/status").json()
    assert status_2["active_hazard_count"] == 2
    assert status_2["landslide"]["detected"] is True
    assert status_2["wildfire"]["detected"] is True
    assert status_2["flash_flood"]["detected"] is False  # Still normal


def test_simulation_scenario_all_critical(client):
    sim_resp = client.post("/api/v1/simulate", json={"scenario": "simultaneous_all_critical"})
    assert sim_resp.status_code == 200
    data = sim_resp.json()
    assert data["scenario"] == "simultaneous_all_critical"
    assert len(data["processed_events"]) == 3

    # All three must be active simultaneously
    status = data["multi_disaster_status"]
    assert status["active_hazard_count"] == 3
    assert status["wildfire"]["detected"] is True
    assert status["flash_flood"]["detected"] is True
    assert status["landslide"]["detected"] is True


def test_alerts_history_api(client):
    alerts_resp = client.get("/api/v1/alerts")
    assert alerts_resp.status_code == 200
    alerts = alerts_resp.json()
    assert isinstance(alerts, list)
    assert len(alerts) > 0


def test_websocket_stream_connection(client):
    with client.websocket_connect("/ws") as ws:
        init_msg = ws.receive_json()
        assert init_msg["type"] == "INITIAL_STATE"
        assert "status" in init_msg["data"]
        assert "receiver_gps" in init_msg["data"]

        # Heartbeat ping
        ws.send_text("ping")
        pong = ws.receive_text()
        assert pong == "pong"


def test_telegram_status_api(client):
    resp = client.get("/api/v1/telegram/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "configured" in data
    assert "mode" in data


def test_manual_emergency_broadcast_api(client):
    broadcast_payload = {
        "hazard_type": "FLASH_FLOOD",
        "locality_name": "Sector 4 Riverbank",
        "latitude": 17.3850,
        "longitude": 78.4867,
        "risk_score": 88.0,
        "instructions": "Immediate evacuation ordered. High water surge incoming.",
        "device_id": "MANUAL_TEST_NODE",
    }
    resp = client.post("/api/v1/alerts/broadcast", json=broadcast_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "dispatched"
    assert data["event"]["hazard_type"] == "FLASH_FLOOD"
    assert data["event"]["detected"] is True
    assert data["event"]["final_risk_score"] == 88.0
    assert data["alert"] is not None


def test_landslide_stations_api(client):
    # 1. Fetch stations list
    resp = client.get("/api/v1/landslides/stations")
    assert resp.status_code == 200
    data = resp.json()
    assert "stations" in data
    assert len(data["stations"]) >= 7
    assert data["active_station"]["id"] == "STN-NE01"

    # 2. Switch active station to Wayanad
    switch_resp = client.post("/api/v1/landslides/active-station", json={"station_id": "STN-WG02"})
    assert switch_resp.status_code == 200
    switch_data = switch_resp.json()
    assert switch_data["active_station"]["id"] == "STN-WG02"
    assert switch_data["active_station"]["district"] == "Wayanad"

    # Reset back to STN-NE01
    client.post("/api/v1/landslides/active-station", json={"station_id": "STN-NE01"})

