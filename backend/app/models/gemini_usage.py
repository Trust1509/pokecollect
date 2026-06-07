from sqlalchemy import Column, Integer, Text

from app.database import Base


class GeminiUsage(Base):
    """Tagesnutzung der Gemini-API (Requests + Tokens) zur Kostenkontrolle."""
    __tablename__ = "gemini_usage"

    day = Column(Text, primary_key=True)        # "YYYY-MM-DD" (UTC)
    requests = Column(Integer, nullable=False, default=0)
    tokens = Column(Integer, nullable=False, default=0)
