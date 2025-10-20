"""
Event API endpoints.

Provides REST API endpoints for event management.
"""

from fastapi import APIRouter
from .models import Event, Store
from .repository import load_store, save_store


# Create router for events domain
router = APIRouter()


@router.get("", response_model=Store)
def get_events():
    """
    Get all events.

    Returns:
        Store: All events in the store
    """
    return load_store()


@router.post("/replace", response_model=Store)
def replace_all(store: Store):
    """
    Replace all events in the store.

    Args:
        store: New complete event store

    Returns:
        Store: The updated event store
    """
    save_store(store.model_dump())
    return store


@router.post("/upsert", response_model=Store)
def upsert_event(ev: Event):
    """
    Insert or update an event.

    Events are matched by title (case-insensitive) and date.
    If a match is found, the event is updated; otherwise, it's inserted.
    Events are kept in chronological order with most recent first.

    Args:
        ev: Event to upsert

    Returns:
        Store: The updated event store
    """
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

    # Sort events in descending chronological order (most recent first)
    new_events.sort(key=lambda e: e["date"], reverse=True)

    store["events"] = new_events
    save_store(store)
    return store


@router.post("/delete")
def delete_event(ev: Event):
    """
    Delete an event from the store.

    Events are matched by title (case-insensitive) and date.

    Args:
        ev: Event to delete (only title and date are used for matching)

    Returns:
        Dict: Success response
    """
    store = load_store()
    key = (ev.title.strip().lower(), ev.date)
    store["events"] = [
        e for e in store["events"]
        if (e["title"].strip().lower(), e["date"]) != key
    ]
    save_store(store)
    return {"ok": True}

