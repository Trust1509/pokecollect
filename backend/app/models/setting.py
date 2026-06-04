from sqlalchemy import Column, String, Text

from app.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(Text, nullable=True)
