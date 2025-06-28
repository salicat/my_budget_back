from datetime import date, datetime
from typing import List
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import Null
from sqlalchemy.sql.expression import null, true
from starlette import responses
from starlette.routing import Router
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
            new_cat = CatsInDb(**cat_in.dict())
            db.add(new_cat)
            db.commit()
            db.flush(new_cat)
        if cat_in.type == "passives":            
            user_in_db.passives = user_in_db.passives + cat_in.value
            new_cat = CatsInDb(**cat_in.dict())
            db.add(new_cat)
            db.commit()
            db.flush(new_cat)
        if cat_in.type == "incomes":
            new_cat = CatsInDb(**cat_in.dict())
            db.add(new_cat)
            db.commit()
            db.flush(new_cat)
        if cat_in.type == "expenses":
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
                user_cats["incomes"].append({   "category"      :cat.category,
                                                "budget"        : cat.budget})
            if cat.type == "expenses":
                user_cats["expenses"].append({  "category"      :cat.category,
                                                "recurrency"    : cat.recurrency,
                                                "budget"        : cat.budget,
                                                "day"           : cat.day})
            if cat.type == "liabilities":
                user_cats["liabilities"].append({   "category"  :cat.category,
                                                    "value"     : cat.value})
            if cat.type == "passives":
                user_cats["passives"].append({      "category"  :cat.category,
                                                    "value"     : cat.value})

    return user_cats

@router.get("/user/cats/{username}/{year}/{month}")
async def expire_cats(username: str, year: int, month: int, db:Session = Depends(get_db)):
    regs = db.query(RegsInDb)  .all()    
    user_cats = []
    cats = db.query(CatsInDb).filter(CatsInDb.username == username).all()
    
    for cat in cats:
        if username == cat.username:                        
            if cat.type == "expenses":
                user_cats.append({  "name"      : cat.category,
                                    "budget"    : cat.budget,
                                    "value"     : 0
                                    })

    for reg in regs:
        if reg.date.month == month:
            if reg.date.year == year:
                if reg.username == username:
                    for cat in user_cats:
                        if reg.category == cat["name"]:
                            cat["value"] = cat["value"] + reg.value    
    
    per_value = sorted(user_cats, key= lambda x:x['value'], reverse=True)

    return per_value

@router.patch("/user/modify/category/")
async def modify_cat(cat_update: CatUpDate, db: Session = Depends(get_db)):
    print("Datos recibidos para modificación:", cat_update)  # Para ver lo que llega
    updated_rows = db.query(CatsInDb).filter(
        CatsInDb.category == cat_update.category,
        CatsInDb.username == cat_update.username
    ).update({
        CatsInDb.budget: cat_update.budget,
        CatsInDb.value: cat_update.value
    }, synchronize_session="fetch")

    if updated_rows:
        db.commit()

    return {"modified_rows": updated_rows}


    

@router.delete("/user/delete/category/")
async def delete_cat(cat_del: CatDel, db : Session = Depends(get_db)):
    # 1. Consulta con print mejorado (usa logging o escribe en stderr)
    categories_to_delete = db.query(CatsInDb).filter(
        CatsInDb.username == cat_del.username,
        CatsInDb.category == cat_del.category
    ).all()
    
    if not categories_to_delete:        
        raise HTTPException(
            status_code=404,
            detail=f"No existe la categoría '{cat_del.category}' para el usuario {cat_del.username}"
        )

    for cat in categories_to_delete:
        db.delete(cat)
    
    db.commit()

    return {"message": f"Categoría '{cat_del.category}' eliminada correctamente"}

