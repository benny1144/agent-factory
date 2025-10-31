from __future__ import annotations
from fastapi import APIRouter

router = APIRouter(prefix='/api/auth', tags=['auth'])

@router.get('/oauth2/start')
def oauth2_start():
    return {'ok': True, 'data': {'flow': 'oauth2_stub'}}

@router.get('/sso/start')
def sso_start():
    return {'ok': True, 'data': {'flow': 'sso_stub'}}
