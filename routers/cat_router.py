from typing import List
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import Null
from sqlalchemy.sql.expression import true
from starlette import responses
from db.db_connection import get_db
from db.users_db import UserInDB
from db.regs_db import RegsInDb
from db.cats_db import CatsInDb
from models.cats_models import CatIn, CatDel, CatUpDate, CatOut, CatTypes

router = APIRouter()
 
@router.post("/user/create/category/")
async def create_cat(cat_in: CatIn, db: Session = Depends(get_db)):
    all_cats = db.query(CatsInDb).all()
    user_in_db = db.query(UserInDB).get(cat_in.username)
    user_cats = []
    for cat in all_cats:
        if cat.username == cat_in.username:
                user_cats.append(cat.category)
    if cat_in.category in user_cats:
        raise HTTPException(status_code=403, detail="Ya tienes una categoria llamada " + cat_in.category)
    if cat_in.category not in user_cats:
        user_cats.append(cat_in.category)
        if cat_in.type == "liabilities":
            user_in_db.liabilities = user_in_db.liabilities + cat_in.value
            cat_in.budget = 0
            new_cat = CatsInDb(**cat_in.dict())
            db.add(new_cat)
            db.commit()
            db.flush(new_cat)
        if cat_in.type == "passives":            
            user_in_db.passives = user_in_db.passives + cat_in.value
            cat_in.budget = 0
            new_cat = CatsInDb(**cat_in.dict())
            db.add(new_cat)
            db.commit()
            db.flush(new_cat)
        if cat_in.type == "incomes":
            cat_in.value = 0
            new_cat = CatsInDb(**cat_in.dict())
            db.add(new_cat)
            db.commit()
            db.flush(new_cat)
        if cat_in.type == "expenses":
            cat_in.value = 0
            new_cat = CatsInDb(**cat_in.dict())
            db.add(new_cat)
            db.commit()
            db.flush(new_cat)
    return { "message" : cat_in.category + " creada con exito"}
    
@router.get("/user/cats/{username}")
async def get_cats(username : str, db: Session = Depends(get_db)):
    all_cats = db.query(CatsInDb).all()
    user_cats = {
        "incomes" : [],
        "expenses" : [],
        "liabilities" : [],
        "passives" : []
    }
    for cat in all_cats:
        if cat.username == username:
            if cat.type == "incomes":
                user_cats["incomes"].append({"category":cat.category,
                                            "budget" : cat.budget})
            if cat.type == "expenses":
                user_cats["expenses"].append({"category":cat.category,
                                            "budget" : cat.budget})
            if cat.type == "liabilities":
                user_cats["liabilities"].append({"category":cat.category,
                                            "value" : cat.value})
            if cat.type == "passives":
                user_cats["passives"].append({"category":cat.category,
                                            "value" : cat.value})
    return user_cats
 
@router.delete("/user/delete/category/")
async def delete_cat(cat_del: CatDel, db: Session = Depends(get_db)):
    user_cats = db.query(CatsInDb).get(cat_del.category)
    all_cats = db.query(CatsInDb).all()
    user_in_db = db.query(UserInDB).get(cat_del.username)
    regs_in_db = db.query(RegsInDb).all()
    cat_value = user_cats.value    
    regs_deleted = 0

    for reg in regs_in_db:
        if reg.category == cat_del.category:
            regs_deleted += 1
            db.delete(reg)
            db.commit()
            db.flush(reg)

    for cat in all_cats:
        if cat_del.username == cat.username:
            if cat.category == cat_del.category:
                db.delete(cat)
                db.commit()
                db.flush(cat)
                if cat_del.type == "incomes":
                    user_in_db.incomes = user_in_db.incomes - cat.value
                    db.commit()
                    db.refresh(user_in_db)
                    return {"message" : "Se eliminaron " +  " " + str(regs_deleted) + " registro del usuario " + cat_del.username}              
                if cat_del.type == "expenses":        
                    user_in_db.expenses = user_in_db.expenses - cat_value         
                    db.commit()
                    db.refresh(user_in_db)
                    return {"message" : "Se eliminaron " +  " " + str(regs_deleted) + " registro del usuario " + cat_del.username}
                if cat_del.type == "liabilities":
                    user_in_db.liabilities = user_in_db.liabilities - cat_value
                    db.commit()
                    db.refresh(user_in_db)
                    return {"message" : "Se eliminaron " +  " " + str(regs_deleted) + " registro del usuario " + cat_del.username}
                if cat_del.type == "passives":
                    user_in_db.passives = user_in_db.passives - cat_value           
                    db.commit()
                    db.refresh(user_in_db)
                    return {"message" : "Se eliminaron " +  " " + str(regs_deleted) + " regitro del usuario " + cat_del.username}
                else:
                    return {"Message" : "La cagates!!!"}   


    