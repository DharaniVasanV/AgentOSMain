import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:root@localhost:5432/analytics_db")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    PORT: int = int(os.getenv("PORT", 8000))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # Configurable Productivity Formula Weights (Totaling 100 max score)
    WEIGHT_TASK_COMPLETION: float = float(os.getenv("WEIGHT_TASK_COMPLETION", 35.0))
    WEIGHT_OVERDUE_PENALTY: float = float(os.getenv("WEIGHT_OVERDUE_PENALTY", 15.0))
    WEIGHT_MEETING_PARTICIPATION: float = float(os.getenv("WEIGHT_MEETING_PARTICIPATION", 15.0))
    WEIGHT_LEARNING_ACTIVITY: float = float(os.getenv("WEIGHT_LEARNING_ACTIVITY", 15.0))
    WEIGHT_CAREER_ACTIVITY: float = float(os.getenv("WEIGHT_CAREER_ACTIVITY", 10.0))
    WEIGHT_OPPORTUNITIES: float = float(os.getenv("WEIGHT_OPPORTUNITIES", 10.0))

settings = Settings()
