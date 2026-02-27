from sqlalchemy import Column, String, Boolean, BigInteger, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from .database import Base

class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    object_storage_key = Column(String, unique=True, nullable=False)
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    etag = Column(String, nullable=False)
    is_private = Column(Boolean, default=False)

    current_version_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

class AssetVersion(Base):
    __tablename__ = "asset_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"))
    object_storage_key = Column(String, unique=True, nullable=False)
    etag = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AccessToken(Base):
    __tablename__ = "access_tokens"

    token = Column(String, primary_key=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"))
    expires_at = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())