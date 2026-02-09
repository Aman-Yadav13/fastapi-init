from sqlalchemy import Column, Integer, String
from .database import Base

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_name = Column(String, unique=True, index=True, nullable=False)
    cluster_name = Column(String, nullable=True)
    customer_env = Column(String, nullable=True) 
    cloud_platform = Column(String, default="aws")
    region = Column(String, nullable=True)
    project_id = Column(Integer, nullable=True)   
    web_url = Column(String, nullable=True)       