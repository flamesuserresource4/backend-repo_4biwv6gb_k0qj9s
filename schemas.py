"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    hashed_password: str = Field(..., description="Password hash")
    is_active: bool = Field(True, description="Whether user is active")

class Service(BaseModel):
    """
    Services offered
    Collection name: "service"
    """
    title: str
    description: Optional[str] = None
    price_cents: int = Field(..., ge=0, description="Price in cents")
    duration_minutes: int = Field(..., ge=15, le=240)

class Appointment(BaseModel):
    """
    Appointments booked by users
    Collection name: "appointment"
    """
    user_id: str
    service_id: str
    service_title: str
    start_time_iso: str  # ISO 8601 string
    duration_minutes: int
    status: str = Field("scheduled", description="scheduled|completed|canceled")
    order_id: Optional[str] = None

class OrderItem(BaseModel):
    service_id: str
    service_title: str
    quantity: int = 1
    price_cents: int

class Order(BaseModel):
    """
    Orders for checkouts
    Collection name: "order"
    """
    user_id: str
    items: List[OrderItem]
    amount_cents: int
    status: str = Field("pending", description="pending|paid|canceled")
    stripe_session_id: Optional[str] = None
    stripe_payment_intent: Optional[str] = None
    paid_at: Optional[datetime] = None
