import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson.objectid import ObjectId

from database import db, create_document, get_documents
from schemas import User, Service, Appointment, Order, OrderItem

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Rooted in Speech API"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response


# Utility to convert ObjectId to string
class PublicDoc(BaseModel):
    id: str


def to_public(doc: dict) -> dict:
    if not doc:
        return doc
    d = doc.copy()
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # convert datetime to iso
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


# Seed a few default services if none exist
@app.post("/seed-services")
def seed_services():
    if db["service"].count_documents({}) == 0:
        services = [
            {"title": "Behavior Consultation", "description": "Initial consultation", "price_cents": 15000, "duration_minutes": 60},
            {"title": "Therapy Session", "description": "Follow-up therapy", "price_cents": 9000, "duration_minutes": 45},
        ]
        for s in services:
            create_document("service", s)
        return {"seeded": True, "count": len(services)}
    return {"seeded": False}


# Public services list
@app.get("/api/services")
def list_services():
    docs = get_documents("service")
    return [to_public(d) for d in docs]


# Simple auth placeholders (not production ready)
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


@app.post("/api/register")
def register(req: RegisterRequest):
    existing = db["user"].find_one({"email": req.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(name=req.name, email=req.email, hashed_password=req.password)
    user_id = create_document("user", user)
    return {"id": user_id, "name": req.name, "email": req.email}


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/api/login")
def login(req: LoginRequest):
    user = db["user"].find_one({"email": req.email, "hashed_password": req.password})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"id": str(user["_id"]), "name": user.get("name"), "email": user.get("email")}


# Appointments
class CreateAppointmentRequest(BaseModel):
    user_id: str
    service_id: str
    service_title: str
    start_time_iso: str
    duration_minutes: int


@app.post("/api/appointments")
def create_appointment(req: CreateAppointmentRequest):
    # Basic clash check: ensure no appointment overlaps exact slot
    conflict = db["appointment"].find_one({
        "start_time_iso": req.start_time_iso
    })
    if conflict:
        raise HTTPException(status_code=400, detail="Time slot already booked")

    appt = Appointment(
        user_id=req.user_id,
        service_id=req.service_id,
        service_title=req.service_title,
        start_time_iso=req.start_time_iso,
        duration_minutes=req.duration_minutes,
    )
    appt_id = create_document("appointment", appt)
    return {"id": appt_id}


@app.get("/api/appointments")
def list_appointments(user_id: Optional[str] = None):
    filt = {"user_id": user_id} if user_id else {}
    docs = get_documents("appointment", filt)
    return [to_public(d) for d in docs]


# Orders + Stripe checkout (mock for now, with structure ready)
class CheckoutRequest(BaseModel):
    user_id: str
    items: List[OrderItem]


@app.post("/api/checkout")
def create_checkout(req: CheckoutRequest):
    amount = sum(item.price_cents * item.quantity for item in req.items)
    order = Order(user_id=req.user_id, items=req.items, amount_cents=amount)
    order_id = create_document("order", order)
    # In a production app, integrate Stripe Checkout here and return session URL
    return {"order_id": order_id, "amount_cents": amount, "stripe_checkout_url": None}


@app.get("/api/orders")
def list_orders(user_id: str):
    docs = get_documents("order", {"user_id": user_id})
    return [to_public(d) for d in docs]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
