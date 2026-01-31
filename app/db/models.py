import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_auth_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    """Conversation model"""
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="conversation", cascade="all, delete-orphan")
    media = relationship("Media", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Message model - supports text and image messages"""
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(50), nullable=False)  # "user" | "assistant" | "system"
    content_json = Column(JSON, nullable=False)  # {"type": "text", "text": "..."} or {"type": "image", "url": "...", "caption": "..."}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    agent_runs = relationship("AgentRun", back_populates="trigger_message")


class AgentRun(Base):
    """Agent run tracking"""
    __tablename__ = "agent_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    trigger_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # "queued" | "running" | "succeeded" | "failed"
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="agent_runs")
    trigger_message = relationship("Message", back_populates="agent_runs")
    integration_deliveries = relationship("IntegrationDelivery", back_populates="agent_run", cascade="all, delete-orphan")


class Media(Base):
    """Media storage tracking (images, etc.)"""
    __tablename__ = "media"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    media_type = Column(String(100), nullable=False)  # "image/png", etc.
    storage_path = Column(Text, nullable=False)  # Local filesystem path
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="media")


class IntegrationDelivery(Base):
    """Track external system integration deliveries"""
    __tablename__ = "integration_deliveries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False)  # "pending" | "succeeded" | "failed"
    attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    agent_run = relationship("AgentRun", back_populates="integration_deliveries")
