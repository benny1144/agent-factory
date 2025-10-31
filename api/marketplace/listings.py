from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(prefix='/api/marketplace', tags=['marketplace'])

@router.get('/listings')
def list_packages():
    return {'ok': True, 'data': {'listings': []}}
