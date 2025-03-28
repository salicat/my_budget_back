from datetime import date, datetime
from typing import List, Dict, Any
from multiprocessing.sharedctypes import Value
from typing import List
from fastapi import Depends, APIRouter, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.functions import user
from db.db_connection import get_db
from db.users_db import UserInDB
from db.regs_db import RegsInDb
from db.cats_db import CatsInDb
from models.reg_models import RegIn, RegConsult, RegDel, RegOut, RegTrack, ChatbotQuery
from models.user_models import UserOut, UserIn
from io import BytesIO
import os
import json
import base64
import requests
import logging
import re
from dotenv import load_dotenv


router = APIRouter()

load_dotenv()
GOOGLE_VISION_URL = "https://vision.googleapis.com/v1/images:annotate"
API_KEY = os.getenv("API_KEY") 

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def extract_price(value: str) -> float:
    """Convierte un string numérico a float usando el último separador como decimal."""
    # Elimina cualquier caracter que no sea dígito, coma o punto
    value = re.sub(r'[^\d.,]', '', value)
    # Si hay coma y punto, asumimos formato europeo (ej: 1.000,00 → 1000.00)
    if ',' in value and '.' in value:
        value = value.replace('.', '').replace(',', '.')
    # Si solo hay coma, se asume como separador decimal a menos que el segmento posterior tenga 3 dígitos (posible separador de miles)
    elif ',' in value:
        partes = value.split(',')
        if len(partes[-1]) == 3:
            value = ''.join(partes)
        else:
            value = value.replace(',', '.')
    try:
        return float(value)
    except Exception:
        return 0.0

