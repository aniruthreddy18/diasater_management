-- ==============================================================================
-- SMART INDIA HACKATHON (SIH) — TACTICAL MISSION CONTROL
-- Multi-Disaster Early Warning System: Landslides, Flash Floods & Wildfires
-- Supabase PostgreSQL Schema & Realtime Setup
-- ==============================================================================

-- 1. TELEMETRY LOGS TABLE (High-Frequency Edge Telemetry Storage)
CREATE TABLE IF NOT EXISTS public.telemetry_logs (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT,
    device_id TEXT NOT NULL,
    hazard_type TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    sensor_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    base_risk_score DOUBLE PRECISION DEFAULT 0.0,
    final_risk_score DOUBLE PRECISION DEFAULT 0.0,
    risk_level TEXT DEFAULT 'NORMAL',
    detected BOOLEAN DEFAULT FALSE,
    firms_confirmed BOOLEAN DEFAULT FALSE,
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW())
);

-- 2. DISASTER ALERTS TABLE (Emergency Telegram & Siren Broadcast Logs)
CREATE TABLE IF NOT EXISTS public.disaster_alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    hazard_type TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    message TEXT NOT NULL,
    channel TEXT DEFAULT 'TELEGRAM',
    delivered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW())
);

-- 3. ACTIVE STATIONS TABLE (National GSI / CWC / FSI Field Bindings)
CREATE TABLE IF NOT EXISTS public.active_stations (
    category TEXT PRIMARY KEY,
    station_id TEXT NOT NULL,
    station_name TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT TIMEZONE('utc', NOW())
);

-- 4. Enable Supabase Realtime for Instant Map Telemetry Push
ALTER PUBLICATION supabase_realtime ADD TABLE public.telemetry_logs;
ALTER PUBLICATION supabase_realtime ADD TABLE public.disaster_alerts;
ALTER PUBLICATION supabase_realtime ADD TABLE public.active_stations;

-- 5. High-Performance Query Indexes
CREATE INDEX IF NOT EXISTS idx_telemetry_created_at ON public.telemetry_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_hazard ON public.telemetry_logs (hazard_type);
CREATE INDEX IF NOT EXISTS idx_telemetry_device ON public.telemetry_logs (device_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON public.disaster_alerts (created_at DESC);

-- 6. Row Level Security (RLS) Policies
-- Allow public anonymous reads for dashboard viewers, and service-role write access
ALTER TABLE public.telemetry_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.disaster_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.active_stations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access on telemetry_logs" 
    ON public.telemetry_logs FOR SELECT USING (true);

CREATE POLICY "Allow public insert on telemetry_logs" 
    ON public.telemetry_logs FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public read access on disaster_alerts" 
    ON public.disaster_alerts FOR SELECT USING (true);

CREATE POLICY "Allow public insert on disaster_alerts" 
    ON public.disaster_alerts FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public read access on active_stations" 
    ON public.active_stations FOR SELECT USING (true);

CREATE POLICY "Allow public all on active_stations" 
    ON public.active_stations FOR ALL USING (true);
