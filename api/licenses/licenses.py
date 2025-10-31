from fastapi import APIRouter
router = APIRouter(prefix='/api/licenses', tags=['licenses'])
@router.get('/')
def index():
    return {'ok': True, 'data': {'visible': []}}
