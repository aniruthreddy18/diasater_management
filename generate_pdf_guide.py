"""
PDF Guide Generator for Multi-Disaster Early Warning System
Uses ReportLab to generate a high-quality, professional engineering manual.
"""

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)


def create_pdf(output_filename: str):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=14,
        spaceAfter=6,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#334155"),
        spaceBefore=10,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=2,
        spaceAfter=2,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.white,
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # =========================================================================
    # HEADER / TITLE
    # =========================================================================
    story.append(Paragraph("MULTI-DISASTER EARLY WARNING SYSTEM", title_style))
    story.append(
        Paragraph(
            "Hardware-to-Dashboard Connection & Deployment Manual • Comprehensive Integration Guide",
            subtitle_style,
        )
    )
    story.append(
        HRFlowable(
            width="100%", thickness=2, color=colors.HexColor("#2563eb"), spaceAfter=14
        )
    )

    # Info summary box
    meta_data = [
        [
            Paragraph("<b>Target System:</b> ESP32 + GPS (NEO-6M) + Sensors", table_cell_style),
            Paragraph("<b>Active Server IP:</b> <code>10.166.170.10:8000</code>", table_cell_style),
        ],
        [
            Paragraph("<b>Transport Protocol:</b> HTTP REST over 2.4GHz Wi-Fi", table_cell_style),
            Paragraph("<b>Endpoint:</b> <code>/api/v1/telemetry</code>", table_cell_style),
        ],
        [
            Paragraph("<b>Supported Hazards:</b> Wildfire, Flash Flood, Landslide", table_cell_style),
            Paragraph("<b>Dashboard URL:</b> <code>http://localhost:8000</code>", table_cell_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[270, 260])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 1: ARCHITECTURE OVERVIEW
    # =========================================================================
    story.append(Paragraph("1. System Architecture & End-to-End Data Path", h1_style))
    story.append(
        Paragraph(
            "The system operates across three independent physical transmitter systems communicating "
            "with a central software receiver over a shared Wi-Fi network. Each node transmits its unique "
            "hardware identifier, disaster category, real-world satellite GPS coordinates, and raw sensor readings.",
            body_style,
        )
    )

    arch_box = [
        [
            Paragraph(
                "<b>[PHYSICAL TRANSMITTER NODE]</b><br/>"
                "• ESP32 Microcontroller<br/>"
                "• Ceramic Patch GPS Antenna<br/>"
                "• Dedicated Environmental Sensors<br/>"
                "• Connects to 2.4GHz Wi-Fi",
                table_cell_style,
            ),
            Paragraph(
                "<b>══════►<br/>HTTP POST<br/>JSON Packet<br/>(Port 8000)<br/>══════►</b>",
                ParagraphStyle("CenterText", parent=styles["Normal"], alignment=1, fontSize=8),
            ),
            Paragraph(
                "<b>[CENTRAL RECEIVER & DASHBOARD]</b><br/>"
                "• Python FastAPI Asynchronous Receiver<br/>"
                "• Independent Classification Engines<br/>"
                "• NASA FIRMS Satellite Cross-Check (+15%)<br/>"
                "• Real-Time Leaflet OpenStreetMap Visualizer",
                table_cell_style,
            ),
        ]
    ]
    t_arch = Table(arch_box, colWidths=[200, 100, 230])
    t_arch.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#eff6ff")),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#f0fdf4")),
                ("BOX", (0, 0), (0, 0), 1, colors.HexColor("#93c5fd")),
                ("BOX", (2, 0), (2, 0), 1, colors.HexColor("#86efac")),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(t_arch)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 2: STEP-BY-STEP INTEGRATION
    # =========================================================================
    story.append(Paragraph("2. Step-by-Step Connection Procedure", h1_style))

    story.append(Paragraph("Step 1: Verify Host Computer Network Address", h2_style))
    story.append(
        Paragraph(
            "Your Mac hosts the central server. The ESP32 requires the Mac's private local IP. "
            "In Terminal, run: <code>ipconfig getifaddr en0</code>. "
            "Your currently assigned IP is <b><code>10.166.170.10</code></b>. "
            "If your Wi-Fi changes, always re-check this address.",
            body_style,
        )
    )

    story.append(Paragraph("Step 2: Ensure Dashboard Server Is Active", h2_style))
    story.append(
        Paragraph(
            "Launch the receiver from the project root:<br/>"
            "<code>cd /Users/aniruthreddy/Downloads/jarvis && ./venv/bin/python3 run.py</code><br/>"
            "Confirm the server prints: <i>Uvicorn running on http://0.0.0.0:8000</i>. "
            "Navigate to <b><code>http://localhost:8000</code></b> in your web browser.",
            body_style,
        )
    )

    story.append(Paragraph("Step 3: Non-Invasive ESP32 Firmware Integration", h2_style))
    story.append(
        Paragraph(
            "Do <b>not</b> overwrite your existing sensor algorithms or trained machine learning models. "
            "Simply insert the following components into your current Arduino sketch:",
            body_style,
        )
    )

    code_sample = [
        [
            Paragraph(
                "// --- 1. HEADERS & CONFIGURATION (Insert at top of .ino file) ---<br/>"
                "#include &lt;WiFi.h&gt;<br/>"
                "#include &lt;HTTPClient.h&gt;<br/>"
                "const char* WIFI_SSID     = \"YOUR_WIFI_NAME\";<br/>"
                "const char* WIFI_PASSWORD = \"YOUR_WIFI_PASSWORD\";<br/>"
                "const char* SERVER_URL    = \"http://10.166.170.10:8000/api/v1/telemetry\";<br/><br/>"
                "// --- 2. SETUP CODE (Add to void setup) ---<br/>"
                "WiFi.begin(WIFI_SSID, WIFI_PASSWORD);<br/>"
                "while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print(\".\"); }<br/>"
                "Serial.println(\"\\n[Wi-Fi] Connected to Dashboard!\");<br/><br/>"
                "// --- 3. TRANSMISSION FUNCTION (Paste at bottom of file) ---<br/>"
                "void sendDisasterAlert(float lat, float lon, float temp, float smoke) {<br/>"
                "&nbsp;&nbsp;if (WiFi.status() == WL_CONNECTED) {<br/>"
                "&nbsp;&nbsp;&nbsp;&nbsp;HTTPClient http;<br/>"
                "&nbsp;&nbsp;&nbsp;&nbsp;http.begin(SERVER_URL);<br/>"
                "&nbsp;&nbsp;&nbsp;&nbsp;http.addHeader(\"Content-Type\", \"application/json\");<br/>"
                "&nbsp;&nbsp;&nbsp;&nbsp;String payload = \"{\\\"device_id\\\":\\\"FIRE_001\\\",\\\"hazard_type\\\":\\\"WILDFIRE\\\",\"<br/>"
                "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\"\\\"latitude\\\":\" + String(lat, 6) + \",\\\"longitude\\\":\" + String(lon, 6) + \",\"<br/>"
                "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;\"\\\"sensor_data\\\":{\\\"temperature\\\":\" + String(temp, 1) + \",\\\"smoke\\\":\" + String(smoke, 1) + \",\\\"flame_detected\\\":true}}\";<br/>"
                "&nbsp;&nbsp;&nbsp;&nbsp;int code = http.POST(payload);<br/>"
                "&nbsp;&nbsp;&nbsp;&nbsp;Serial.println(\"[TX] Response: \" + String(code));<br/>"
                "&nbsp;&nbsp;&nbsp;&nbsp;http.end();<br/>"
                "&nbsp;&nbsp;}<br/>"
                "}",
                code_style,
            )
        ]
    ]
    t_code = Table(code_sample, colWidths=[530])
    t_code.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(t_code)

    story.append(PageBreak())

    # =========================================================================
    # SECTION 3: PHYSICAL WIRING REFERENCE
    # =========================================================================
    story.append(Paragraph("3. Physical Hardware Pinout & Wiring Table", h1_style))
    story.append(
        Paragraph(
            "Correct pin pairing between the ESP32 and peripheral sensors is critical. "
            "Note that the GPS Transmit (TX) line must cross over to the ESP32 Receive (RX) pin.",
            body_style,
        )
    )

    pin_table_data = [
        [
            Paragraph("Module / Component", table_header_style),
            Paragraph("Module Pin", table_header_style),
            Paragraph("ESP32 Target Pin", table_header_style),
            Paragraph("Functional Description & Notes", table_header_style),
        ],
        [
            Paragraph("<b>NEO-6M GPS Module</b>", table_cell_bold),
            Paragraph("VCC", table_cell_style),
            Paragraph("3.3V or 5V", table_cell_style),
            Paragraph("Power input (recommended 3.3V to minimize thermal drift)", table_cell_style),
        ],
        [
            Paragraph("<b>NEO-6M GPS Module</b>", table_cell_bold),
            Paragraph("GND", table_cell_style),
            Paragraph("GND", table_cell_style),
            Paragraph("Common system ground", table_cell_style),
        ],
        [
            Paragraph("<b>NEO-6M GPS Module</b>", table_cell_bold),
            Paragraph("TX", table_cell_style),
            Paragraph("<b>GPIO 16 (RX2)</b>", table_cell_bold),
            Paragraph("<b>Data Out from GPS → Into ESP32 Hardware Serial2</b>", table_cell_style),
        ],
        [
            Paragraph("<b>NEO-6M GPS Module</b>", table_cell_bold),
            Paragraph("RX", table_cell_style),
            Paragraph("GPIO 17 (TX2)", table_cell_style),
            Paragraph("Command input into GPS (optional for standard NMEA read)", table_cell_style),
        ],
        [
            Paragraph("<b>MQ-2 / MQ-135 Gas</b>", table_cell_bold),
            Paragraph("A0 (Analog)", table_cell_style),
            Paragraph("GPIO 34 (ADC1)", table_cell_style),
            Paragraph("Smoke density measurement (ADC1 active during Wi-Fi)", table_cell_style),
        ],
        [
            Paragraph("<b>Flame Sensor</b>", table_cell_bold),
            Paragraph("D0 (Digital)", table_cell_style),
            Paragraph("GPIO 25", table_cell_style),
            Paragraph("Binary optical flame detection trigger", table_cell_style),
        ],
        [
            Paragraph("<b>HC-SR04 Ultrasonic</b>", table_cell_bold),
            Paragraph("TRIG / ECHO", table_cell_style),
            Paragraph("GPIO 5 / GPIO 18", table_cell_style),
            Paragraph("Flood stage distance measurement", table_cell_style),
        ],
        [
            Paragraph("<b>Soil Moisture Sensor</b>", table_cell_bold),
            Paragraph("AOUT", table_cell_style),
            Paragraph("GPIO 35 (ADC1)", table_cell_style),
            Paragraph("Landslide soil water saturation percentage", table_cell_style),
        ],
    ]
    t_pin = Table(pin_table_data, colWidths=[110, 75, 100, 245])
    t_pin.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_pin)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 4: CONCENTRIC RISK RADIUS CLASSIFICATION & LOCALITY ALERTING
    # =========================================================================
    story.append(Paragraph("4. Concentric Locality Risk Radius Classification", h1_style))
    story.append(
        Paragraph(
            "When sensor readings transition from <b>CLEAR</b> to <b>DANGER</b>, the dashboard "
            "automatically centers on the satellite GPS coordinates and renders 3 concentric risk zones based on "
            "the computed composite risk percentage:",
            body_style,
        )
    )

    risk_zone_data = [
        [
            Paragraph("Classification Zone", table_header_style),
            Paragraph("Map Visual", table_header_style),
            Paragraph("Evacuation & Public Action", table_header_style),
            Paragraph("Formula & Example (R=85%)", table_header_style),
        ],
        [
            Paragraph("<b>🔴 Zone 1: VERY DANGER</b>", table_cell_bold),
            Paragraph("Crimson Pulse<br/>Fill: 38%", table_cell_style),
            Paragraph("<b>Immediate Mandatory Evacuation</b>. Severe threat to life, active fire/flood front.", table_cell_style),
            Paragraph("<code>r = (R/100) × 1.5 km</code><br/><b>&lt; 1.28 km</b>", table_cell_style),
        ],
        [
            Paragraph("<b>🟠 Zone 2: DANGER</b>", table_cell_bold),
            Paragraph("Orange Dashed<br/>Fill: 22%", table_cell_style),
            Paragraph("<b>High Warning Zone</b>. Prepare evacuation, clear critical routes, shelter vulnerable.", table_cell_style),
            Paragraph("<code>r = (R/100) × 3.5 km</code><br/><b>&lt; 2.98 km</b>", table_cell_style),
        ],
        [
            Paragraph("<b>🟡 Zone 3: MODERATE DANGER</b>", table_cell_bold),
            Paragraph("Amber Dotted<br/>Fill: 12%", table_cell_style),
            Paragraph("<b>Advisory & Watch Zone</b>. Monitor emergency broadcasts, prepare go-bags.", table_cell_style),
            Paragraph("<code>r = (R/100) × 6.0 km</code><br/><b>&lt; 5.10 km</b>", table_cell_style),
        ],
    ]
    t_risk_zone = Table(risk_zone_data, colWidths=[120, 90, 180, 140])
    t_risk_zone.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7f1d1d")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff1f2")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t_risk_zone)
    story.append(Spacer(1, 14))
    story.append(PageBreak())

    # =========================================================================
    # SECTION 5: DIAGNOSTIC & TROUBLESHOOTING MATRIX
    # =========================================================================
    story.append(Paragraph("5. Diagnostic & Troubleshooting Matrix", h1_style))
    story.append(
        Paragraph(
            "Every anticipated hardware, network, and software error condition is categorized below "
            "along with its immediate physical resolution.",
            body_style,
        )
    )

    trouble_data = [
        [
            Paragraph("Symptom / Error Code", table_header_style),
            Paragraph("Root Cause", table_header_style),
            Paragraph("Required Physical / Software Action", table_header_style),
        ],
        [
            Paragraph("<b>Wi-Fi dots loop indefinitely<br/>(Connecting........)</b>", table_cell_bold),
            Paragraph("ESP32 attempting connection to a 5GHz network band.", table_cell_style),
            Paragraph(
                "ESP32 hardware contains a 2.4GHz radio only. Switch your router or phone hotspot "
                "to <b>2.4GHz</b> (enable 'Maximize Compatibility' on iPhone). Verify SSID spelling.",
                table_cell_style,
            ),
        ],
        [
            Paragraph("<b>HTTP POST Error: -1<br/>(Connection Refused)</b>", table_cell_bold),
            Paragraph("Subnet mismatch or server unreachable.", table_cell_style),
            Paragraph(
                "Verify that both your Mac and ESP32 share the same Wi-Fi. Check that your Mac's IP "
                "matches <code>10.166.170.10</code>. Check that Python server is running on port 8000.",
                table_cell_style,
            ),
        ],
        [
            Paragraph("<b>GPS Coordinates Show<br/>0.000000, 0.000000</b>", table_cell_bold),
            Paragraph("No satellite lock acquired yet.", table_cell_style),
            Paragraph(
                "Place the ceramic square patch antenna with the <b>flat tan side facing straight UP</b> "
                "outdoors or directly on a windowsill. Wait 60–90 seconds until the module LED blinks.",
                table_cell_style,
            ),
        ],
        [
            Paragraph("<b>Brownout Detector Was Triggered</b>", table_cell_bold),
            Paragraph("Power surge voltage drop when Wi-Fi modem engages.", table_cell_style),
            Paragraph(
                "Wi-Fi transmission requires ~250mA instant current. Power the ESP32 from a USB 3.0 port "
                "or dedicated 5V 1A power supply. Do not power through high-resistance unpowered hubs.",
                table_cell_style,
            ),
        ],
        [
            Paragraph("<b>WiFi.h: No such file or directory</b>", table_cell_bold),
            Paragraph("Incorrect microcontroller target board in IDE.", table_cell_style),
            Paragraph(
                "Navigate to <i>Tools → Board</i> in Arduino IDE and select <b>ESP32 Dev Module</b>.",
                table_cell_style,
            ),
        ],
        [
            Paragraph("<b>HTTP Status Code: 400<br/>(Bad Request)</b>", table_cell_bold),
            Paragraph("Malformed JSON telemetry string.", table_cell_style),
            Paragraph(
                "Ensure JSON field keys match standard schema: <code>device_id</code>, "
                "<code>hazard_type</code>, <code>latitude</code>, <code>longitude</code>, <code>sensor_data</code>.",
                table_cell_style,
            ),
        ],
        [
            Paragraph("<b>Node Collisions On Shared Wi-Fi</b>", table_cell_bold),
            Paragraph("Concern over simultaneous transmissions.", table_cell_style),
            Paragraph(
                "No collision can occur. Wi-Fi uses hardware CSMA/CA packet scheduling and the Python "
                "FastAPI backend is asynchronous (<code>asyncio</code>). All 3 nodes can transmit simultaneously.",
                table_cell_style,
            ),
        ],
    ]
    t_trouble = Table(trouble_data, colWidths=[125, 140, 265])
    t_trouble.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b91c1c")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff1f2")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_trouble)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 6: TELEGRAM BOT INTEGRATION & LOCALITY ALERT SETUP
    # =========================================================================
    story.append(Paragraph("6. Telegram Early Warning Bot Setup Guide", h1_style))
    story.append(
        Paragraph(
            "Emergency dispatches and locality evacuation orders are transmitted in real-time "
            "to Telegram responders and municipal groups. Follow these steps to connect your bot:",
            body_style,
        )
    )

    tg_steps_data = [
        [
            Paragraph("Step", table_header_style),
            Paragraph("Action", table_header_style),
            Paragraph("Exact Command / Procedure", table_header_style),
        ],
        [
            Paragraph("<b>1. Create Bot</b>", table_cell_bold),
            Paragraph("Open Telegram and search for <b>@BotFather</b>", table_cell_style),
            Paragraph("Send <code>/newbot</code>, specify your display name and unique bot username ending in 'bot'.", table_cell_style),
        ],
        [
            Paragraph("<b>2. Copy Token</b>", table_cell_bold),
            Paragraph("Obtain the HTTP API Bot Token", table_cell_style),
            Paragraph("Copy the string (e.g., <code>7123456789:AAHxyzABC123...</code>) into Dashboard <i>Bot Token</i> field.", table_cell_style),
        ],
        [
            Paragraph("<b>3. Get Chat ID</b>", table_cell_bold),
            Paragraph("Determine destination user or channel ID", table_cell_style),
            Paragraph(
                "• Personal: Start bot, search <b>@userinfobot</b>, send <code>/start</code> to copy ID.<br/>"
                "• Locality Channel: Add bot as Admin to your Telegram channel, send a post, and check ID with <b>@RawDataBot</b> (starts with <code>-100...</code>).",
                table_cell_style,
            ),
        ],
        [
            Paragraph("<b>4. Connect</b>", table_cell_bold),
            Paragraph("Activate live dispatch in Dashboard", table_cell_style),
            Paragraph("Click <b>'Save & Connect Telegram'</b> or test with <b>'Send Test Alert Handshake'</b>.", table_cell_style),
        ],
    ]
    t_tg = Table(tg_steps_data, colWidths=[80, 150, 300])
    t_tg.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0369a1")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f9ff")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(t_tg)
    story.append(Spacer(1, 14))

    # =========================================================================
    # SECTION 7: OPERATIONAL VERIFICATION CHECKLIST
    # =========================================================================
    story.append(Paragraph("7. Operational Verification Checklist", h1_style))
    checklist_text = (
        "<b>[  ] Host Server Verification:</b> Terminal shows <i>Uvicorn running on http://0.0.0.0:8000</i>.<br/>"
        "<b>[  ] Dashboard UI Check:</b> Open <code>http://localhost:8000</code> in browser; tactical map displays.<br/>"
        "<b>[  ] Hardware Antenna Check:</b> GPS patch antenna oriented flat-face upwards with clear view of sky.<br/>"
        "<b>[  ] Serial Monitor Check:</b> Arduino Serial Monitor at 115200 baud displays <i>[DASHBOARD] Sent! Server code: 200</i>.<br/>"
        "<b>[  ] Real-Time Plot Check:</b> Dynamic marker (🔥, 🌊, ⛰️) flies to coordinates on OpenStreetMap."
    )
    story.append(Paragraph(checklist_text, body_style))

    doc.build(story)
    print(f"PDF successfully generated at: {output_filename}")


if __name__ == "__main__":
    pdf_path = "/Users/aniruthreddy/Downloads/jarvis/ESP32_HARDWARE_DASHBOARD_CONNECTION_GUIDE.pdf"
    create_pdf(pdf_path)
