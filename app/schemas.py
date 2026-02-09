from pydantic import BaseModel
from typing import Optional

# Base schema with shared attributes
class AssetBase(BaseModel):
    asset_name: str
    cluster_name: Optional[str] = None
    customer_env: Optional[str] = None
    cloud_platform: Optional[str] = "aws"
    region: Optional[str] = None
    project_id: Optional[int] = None
    web_url: Optional[str] = None

# Schema for creating an asset 
class AssetCreate(AssetBase):
    pass

# Schema for reading an asset 
class Asset(AssetBase):
    id: int

    class Config:
        from_attributes = True  # Allows Pydantic to read SQLAlchemy models