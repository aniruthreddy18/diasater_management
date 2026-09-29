"""
Telegram Alert Dispatcher
Multi-Disaster Early Warning System
"""

import time
import uuid
import logging
from typing import Dict, List, Optional, Any
import httpx

from config.settings import settings
from core.models import HazardEvent, AlertRecord, RiskLevel
from risk.risk_engine import risk_engine
from .formatter import format_telegram_alert

logger = logging.getLogger(__name__)


class TelegramAlertDispatcher:
    """
    Dispatches early warning notifications to Telegram.
    Includes rate-limiting cooldown and mock fallback for zero-dependency local testing.
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        cooldown_seconds: Optional[float] = None,
        min_risk_level: Optional[str] = None,
    ):
        raw_token = bot_token if bot_token is not None else settings.telegram.bot_token
        raw_chat = chat_id if chat_id is not None else settings.telegram.chat_id
        self.bot_token = "".join(raw_token.split()) if raw_token else ""
        self.chat_id = "".join(raw_chat.split()) if raw_chat else ""
        self.cooldown_seconds = (
            cooldown_seconds if cooldown_seconds is not None else settings.telegram.cooldown_seconds
        )
        self.min_risk_level = (
            min_risk_level if min_risk_level is not None else settings.telegram.min_alert_risk_level
        )

        # Track last alert dispatch timestamp per device / hazard key
        self._last_alert_times: Dict[str, float] = {}
        # In-memory history of alerts for web dashboard & inspection
        self._alerts_history: List[AlertRecord] = []

    def is_configured(self) -> bool:
        """Check if real Telegram credentials are provided."""
        return bool(self.bot_token and self.chat_id)

    async def send_event_alert(self, event: HazardEvent, force: bool = False) -> Optional[AlertRecord]:
        """
        Evaluate and dispatch an alert if the hazard event meets risk criteria.
        """
        # 1. Check if event warrants an alert
        should_alert = risk_engine.should_trigger_alert(
            event.risk_level,
            event.final_risk_score,
            min_level=self.min_risk_level,
        )

        if not should_alert and not force:
            logger.debug(
                "Event [%s] (%s) below alert threshold '%s'. Alert suppressed.",
                event.event_id, event.risk_level.value, self.min_risk_level
            )
            return None

        # 2. Check cooldown per hazard type
        now = time.time()
        throttle_key = f"{event.hazard_type.value}_{event.device_id}"
        last_alert_time = self._last_alert_times.get(throttle_key, 0.0)

        # Allow bypass if force is True or if risk escalated to EXTREME
        if not force and (now - last_alert_time < self.cooldown_seconds) and event.risk_level != RiskLevel.EXTREME:
            remaining = int(self.cooldown_seconds - (now - last_alert_time))
            logger.info("Alert for %s throttled by cooldown (%ds remaining)", throttle_key, remaining)
            return None

        # 3. Format message
        message_text = format_telegram_alert(event)
        alert_id = f"ALT_{uuid.uuid4().hex[:8]}"

        delivered = False
        error_msg = None

        # 4. Dispatch via Telegram Bot API or Fallback
        self._last_alert_times[throttle_key] = now

        if self.is_configured():
            url = f"{settings.telegram.api_url}{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message_text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        delivered = True
                        logger.info("Telegram alert dispatched successfully for %s", event.hazard_type.value)
                    else:
                        error_msg = f"Telegram HTTP {resp.status_code}: {resp.text}"
                        logger.error("Failed sending Telegram alert: %s", error_msg)
            except Exception as e:
                error_msg = str(e)
                logger.error("Telegram connection error: %s", e)
        else:
            # Fallback simulated alert dispatch
            delivered = True  # Recorded locally
            logger.info(
                "\n================ TELEGRAM ALERT (SIMULATION/LOCAL) ================\n"
                "%s\n"
                "===================================================================",
                message_text
            )

        alert_record = AlertRecord(
            alert_id=alert_id,
            hazard_type=event.hazard_type,
            device_id=event.device_id,
            risk_level=event.risk_level,
            risk_score=event.final_risk_score,
            latitude=event.latitude,
            longitude=event.longitude,
            timestamp=event.timestamp,
            message=message_text,
            channel="TELEGRAM",
            delivered=delivered,
            error=error_msg,
        )

        self._alerts_history.insert(0, alert_record)
        if len(self._alerts_history) > 100:
            self._alerts_history.pop()

        return alert_record

    def get_recent_alerts(self, limit: int = 50) -> List[AlertRecord]:
        """Return list of recent alerts."""
        return list(self._alerts_history[:limit])

    def update_credentials(self, bot_token: str, chat_id: str):
        """Update Telegram credentials dynamically at runtime."""
        self.bot_token = "".join(bot_token.split())
        self.chat_id = "".join(chat_id.split())

    async def test_connection(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None) -> Dict[str, Any]:
        """Send a test handshake message to verify Telegram Bot configuration."""
        token = "".join((bot_token or self.bot_token or "").split())
        target_chat = "".join((chat_id or self.chat_id or "").split())

        if not token:
            return {"success": False, "error": "Bot token is missing. Please enter your Telegram Bot Token."}
        if not target_chat:
            return {"success": False, "error": "Chat ID is missing. Please enter your Telegram Chat ID."}

        url = f"{settings.telegram.api_url}{token}/sendMessage"
        test_msg = (
            "🚨 *MULTI-DISASTER EARLY WARNING SYSTEM* 🚨\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ *Telegram Bot Integration:* `CONNECTED`\n"
            "📡 *Central Receiver:* `ONLINE (Port 8000)`\n"
            "🗺️ *Status:* Early Warning Locality Alerts are active!\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "_Automated Handshake Test Dispatch_"
        )
        payload = {
            "chat_id": target_chat,
            "text": test_msg,
            "parse_mode": "Markdown",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    return {
                        "success": True,
                        "message": "Telegram handshake successful! Test alert delivered.",
                        "bot_configured": True,
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Telegram API returned {resp.status_code}: {resp.text}",
                        "bot_configured": False,
                    }
        except Exception as e:
            return {
                "success": False,
                "error": f"Connection failed: {str(e)}",
                "bot_configured": False,
            }


# Global alert dispatcher instance
telegram_dispatcher = TelegramAlertDispatcher()
