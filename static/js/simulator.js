/**
 * Interactive Hardware Simulation Bench
 * Multi-Disaster Early Warning System
 */

class SimulationBench {
  async triggerScenario(scenario) {
    const btn = window.event?.currentTarget;
    const originalText = btn ? btn.innerHTML : "";
    if (btn) {
      btn.style.opacity = "0.7";
      btn.style.transform = "scale(0.98)";
    }

    try {
      const response = await fetch("/api/v1/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario }),
      });

      if (!response.ok) {
        const err = await response.json();
        alert(`Simulation Error: ${err.detail || "Request failed"}`);
      } else {
        // Immediate sync to refresh dashboard UI without delay
        if (window.dashboardCtrl) {
          await window.dashboardCtrl.fetchInitialStateREST();
        }
      }
    } catch (e) {
      console.error("Simulation trigger failed:", e);
    } finally {
      if (btn) {
        btn.style.opacity = "1";
        btn.style.transform = "none";
      }
    }
  }

  async resetAll() {
    try {
      await fetch("/api/v1/reset", { method: "POST" });
      if (window.dashboardCtrl) {
        await window.dashboardCtrl.fetchInitialStateREST();
      }
    } catch (e) {
      console.error("Reset failed:", e);
    }
  }
}

window.simBench = new SimulationBench();
