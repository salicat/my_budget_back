from typing import List
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from db.db_connection import get_db
from db.users_db import UserInDB
from db.regs_db import RegsInDb
from db.cats_db import CatsInDb
from models.user_models import UserIn, UserOut

router = APIRouter()

@router.post("/user/auth/")
async def auth_user(user_in: UserIn, db: Session = Depends(get_db)):
    print("request started")
    user_in_db = db.query(UserInDB).get(user_in.username)
    
    
    
    if user_in_db == None:
        raise HTTPException(status_code=404, detail="El usuario no existe")
    if user_in_db.password != user_in.password:
       raise HTTPException(status_code=403, detail="Error de autenticacion")
    return {"Autenticado": True}

@router.post("/user/create/")
async def create_user(user_in: UserIn, db: Session = Depends(get_db)):
    user_in_db = db.query(UserInDB).get(user_in.username)
    print(user_in_db)
    if user_in_db == None:
        new_user = UserInDB(**user_in.dict(),
                            liabilities = 0,
                            passives    = 0,
                            )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    if user_in.username == user_in_db.username:
        raise HTTPException(status_code=403, detail="Ya existe un usuario con el nombre "+ user_in.username)
    
    
@router.get("/user/resumen/{username}")
async def get_balance(username: str, db: Session = Depends(get_db)):
    user_in_db = db.query(UserInDB).get(username)
    if user_in_db == None:
        raise HTTPException(status_code=404, detail="El usuario no existe")
        
    return {"liabilities" : user_in_db.liabilities,
            "passives" : user_in_db.passives,
            }
