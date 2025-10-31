from fastapi import APIRouter
router = APIRouter(prefix='/api/analytics', tags=['analytics'])
@router.get('/usage')
def usage():
    return {'ok': True, 'data': {'streams': []}}
