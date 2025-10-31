from __future__ import annotations
from fastapi import APIRouter
from tools.agent_packager import import_agent

router = APIRouter(prefix='/api/agents', tags=['agents'])

@router.post('/import')
def import_endpoint(pkg: str, dest: str):
    return {'ok': True, 'data': {'dest': import_agent(pkg, dest)}}
