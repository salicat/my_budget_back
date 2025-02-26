from datetime import date, datetime
from multiprocessing.sharedctypes import Value
from typing import List
from fastapi import Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.functions import user
from db.db_connection import get_db
from db.users_db import UserInDB
from db.regs_db import RegsInDb
from db.cats_db import CatsInDb
from models.reg_models import RegIn, RegConsult, RegDel, RegOut, RegTrack, ChatbotQuery
from models.user_models import UserOut, UserIn
import os


router = APIRouter()

@router.post("/user/register/")
async def make_register(reg_in: RegIn, db: Session = Depends(get_db)):
    user_in_db = db.query(UserInDB).get(reg_in.username)
    all_cats = db.query(CatsInDb).all()
    user_cats = []        
    for cat in all_cats:        
        if cat.username == reg_in.username:
            user_cats.append(cat.category)


    if reg_in.type == "incomes":
        new_reg_in = RegsInDb(**reg_in.dict())
        db.add(new_reg_in)
        db.commit()
        db.refresh(new_reg_in)
    if reg_in.type == "expenses":
        new_reg_in = RegsInDb(**reg_in.dict())
        db.add(new_reg_in)
        db.commit()
        db.refresh(new_reg_in)
    if reg_in.type == "liabilities":        
        user_in_db.liabilities = user_in_db.liabilities + reg_in.value
        new_reg_in = RegsInDb(**reg_in.dict())
        db.add(new_reg_in)
        db.commit()
        db.refresh(new_reg_in)
    if reg_in.type == "passives":    
        user_in_db.passives = user_in_db.passives + reg_in.value
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

@router.get("/user/month_records/{username}/{year}/{month}")
async def month_records(username: str, year:int, month:int, db:Session = Depends(get_db)):
    regs = db.query(RegsInDb).all()
    for reg in regs:
        if reg.date.year == 20223:  # Verificar año fuera de rango
            print(f"Registro con año inválido encontrado: {reg}")

    user_regs = []
    for reg in regs:
        if reg.username == username:
            if reg.date.year == year: 
                if reg.date.month == month: 
                    user_regs.append(reg)         
    return  user_regs

@router.get("/user/month_regs/{username}/{year}/{month}")
async def rec_date(username: str, year: int, month :int, db: Session = Depends(get_db)):
    regs = db.query(RegsInDb).all()    
    user_cats = []
    cats = db.query(CatsInDb).all()    

    for cat in cats:
        if username == cat.username:                        
            if cat.type == "expenses":
                if cat.recurrency == True:
                    user_cats.append({  "category"  : cat.category, 
                                        "budget"    : cat.budget,
                                        "value"     : 0,
                                        "expires"   : cat.day
                                                    })

    for reg in regs:
        if reg.date.month == month:
            if reg.date.year == year:
                for cat in user_cats:
                    if reg.category in cat["category"]:       
                        cat["value"] = cat["value"] + reg.value                                                 
        
    return user_cats



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
        if i.type == "liabilities":
            user_in_db.liabilities = user_in_db.liabilities - i.value
            db.commit()
            db.refresh(user_in_db)
        if i.type == "passives":
            user_in_db.passives = user_in_db.passives - i.value
            db.commit()
            db.refresh(user_in_db)

    return len(user_regs)

@router.get("/user/track/{username}/{year}/{month}/{category}")
async def track_months(username: str, year: int, month: int, category: str, db: Session = Depends(get_db)):
    # Nombres de los meses con abreviaturas
    meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 
             'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

    # Inicializar la lista de meses en orden ascendente, terminando en el mes solicitado
    resultado = []
    current_month = month
    current_year = year

    for _ in range(12):
        # Agregar el mes actual al inicio del resultado
        resultado.insert(0, [f"{meses[current_month - 1]}'{str(current_year)[-2:]}", 0])

        # Retroceder un mes
        current_month -= 1
        if current_month == 0:
            current_month = 12
            current_year -= 1

    # Obtener todos los registros de la base de datos
    registros = db.query(RegsInDb).all()

    # Iterar sobre los registros para sumar los valores correspondientes
    for reg in registros:
        if reg.username == username and reg.category == category:
            reg_month = reg.date.month
            reg_year = reg.date.year

            # Buscar la posición del mes y año del registro en el resultado
            for i, (mes_label, _) in enumerate(resultado):
                if mes_label == f"{meses[reg_month - 1]}'{str(reg_year)[-2:]}":
                    resultado[i][1] += reg.value
                    break

    return resultado



@router.get("/user/incomes/{username}/{month}/")
async def user_incomes(username : str, month: int, db: Session = Depends(get_db)):
    regs = db.query(RegsInDb).all()
    user_incomes = []
    user_expenses = []
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 
                    'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 
                    'Noviembre', 'Diciembre']
    
    for u in regs:
        if username == u.username:
            if u.type == "incomes":
                user_incomes.append(u)
            elif u.type == "expenses":
                user_expenses.append(u)

    return {"expenses": user_expenses,
            "incomes" : user_incomes}

