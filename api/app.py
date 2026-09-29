"""
FastAPI Backend Application & REST/WebSocket Endpoints
Multi-Disaster Early Warning System
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config.settings import settings
from core.models import (
    StandardPacket,
    RawIngestPacket,
    HazardEvent,
    MultiDisasterStatus,
    AlertRecord,
    HazardType,
)
from core.event_bus import event_bus
from receiver.central_receiver import central_receiver
from classifier.data_classifier import data_classifier
from state.state_manager import state_manager
from alerts.telegram_bot import telegram_dispatcher
from firms.client import firms_client, FirmsHotspot
from simulator.hardware_nodes import (
    LandslideHardwareNode,
    FloodHardwareNode,
    WildfireHardwareNode,
)
from core.landslide_stations import landslide_station_manager
from core.flood_stations import flood_station_manager
from core.wildfire_stations import wildfire_station_manager
from .websocket_manager import ws_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


# Pipeline Orchestration Helper
async def process_incoming_packet(packet: StandardPacket) -> HazardEvent:
    """
    Execute full pipeline:
    Standard Packet -> Data Classifier -> Domain Engine -> FIRMS Check (if Wildfire) ->
    State Manager Update -> Telegram Alert Check -> WebSocket Broadcast
    """
    # 1. Route and evaluate through independent engine
    hazard_event = await data_classifier.route_and_process(packet)

    # 2. Update simultaneous independent state store
    await state_manager.update_hazard_state(hazard_event)

    # 3. Check and dispatch Telegram alert if risk threshold exceeded
    alert_record = await telegram_dispatcher.send_event_alert(hazard_event)

    # 4. Broadcast live update to all connected map dashboards
    status_snapshot = await state_manager.get_multi_disaster_status()
    await ws_manager.broadcast(
        message_type="HAZARD_UPDATE",
        data={
            "event": hazard_event.model_dump(),
            "status": status_snapshot.model_dump(),
            "alert": alert_record.model_dump() if alert_record else None,
        },
    )

    return hazard_event


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    logger.info("Initializing %s v%s", settings.app_name, settings.version)
    logger.info("Central Receiver GPS: (%.4f, %.4f)",
                central_receiver.default_latitude, central_receiver.default_longitude)
    if telegram_dispatcher.is_configured():
        logger.info("Telegram Alerts: ACTIVE (Chat ID: %s)", telegram_dispatcher.chat_id)
    else:
        logger.info("Telegram Alerts: RUNNING IN LOCAL/SIMULATION MODE (Set TELEGRAM_BOT_TOKEN & CHAT_ID to enable live Telegram push)")

    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Backend API and Central Receiver for Multi-Disaster Early Warning System (Landslides, Flash Floods, Wildfires)",
    lifespan=lifespan,
)

# Request Models
class SimulateRequest(BaseModel):
    scenario: str  # "wildfire_critical", "flood_critical", "landslide_critical", "simultaneous_all_critical", "reset_normal"


class UpdateGpsRequest(BaseModel):
    latitude: float
    longitude: float


class AddHotspotRequest(BaseModel):
    latitude: float
    longitude: float
    brightness: float = 330.0
    confidence: str = "high"


class TelegramTestRequest(BaseModel):
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None


class TelegramConfigRequest(BaseModel):
    bot_token: str
    chat_id: str


class ManualBroadcastRequest(BaseModel):
    hazard_type: str = "WILDFIRE"
    locality_name: str = "Gandipet Locality"
    latitude: float = 17.3918
    longitude: float = 78.3194
    risk_score: float = 85.0
    instructions: str = "Immediate evacuation ordered. Proceed to nearest safety zone."
    device_id: str = "MANUAL_COMMAND_DISPATCH"


# ==============================================================================
# REST API Endpoints
# ==============================================================================

@app.post("/api/v1/telemetry", response_model=HazardEvent)
async def ingest_telemetry(raw_packet: RawIngestPacket):
    """
    Central Receiver telemetry ingestion endpoint.
    Accepts raw or structured packet from any of the three independent hardware nodes.
    Pairs with GPS coordinates, classifies hazard, evaluates risk, updates state, and alerts.
    """
    try:
        # Ingest and normalize through Central Receiver
        standard_packet = central_receiver.ingest_raw_packet(raw_packet.model_dump())
        event = await process_incoming_packet(standard_packet)
        return event
    except Exception as e:
        logger.error("Error processing telemetry packet: %s", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/status", response_model=MultiDisasterStatus)
async def get_system_status():
    """
    Get current simultaneous status of all three disaster types.
    Confirms that all three hazard states are maintained independently.
    """
    status = await state_manager.get_multi_disaster_status()
    status.receiver_coordinates = central_receiver.get_receiver_gps()
    return status


@app.get("/api/v1/events", response_model=List[HazardEvent])
async def get_recent_events(limit: int = Query(default=50, ge=1, le=100)):
    """Get recent hazard evaluation events."""
    return await state_manager.get_recent_events(limit=limit)


@app.get("/api/v1/alerts", response_model=List[AlertRecord])
async def get_recent_alerts(limit: int = Query(default=50, ge=1, le=100)):
    """Get history of dispatched early warning alerts."""
    return telegram_dispatcher.get_recent_alerts(limit=limit)


class StationSelectRequest(BaseModel):
    station_id: str


@app.get("/api/v1/landslides/stations")
async def get_landslide_stations():
    """Get all high-vulnerability national landslide monitoring stations and current active binding."""
    return {
        "stations": landslide_station_manager.get_all_stations(),
        "active_station": landslide_station_manager.get_active_field_station(),
    }


@app.post("/api/v1/landslides/active-station")
async def select_active_landslide_station(req: StationSelectRequest):
    """Switch the station bound to the live field IoT unit."""
    success = landslide_station_manager.set_active_station(req.station_id)
    if not success:
        raise HTTPException(status_code=404, detail="Station not found")
    st = landslide_station_manager.get_active_field_station()
    return {"success": True, "active_station": st}


@app.get("/api/v1/floods/stations")
async def get_flood_stations():
    """Get all high-vulnerability national flash flood monitoring stations and current active binding."""
    return {
        "stations": flood_station_manager.get_all_stations(),
        "active_station": flood_station_manager.get_active_field_station(),
    }


@app.post("/api/v1/floods/active-station")
async def select_active_flood_station(req: StationSelectRequest):
    """Switch the flood station bound to the live field IoT unit."""
    success = flood_station_manager.set_active_station(req.station_id)
    if not success:
        raise HTTPException(status_code=404, detail="Station not found")
    st = flood_station_manager.get_active_field_station()
    return {"success": True, "active_station": st}


@app.get("/api/v1/wildfires/stations")
async def get_wildfire_stations():
    """Get all high-vulnerability national wildfire and fire-gas stations and current active binding."""
    return {
        "stations": wildfire_station_manager.get_all_stations(),
        "active_station": wildfire_station_manager.get_active_field_station(),
    }


@app.post("/api/v1/wildfires/active-station")
async def select_active_wildfire_station(req: StationSelectRequest):
    """Switch the wildfire station bound to the live field IoT unit."""
    success = wildfire_station_manager.set_active_station(req.station_id)
    if not success:
        raise HTTPException(status_code=404, detail="Station not found")
    st = wildfire_station_manager.get_active_field_station()
    return {"success": True, "active_station": st}


@app.get("/api/v1/telegram/status")
async def get_telegram_status():
    """Get current Telegram Bot connection and mode status."""
    return {
        "configured": telegram_dispatcher.is_configured(),
        "chat_id": telegram_dispatcher.chat_id,
        "has_token": bool(telegram_dispatcher.bot_token),
        "mode": "LIVE" if telegram_dispatcher.is_configured() else "SIMULATION",
    }


@app.post("/api/v1/telegram/test")
async def test_telegram_connection(req: TelegramTestRequest):
    """Send test alert to verify Telegram bot connectivity."""
    result = await telegram_dispatcher.test_connection(req.bot_token, req.chat_id)
    return result


@app.post("/api/v1/telegram/config")
async def update_telegram_config(req: TelegramConfigRequest):
    """Save Telegram bot credentials, persist to .env, and test connection."""
    result = await telegram_dispatcher.test_connection(req.bot_token, req.chat_id)
    if result["success"]:
        telegram_dispatcher.update_credentials(req.bot_token, req.chat_id)
        # Persist to .env
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        try:
            lines = []
            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    lines = f.readlines()
            token_set = False
            chat_set = False
            new_lines = []
            for line in lines:
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    new_lines.append(f"TELEGRAM_BOT_TOKEN={req.bot_token.strip()}\n")
                    token_set = True
                elif line.startswith("TELEGRAM_CHAT_ID="):
                    new_lines.append(f"TELEGRAM_CHAT_ID={req.chat_id.strip()}\n")
                    chat_set = True
                else:
                    new_lines.append(line)
            if not token_set:
                new_lines.append(f"TELEGRAM_BOT_TOKEN={req.bot_token.strip()}\n")
            if not chat_set:
                new_lines.append(f"TELEGRAM_CHAT_ID={req.chat_id.strip()}\n")
            with open(env_path, "w") as f:
                f.writelines(new_lines)
            logger.info("Updated Telegram credentials in .env and runtime.")
        except Exception as e:
            logger.warning("Could not persist Telegram credentials to .env: %s", e)

    return result


@app.post("/api/v1/alerts/broadcast")
async def broadcast_manual_alert(req: ManualBroadcastRequest):
    """
    Manually dispatch an emergency evacuation alert to locality residents.
    Dispatches via Telegram, plots on digital map with concentric risk circles, and logs to Alert Dashboard.
    """
    from risk.risk_engine import risk_engine
    
    ht = StandardPacket.normalize_hazard_type(req.hazard_type)
    score = risk_engine.clamp_score(req.risk_score)
    risk_lvl = risk_engine.classify_risk_score(score)
    
    event = HazardEvent(
        event_id=f"EV_MANUAL_{uuid.uuid4().hex[:6].upper()}",
        device_id=req.device_id,
        hazard_type=ht,
        latitude=req.latitude,
        longitude=req.longitude,
        timestamp=datetime.now(timezone.utc).isoformat(),
        detected=True,
        base_risk_score=score,
        firms_confirmed=None,
        nearest_firms_distance_km=None,
        firms_adjustment=0.0,
        final_risk_score=score,
        risk_level=risk_lvl,
        sensor_data={"locality": req.locality_name, "instructions": req.instructions},
        message=f"LOCALITY ALERT [{req.locality_name}]: {req.instructions}",
    )
    
    # Update state store
    await state_manager.update_hazard_state(event)
    
    # Send Telegram alert (forced, bypasses cooldown)
    alert_record = await telegram_dispatcher.send_event_alert(event, force=True)
    
    # Broadcast to all connected dashboards via WebSocket
    status_snapshot = await state_manager.get_multi_disaster_status()
    await ws_manager.broadcast(
        message_type="HAZARD_UPDATE",
        data={
            "event": event.model_dump(),
            "status": status_snapshot.model_dump(),
            "alert": alert_record.model_dump() if alert_record else None,
        },
    )
    
    return {
        "status": "dispatched",
        "event": event.model_dump(),
        "alert": alert_record.model_dump() if alert_record else None,
    }


@app.post("/api/v1/receiver/gps")
async def update_receiver_gps(gps: UpdateGpsRequest):
    """Update Central Receiver GPS coordinates."""
    central_receiver.update_receiver_gps(gps.latitude, gps.longitude)
    return {"message": "Receiver GPS updated", "gps": central_receiver.get_receiver_gps()}


@app.post("/api/v1/reset")
async def reset_monitoring():
    """Reset all disaster states back to NORMAL."""
    await state_manager.reset_all_states()
    status = await state_manager.get_multi_disaster_status()
    await ws_manager.broadcast("STATUS_RESET", {"status": status.model_dump()})
    return {"message": "All hazard states reset to NORMAL", "status": status}


@app.post("/api/v1/firms/hotspots")
async def add_firms_hotspot(hotspot: AddHotspotRequest):
    """Add a simulated NASA FIRMS hotspot for wildfire corroboration testing."""
    hs = FirmsHotspot(
        latitude=hotspot.latitude,
        longitude=hotspot.longitude,
        brightness=hotspot.brightness,
        confidence=hotspot.confidence,
    )
    firms_client.add_simulated_hotspot(hs)
    return {"message": "Simulated NASA FIRMS hotspot registered", "hotspot": hs.model_dump()}


@app.post("/api/v1/simulate")
async def trigger_simulation_scenario(req: SimulateRequest):
    """
    Execute end-to-end simulation scenarios for evaluation and demonstration:
    - wildfire_critical: High fire danger + NASA FIRMS confirmation (+15%)
    - flood_critical: Extreme stage surge and rainfall
    - landslide_critical: High slope tilt angle and soil saturation
    - simultaneous_all_critical: All 3 hazards triggering simultaneously!
    - reset_normal: Returns all 3 hardware systems to safe baseline
    """
    scenario = req.scenario.lower().strip()
    results = []

    ls_node = LandslideHardwareNode()
    fl_node = FloodHardwareNode()
    wf_node = WildfireHardwareNode()

    if scenario == "wildfire_critical":
        pkt = central_receiver.ingest_raw_packet(wf_node.generate_packet(condition="critical"))
        ev = await process_incoming_packet(pkt)
        results.append(ev)

    elif scenario == "flood_critical":
        pkt = central_receiver.ingest_raw_packet(fl_node.generate_packet(condition="critical"))
        ev = await process_incoming_packet(pkt)
        results.append(ev)

    elif scenario == "landslide_critical":
        pkt = central_receiver.ingest_raw_packet(ls_node.generate_packet(condition="critical"))
        ev = await process_incoming_packet(pkt)
        results.append(ev)

    elif scenario in ("simultaneous_all_critical", "multi_disaster_critical"):
        # Emits critical packets from all three separate hardware systems!
        # Demonstrates Core Requirement: simultaneous multi-hazard handling
        pkt_wf = central_receiver.ingest_raw_packet(wf_node.generate_packet(condition="critical"))
        ev_wf = await process_incoming_packet(pkt_wf)
        results.append(ev_wf)

        pkt_fl = central_receiver.ingest_raw_packet(fl_node.generate_packet(condition="critical"))
        ev_fl = await process_incoming_packet(pkt_fl)
        results.append(ev_fl)

        pkt_ls = central_receiver.ingest_raw_packet(ls_node.generate_packet(condition="critical"))
        ev_ls = await process_incoming_packet(pkt_ls)
        results.append(ev_ls)

    elif scenario == "reset_normal":
        pkt_wf = central_receiver.ingest_raw_packet(wf_node.generate_packet(condition="normal"))
        await process_incoming_packet(pkt_wf)
        pkt_fl = central_receiver.ingest_raw_packet(fl_node.generate_packet(condition="normal"))
        await process_incoming_packet(pkt_fl)
        pkt_ls = central_receiver.ingest_raw_packet(ls_node.generate_packet(condition="normal"))
        await process_incoming_packet(pkt_ls)
        await state_manager.reset_all_states()
        return {"scenario": scenario, "message": "All nodes returned to normal baseline."}

    else:
        raise HTTPException(
            status_code=400,
            detail="Unknown scenario. Choose from: wildfire_critical, flood_critical, landslide_critical, simultaneous_all_critical, reset_normal"
        )

    status = await state_manager.get_multi_disaster_status()
    return {
        "scenario": scenario,
        "processed_events": [e.model_dump() for e in results],
        "multi_disaster_status": status.model_dump(),
    }


# ==============================================================================
# WebSocket Endpoint for Real-time Dashboard Streaming
# ==============================================================================

@app.websocket("/ws")
async def websocket_telemetry_stream(websocket: WebSocket):
    """
    Real-time bidirectional WebSocket connection for the digital map dashboard.
    Pushes status updates, live hardware telemetry, and alerts instantly.
    """
    await ws_manager.connect(websocket)
    try:
        # Send initial state snapshot on connect
        status = await state_manager.get_multi_disaster_status()
        events = await state_manager.get_recent_events(limit=20)
        alerts = telegram_dispatcher.get_recent_alerts(limit=20)

        await websocket.send_json({
            "type": "INITIAL_STATE",
            "data": {
                "status": status.model_dump(),
                "events": [e.model_dump() for e in events],
                "alerts": [a.model_dump() for a in alerts],
                "receiver_gps": central_receiver.get_receiver_gps(),
                "firms_hotspots": [h.model_dump() for h in firms_client._simulated_hotspots],
            },
        })

        # Keep listening for client commands (ping, scenario triggers)
        while True:
            text = await websocket.receive_text()
            # Client can send heartbeat or commands
            if text == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.debug("WebSocket error: %s", e)
        ws_manager.disconnect(websocket)


# ==============================================================================
# Web UI Static Assets & Dashboard Route
# ==============================================================================

static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
async def serve_dashboard():
    """Serve the interactive digital map dashboard."""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_file):
        return FileResponse(index_file)
    return {"message": f"{settings.app_name} is running. Web UI not yet compiled."}
