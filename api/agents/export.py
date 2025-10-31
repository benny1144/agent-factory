from __future__ import annotations
from fastapi import APIRouter
from tools.agent_packager import export_agent

router = APIRouter(prefix='/api/agents', tags=['agents'])

@router.post('/export')
def export_endpoint(src: str, out: str):
    return {'ok': True, 'data': {'path': export_agent(src, out)}}
