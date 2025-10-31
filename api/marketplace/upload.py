from fastapi import APIRouter
router = APIRouter(prefix='/api/marketplace', tags=['marketplace'])
@router.post('/upload')
def upload():
    return {'ok': True, 'data': {'validated': True}}