def parse_products(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Procesa las líneas extraídas por OCR y devuelve una lista de diccionarios
    con los datos de cada producto (cantidad, nombre y precio).
    
    La función detecta el precio buscando el último número en la línea que contenga
    separador (coma o punto). Se asume que si la línea inicia con dígitos, estos son la cantidad.
    Si no se encuentra cantidad se asigna 1 por defecto.
    La información se arma de forma independiente al formato del ticket.
    """
    products = []
    current_product: Dict[str, Any] = {}

    # Lista de palabras de cabecera que pueden ayudar a identificar que no es producto
    header_keywords = ["precio", "importe", "descripción", "unidad", "(€)", "total", "ticket", "caja", "centro", "cif"]

    def is_header(line: str) -> bool:
        for word in header_keywords:
            if word.lower() in line.lower():
                return True
        return False

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
        # Si la línea es un encabezado o contiene "total" (se ignora la parte final del ticket)
        if is_header(line_clean):
            if "total" in line_clean.lower():
                # Se finaliza la lectura al encontrar "total" (se asume fin de productos)
                break
            continue

        # Caso 1: Línea que inicia con cantidad y nombre (ej: "2 SOJA NATURAL")
        match = re.match(r'^(\d+)\s+(.+)$', line_clean)
        if match:
            # Si hay un producto en curso sin precio, lo finalizamos con precio 0.0
            if current_product and "price" not in current_product:
                current_product.setdefault("quantity", 1)
                current_product.setdefault("name", "")
                current_product["price"] = 0.0
                products.append(current_product)
                current_product = {}
            qty, name = match.groups()
            current_product["quantity"] = int(qty)
            current_product["name"] = name.strip()
            # Revisar si en la misma línea hay un precio al final (número con separador)
            price_matches = re.findall(r'(\d+(?:[.,]\d+)+)', line_clean)
            if price_matches:
                # Tomar el último valor como precio
                price_str = price_matches[-1]
                current_product["price"] = extract_price(price_str)
                products.append(current_product)
                current_product = {}
            continue

        # Caso 2: Línea que es solo un número (posible cantidad o precio)
        if re.fullmatch(r'\d+', line_clean):
            # Si no hay cantidad definida, asignar como cantidad
            if "quantity" not in current_product:
                current_product["quantity"] = int(line_clean)
            else:
                # Si ya existe cantidad, quizá se trate de un precio sin separador,
                # pero como no cumple el formato (falta separador), se ignora.
                pass
            continue

        # Caso 3: Línea que contiene un número con separador (precio)
        price_candidates = re.findall(r'(\d+(?:[.,]\d+)+)', line_clean)
        if price_candidates:
            price_str = price_candidates[-1]  # Usar el último valor encontrado
            current_product["price"] = extract_price(price_str)
            # Si no se tenía cantidad, se asume 1
            if "quantity" not in current_product:
                current_product["quantity"] = 1
            # Si no se tenía nombre, se asume que el resto de la línea (sin el precio) es el nombre
            if "name" not in current_product or not current_product["name"]:
                # Remover el precio de la línea y limpiar
                name_candidate = re.sub(r'(\d+(?:[.,]\d+)+)\s*$', '', line_clean).strip()
                current_product["name"] = name_candidate if name_candidate else "Sin nombre"
            products.append(current_product)
            current_product = {}
            continue

        # Caso 4: Línea que es texto y se asume parte del nombre del producto
        if "name" in current_product:
            current_product["name"] += " " + line_clean
        else:
            current_product["name"] = line_clean

    # Si queda un producto sin precio asignado, se finaliza con precio 0.0
    if current_product:
        current_product.setdefault("quantity", 1)
        current_product.setdefault("name", "Sin nombre")
        current_product.setdefault("price", 0.0)
        products.append(current_product)

    return products

def google_vision_ocr(image_content: bytes) -> List[str]:
    try:
        encoded_image = base64.b64encode(image_content).decode("utf-8")
        response = requests.post(
            f"{GOOGLE_VISION_URL}?key={API_KEY}",
            json={
                "requests": [{
                    "image": {"content": encoded_image},
                    "features": [{"type": "TEXT_DETECTION"}]
                }]
            }
        )
        response.raise_for_status()
        full_text = response.json()["responses"][0]["textAnnotations"][0]["description"]
        logging.info(f"Texto detectado:\n{full_text}")

        lines = full_text.split('\n')
        products = parse_products(lines)
        formatted_products = []
        for prod in products:
            nombre = prod.get("name", "Sin nombre")
            precio = prod.get("price", 0.0)
            cantidad = prod.get("quantity", 1)
            formatted_products.append(f"{cantidad}x {nombre} - {precio}")
        return formatted_products

    except Exception as e:
        logging.error(f"Error en google_vision_ocr: {str(e)}")
        raise


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
    
    user_regs = []
    for reg in regs:
        if reg.username == username:
            if reg.date.year == year: 
                if reg.date.month == month: 
                    user_regs.append(reg)         
    return  user_regs

@router.get("/user/month_regs/{username}/{year}/{month}")
async def rec_date(username: str, year: int, month: int, db: Session = Depends(get_db)):
    regs = db.query(RegsInDb).filter(RegsInDb.username == username).all()    
    cats = db.query(CatsInDb).filter(CatsInDb.username == username).all()    
    
    user_cats = []
    for cat in cats:
        if cat.type == "expenses" and cat.recurrency == True:
            user_cats.append({
                "category"  : cat.category, 
                "budget"    : cat.budget,
                "value"     : 0,
                "expires"   : cat.day
            })

    for reg in regs:
        if reg.date.month == month and reg.date.year == year:
            for cat in user_cats:
                # Usar comparación exacta en lugar de 'in'
                if reg.category == cat["category"]:
                    cat["value"] += reg.value                                                 
        
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


#image Recongnition
@router.post("/process-receipt/{username}")
async def process_receipt(
    username: str,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        if not image.content_type.startswith("image/"):
            raise HTTPException(400, "Solo imágenes JPEG/PNG")
        
        image_content = await image.read()
        encoded_image = base64.b64encode(image_content).decode("utf-8")
        response = requests.post(
            f"{GOOGLE_VISION_URL}?key={API_KEY}",
            json={
                "requests": [{
                    "image": {"content": encoded_image},
                    "features": [{"type": "TEXT_DETECTION"}]
                }]
            }
        )
        response.raise_for_status()
        full_text = response.json()["responses"][0]["textAnnotations"][0]["description"]
        logging.info(f"=== TEXTO OCR ===\n{full_text}")

        lines = full_text.split('\n')
        products = parse_products(lines)

        registros = []
        for prod in products:
            registros.append({
                "username": username,
                "date": date.today().isoformat(),
                "type": "expenses",
                "category": "Otros",
                "description": f"{prod.get('quantity', 1)}x {prod.get('name', 'Sin nombre')}",
                "value": prod.get("price", 0.0) * prod.get("quantity", 1)
            })

        user_categories = db.query(CatsInDb.category).filter(
            CatsInDb.username == username
        ).all()
        user_categories = [cat[0] for cat in user_categories]
        
        for registro in registros:
            for cat in user_categories:
                if cat.lower() in registro["description"].lower():
                    registro["category"] = cat
                    break

        total = None
        for line in lines:
            line_clean = line.strip().lower()
            if "total" in line_clean:
                numeros = re.findall(r'\d+(?:[.,]\d+)+', line_clean)
                if numeros:
                    total = extract_price(numeros[-1])
                    break

        if total is not None:
            suma_calculada = sum(item["value"] for item in registros)
            if abs(suma_calculada - total) > 2.0:
                logging.warning(f"⚠️ Validación fallida: Total ({total}) vs Calculado ({suma_calculada})")

        return registros

    except Exception as e:
        logging.error(f"Error en process_receipt: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Error interno: {str(e)}")