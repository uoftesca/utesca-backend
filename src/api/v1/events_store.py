from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from pathlib import Path
import json

print(f"events_store loaded from: {__file__}")

# ----- storage helpers -----
BASE_DIR = Path(__file__).resolve().parent
STORE_PATH = BASE_DIR / "events_store.json"

def load_store():
    if STORE_PATH.exists():
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    return {"events": []}

def save_store(store: dict):
    STORE_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")

# ----- models -----
class Event(BaseModel):
    title: str
    date: str
    description: Optional[str] = ""
    category: Optional[str] = ""
    registrationLink: Optional[str] = ""
    image: Optional[str] = ""
    imagePosition: Optional[str | int] = "center"
    driveLink: Optional[str] = ""

class Store(BaseModel):
    events: List[Event] = Field(default_factory=list)

# IMPORTANT: export a router with a prefix and tag
router = APIRouter(prefix="/events", tags=["Events"])

@router.get("", response_model=Store)
def get_events():
    return load_store()

@router.post("/replace", response_model=Store)
def replace_all(store: Store):
    save_store(store.model_dump())
    return store

@router.post("/upsert", response_model=Store)
def upsert_event(ev: Event):
    store = load_store()
    key = (ev.title.strip().lower(), ev.date)
    new_events, replaced = [], False
    for e in store["events"]:
        if (e["title"].strip().lower(), e["date"]) == key:
            new_events.append(ev.model_dump())
            replaced = True
        else:
            new_events.append(e)
    if not replaced:
        new_events.append(ev.model_dump())
    store["events"] = new_events
    save_store(store)
    return store

@router.post("/delete")
def delete_event(ev: Event):
    store = load_store()
    key = (ev.title.strip().lower(), ev.date)
    store["events"] = [e for e in store["events"] if (e["title"].strip().lower(), e["date"]) != key]
    save_store(store)
    return {"ok": True}
