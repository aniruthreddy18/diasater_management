"""
Command-Line Multi-Disaster Simulation Runner
Multi-Disaster Early Warning System
"""

import sys
import time
import argparse
import asyncio
import httpx
from simulator.hardware_nodes import (
    LandslideHardwareNode,
    FloodHardwareNode,
    WildfireHardwareNode,
)


async def send_packet(base_url: str, packet: dict) -> dict:
    """Send packet to backend telemetry endpoint."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{base_url}/api/v1/telemetry", json=packet)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[ERROR] Failed ({resp.status_code}): {resp.text}")
            return {}


async def run_scenario(base_url: str, scenario: str):
    """Run a named scenario."""
    ls_node = LandslideHardwareNode()
    fl_node = FloodHardwareNode()
    wf_node = WildfireHardwareNode()

    print(f"\n=======================================================")
    print(f"  RUNNING SCENARIO: {scenario.upper()}")
    print(f"=======================================================\n")

    if scenario == "wildfire":
        pkt = wf_node.generate_packet(condition="critical")
        print(f"[EMIT] Wildfire Node ({pkt['device_id']}) emitting critical telemetry...")
        res = await send_packet(base_url, pkt)
        print(f"[RESULT] Detected: {res.get('detected')}, Final Risk: {res.get('final_risk_score')}%, Level: {res.get('risk_level')}")
        print(f"[FIRMS]  Confirmed: {res.get('firms_confirmed')}, Distance: {res.get('nearest_firms_distance_km')} km, Bonus: +{res.get('firms_adjustment')}%")

    elif scenario == "flood":
        pkt = fl_node.generate_packet(condition="critical")
        print(f"[EMIT] Flash Flood Node ({pkt['device_id']}) emitting critical telemetry...")
        res = await send_packet(base_url, pkt)
        print(f"[RESULT] Detected: {res.get('detected')}, Final Risk: {res.get('final_risk_score')}%, Level: {res.get('risk_level')}")

    elif scenario == "landslide":
        pkt = ls_node.generate_packet(condition="critical")
        print(f"[EMIT] Landslide Node ({pkt['device_id']}) emitting critical telemetry...")
        res = await send_packet(base_url, pkt)
        print(f"[RESULT] Detected: {res.get('detected')}, Final Risk: {res.get('final_risk_score')}%, Level: {res.get('risk_level')}")

    elif scenario in ("multi", "simultaneous"):
        print("[TEST] Emitting critical telemetry from ALL THREE independent hardware nodes simultaneously!\n")

        pkt_wf = wf_node.generate_packet(condition="critical")
        pkt_fl = fl_node.generate_packet(condition="critical")
        pkt_ls = ls_node.generate_packet(condition="critical")

        print("-> Emitting Wildfire Node...")
        res_wf = await send_packet(base_url, pkt_wf)
        print(f"   Wildfire: {res_wf.get('risk_level')} ({res_wf.get('final_risk_score')}%), FIRMS: {res_wf.get('firms_confirmed')}")

        print("-> Emitting Flood Node...")
        res_fl = await send_packet(base_url, pkt_fl)
        print(f"   Flood:    {res_fl.get('risk_level')} ({res_fl.get('final_risk_score')}%)")

        print("-> Emitting Landslide Node...")
        res_ls = await send_packet(base_url, pkt_ls)
        print(f"   Landslide:{res_ls.get('risk_level')} ({res_ls.get('final_risk_score')}%)")

        # Query simultaneous status
        async with httpx.AsyncClient(timeout=10.0) as client:
            status_resp = await client.get(f"{base_url}/api/v1/status")
            if status_resp.status_code == 200:
                s = status_resp.json()
                print("\n--- SIMULTANEOUS STATUS VERIFICATION ---")
                print(f"Active Disasters: {s.get('active_hazard_count')}/3")
                print(f"Wildfire State:   {s.get('wildfire', {}).get('status_label')} ({s.get('wildfire', {}).get('risk_level')})")
                print(f"Flood State:      {s.get('flash_flood', {}).get('status_label')} ({s.get('flash_flood', {}).get('risk_level')})")
                print(f"Landslide State:  {s.get('landslide', {}).get('status_label')} ({s.get('landslide', {}).get('risk_level')})")
                print("----------------------------------------")

    elif scenario == "reset":
        print("[RESET] Resetting all hazard states to NORMAL...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{base_url}/api/v1/reset")
            print(f"[RESULT] {resp.json().get('message')}")

    else:
        print(f"Unknown scenario '{scenario}'. Use: wildfire, flood, landslide, multi, or reset.")


def main():
    parser = argparse.ArgumentParser(description="Multi-Disaster Early Warning Hardware Simulator")
    parser.add_argument(
        "--scenario",
        "-s",
        type=str,
        default="multi",
        choices=["wildfire", "flood", "landslide", "multi", "simultaneous", "reset"],
        help="Disaster scenario to simulate",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    asyncio.run(run_scenario(args.host, args.scenario))


if __name__ == "__main__":
    main()
