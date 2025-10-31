from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(prefix='/api/billing', tags=['billing'])

@router.post('/subscribe')
def subscribe(tenant_id: str):
    return {'ok': True, 'data': {'tenant_id': tenant_id, 'status': 'subscribed_stub'}}

@router.post('/webhook')
def webhook():
    return {'ok': True, 'data': {'received': True}}
