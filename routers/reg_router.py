from typing import List
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import user
from db.db_connection import get_db
from db.users_db import UserInDB
from db.regs_db import RegsInDb
from db.cats_db import CatsInDb
from models.reg_models import RegIn, RegConsult, RegDel, RegOut
from models.user_models import UserOut, UserIn

router = APIRouter()

@router.post("/user/register/")
async def make_register(reg_in: RegIn, db: Session = Depends(get_db)):
    user_in_db = db.query(UserInDB).get(reg_in.username)
    cat_in_db = db.query(CatsInDb).get(reg_in.category)
    all_cats = db.query(CatsInDb).all()
    user_cats = []       
    for cat in all_cats:        
        if cat.username == reg_in.username:
            user_cats.append(cat.category)
    
    if reg_in.category not in user_cats:
        raise HTTPException(status_code=403, detail="no tienes una categoria " + reg_in.category)
    if reg_in.type == "incomes":
        user_in_db.incomes = user_in_db.incomes + reg_in.value
        cat_in_db.value = cat_in_db.value + reg_in.value 
        new_reg_in = RegsInDb(**reg_in.dict())
        db.add(new_reg_in)
        db.commit()
        db.refresh(new_reg_in)
    if reg_in.type == "expenses":
        user_in_db.expenses = user_in_db.expenses + reg_in.value
        cat_in_db.value = cat_in_db.value + reg_in.value 
        new_reg_in = RegsInDb(**reg_in.dict())
        db.add(new_reg_in)
        db.commit()
        db.refresh(new_reg_in)
    if reg_in.type == "liabilities":        
        user_in_db.liabilities = user_in_db.liabilities + reg_in.value
        cat_in_db.value = cat_in_db.value + reg_in.value 
        new_reg_in = RegsInDb(**reg_in.dict())
        db.add(new_reg_in)
        db.commit()
        db.refresh(new_reg_in)
    if reg_in.type == "passives":    
        user_in_db.passives = user_in_db.passives + reg_in.value
        cat_in_db.value = cat_in_db.value + reg_in.value
        new_reg_in = RegsInDb(**reg_in.dict())
        db.add(new_reg_in)
        db.commit()
        db.refresh(new_reg_in)
            
    
    return {"Message" : "registro " + reg_in.category + " exitoso, valor : " + str(reg_in.value)}

    
@router.get("/user/records/{username}")
async def get_records(username:str, db: Session = Depends(get_db)):
    regs = db.query(RegsInDb).all()
    user_regs = []
    for reg in regs:
        if reg.username == username:
            user_regs.append(reg)
    
    return user_regs

@router.delete("/user/records/delete/")
async def del_record(reg_del:RegDel, db: Session = Depends(get_db)):
    regs = db.query(RegsInDb).all()
    user_in_db = db.query(UserInDB).get(reg_del.username)
    user_regs = []
    
    for reg in regs:
        if reg.id in reg_del.id:
            if reg.username == reg_del.username:                    
                user_regs.append(reg)
                db.delete(reg)
                db.commit()
                db.flush(reg)
      
    for i in user_regs:
        if i.type == "incomes":
            user_in_db.incomes = user_in_db.incomes - i.value
            db.commit()
            db.refresh(user_in_db)
        if i.type == "expenses":
            user_in_db.expenses = user_in_db.expenses - i.value
            db.commit()
            db.refresh(user_in_db)
        if i.type == "liabilities":
            user_in_db.liabilities = user_in_db.liabilities - i.value
            db.commit()
            db.refresh(user_in_db)
        if i.type == "passives":
            user_in_db.passives = user_in_db.passives - i.value
            db.commit()
            db.refresh(user_in_db)

    return len(user_regs)
