import os
import uvicorn
from analytics_agent.app.config import settings

if __name__ == "__main__":
    print(f"Starting AgentOS Analytics Agent on http://localhost:{settings.PORT} ...")
    uvicorn.run("analytics_agent.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
