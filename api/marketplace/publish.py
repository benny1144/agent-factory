from fastapi import APIRouter
router = APIRouter(prefix='/api/marketplace', tags=['marketplace'])
@router.post('/publish')
def publish():
    return {'ok': True}
