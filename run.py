"""
Multi-Disaster Early Warning System — Launcher
"""

import uvicorn
from config.settings import settings

if __name__ == "__main__":
    print(f"\n==================================================================")
    print(f"  Starting {settings.app_name} v{settings.version}")
    print(f"  Central Receiver GPS: ({settings.receiver.default_latitude}, {settings.receiver.default_longitude})")
    print(f"  Digital Map & Dashboard: http://localhost:{settings.server_port}")
    print(f"  API Docs (Swagger):      http://localhost:{settings.server_port}/docs")
    print(f"==================================================================\n")

    uvicorn.run(
        "api.app:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
        log_level="info",
    )
