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

HEADER_KEYWORDS = {
    "precio", "importe", "descripción", "unidad", "(€)", "ticket", "caja", "centro",
    "cif", "subtotal", "impuesto", "base imponible", "iva", "cuota", "nif", "factura",
    "hora", "fecha", "op:", "nº", "operation", "contactless", "verific", "tarjeta..bancaria",
    "pvp", "pvp/unit"
}

STORE_KEYWORDS = {
    "mercadona", "starbucks", "grupo dia", "dia", "pet r", "petrer", "cl guadari", "amorebieta",
    "kuta", "bali", "feedback", "address", "avda.", "telefono", "teléfono"
}

PAYMENT_KEYWORDS = {
    "tarjeta", "efectivo", "pago", "credit", "debit", "card", "cash", "bancaria", "mastercard",
    "visa"
}


def extract_price(value: str) -> float:
    """
    Convierte un string numérico a float usando el último separador como decimal.
    Maneja posibles formatos como:
      - "1,000.00"
      - "1000,00"
      - "1.000,00"
      - "62,000" (caso Starbucks, 62 mil)
    """
    value = re.sub(r'[^\d.,]', '', value)  # Elimina caracteres no deseados
    if ',' in value and '.' in value:
        # Caso europeo: 1.000,00 -> 1000.00
        value = value.replace('.', '').replace(',', '.')
    elif ',' in value:
        # Si la parte final tras la coma tiene 3 dígitos, se asume separador de miles
        partes = value.split(',')
        if len(partes[-1]) == 3:
            value = ''.join(partes)
        else:
            value = value.replace(',', '.')
    try:
        return float(value)
    except Exception:
        return 0.0

def is_line_irrelevant(line: str) -> bool:
    """
    Determina si una línea se considera irrelevante porque contiene
    datos de cabecera, direcciones, CIF, etc.
    """
    l = line.lower()
    # Marcar como irrelevante si coincide con alguna palabra clave
    if any(k in l for k in HEADER_KEYWORDS):
        return True
    if any(k in l for k in STORE_KEYWORDS):
        return True
    return False

def parse_products(lines: List[str]) -> List[Dict[str, Any]]:
    """
    Procesa las líneas para extraer artículos con (cantidad, nombre, precio).
    Se asume que:
      - Si una línea comienza con dígitos, se interpretan como cantidad (p.ej. "2 SOJA NATURAL").
      - Si no hay cantidad, se asume 1.
      - El precio se extrae del último número que tenga coma o punto (ej: "1,99" o "62,000").
      - Si se detecta la palabra 'total' en la línea, se asume fin de productos.
    """
    products = []
    current_product: Dict[str, Any] = {}

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        # Si la línea contiene la palabra "total", asumimos que ya no hay más productos
        if "total" in line_clean.lower():
            break

        # Saltar líneas irrelevantes
        if is_line_irrelevant(line_clean):
            continue

        # Caso 1: Línea que inicia con cantidad y algo más (ej: "2 SOJA NATURAL")
        match = re.match(r'^(\d+)\s+(.+)$', line_clean)
        if match:
            # Si había un producto en curso sin precio, cerrarlo
            if current_product and "price" not in current_product:
                current_product.setdefault("quantity", 1)
                current_product.setdefault("name", "Sin nombre")
                current_product["price"] = 0.0
                products.append(current_product)
                current_product = {}

            qty, name_part = match.groups()
            current_product["quantity"] = int(qty)
            current_product["name"] = name_part.strip()

            # Verificar si en la misma línea viene un precio
            price_candidates = re.findall(r'(\d+(?:[.,]\d+)+)', line_clean)
            if price_candidates:
                price_str = price_candidates[-1]  # último valor
                current_product["price"] = extract_price(price_str)
                products.append(current_product)
                current_product = {}
            continue

        # Caso 2: Línea con un posible precio (buscamos el último número con separador)
        price_candidates = re.findall(r'(\d+(?:[.,]\d+)+)', line_clean)
        if price_candidates:
            # Extraemos el precio y el resto lo consideramos nombre
            price_str = price_candidates[-1]
            price_val = extract_price(price_str)

            # Si no hay cantidad, asumimos 1
            if "quantity" not in current_product:
                current_product["quantity"] = 1

            # Si no hay nombre, el resto de la línea (sin el precio) es el nombre
            if "name" not in current_product or not current_product["name"]:
                name_candidate = re.sub(r'(\d+(?:[.,]\d+)+)\s*$', '', line_clean).strip()
                current_product["name"] = name_candidate if name_candidate else "Sin nombre"

            current_product["price"] = price_val
            products.append(current_product)
            current_product = {}
        else:
            # Caso 3: Si no se encontró precio, asumimos que es parte del nombre
            if "name" in current_product:
                current_product["name"] += " " + line_clean
            else:
                current_product["name"] = line_clean

    # Si al final queda un producto sin precio, cerrarlo con precio 0
    if current_product:
        current_product.setdefault("quantity", 1)
        current_product.setdefault("name", "Sin nombre")
        current_product.setdefault("price", 0.0)
        products.append(current_product)

    return products

def find_ticket_total(lines: List[str]) -> float:
    """
    Busca el valor total en las líneas. Recorre de abajo hacia arriba
    y si encuentra la palabra "total" (o "grand total"), intenta extraer
    el valor en la misma línea o en las siguientes 2 líneas.
    Evita líneas que tengan "subtotal", "base imponible", "iva", etc.
    """
    exclude_if_contains = {"subtotal", "imponible", "iva", "impuesto", "tax", "cuota"}
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip().lower()
        if "total" in line or "grand total" in line:
            # Omitir si es "subtotal", "iva", etc.
            if any(word in line for word in exclude_if_contains):
                continue

            # Intentar extraer el número en la misma línea
            matches = re.findall(r'\d+(?:[.,]\d+)+', line)
            if matches:
                return extract_price(matches[-1])

            # Si no hay número en la misma línea, mirar 1-2 líneas siguientes
            for j in range(i + 1, min(i + 3, len(lines))):
                next_line = lines[j].strip().lower()
                # Evitar líneas irrelevantes de subtotales/impuestos
                if any(word in next_line for word in exclude_if_contains):
                    continue
                # Buscar precios
                matches_next = re.findall(r'\d+(?:[.,]\d+)+', next_line)
                if matches_next:
                    return extract_price(matches_next[-1])

    return 0.0



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

def extract_total(lines: List[str]) -> float:
    payment_keywords = {'tarjeta', 'efectivo', 'pago', 'credit', 'debit', 'card', 'cash', 'bancaria'}
    for i in range(len(lines)):
        line_clean = lines[i].strip().lower()
        if "total" in line_clean:
            # Verificar las siguientes 2 líneas para palabras clave de pago
            for j in range(i + 1, min(i + 3, len(lines))):
                next_line_clean = lines[j].strip().lower()
                if any(keyword in next_line_clean for keyword in payment_keywords):
                    numbers = re.findall(r'\d+[\.,]\d+', line_clean)
                    if numbers:
                        return extract_price(numbers[-1])
    # Búsqueda inversa si no se encuentra
    for line in reversed(lines):
        line_clean = line.strip().lower()
        if "total" in line_clean:
            numbers = re.findall(r'\d+[\.,]\d+', line_clean)
            if numbers:
                return extract_price(numbers[-1])
    return 0.0

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
    
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    
    # 1) Todos los registros del usuario
    regs = db.query(RegsInDb).filter(RegsInDb.username == username).all()

    # 2) Filtrar los registros del mes/año solicitados
    user_regs = []
    for reg in regs:
        if reg.date.year == year and reg.date.month == month:
            user_regs.append(reg)

    # 3) Inicializar el historial de gastos de los últimos 12 meses
    resultado = []
    current_month = month
    current_year = year

    for _ in range(12):
        etiqueta = f"{meses[current_month - 1]}'{str(current_year)[-2:]}"
        # Insertamos al principio para que al final queden en orden ascendente
        resultado.insert(0, [etiqueta, 0.0])

        # Retroceder un mes
        current_month -= 1
        if current_month == 0:
            current_month = 12
            current_year -= 1

    # 4) Sumar los gastos (type == "expenses") en cada mes
    for reg in regs:
        if reg.type == "expenses":
            etiqueta_reg = f"{meses[reg.date.month - 1]}'{str(reg.date.year)[-2:]}"
            # Buscar en resultado la etiqueta correspondiente
            for item in resultado:
                if item[0] == etiqueta_reg:
                    item[1] += float(reg.value)
                    break

    # 5) Devolver ambos resultados sin cambiar el frontend
    return user_regs, resultado

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
    db: Session = Depends(get_db), 
):

    try:
        # Validar tipo de archivo
        if not image.content_type.startswith("image/"):
            raise HTTPException(400, "Solo se permiten imágenes JPEG/PNG")

        # Leer y codificar la imagen
        image_content = await image.read()
        encoded_image = base64.b64encode(image_content).decode("utf-8")

        # Llamar a Google Vision
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

        # Extraer texto
        full_text = response.json()["responses"][0]["textAnnotations"][0]["description"]
        logging.info(f"=== TEXTO OCR ===\n{full_text}")

        # Separar por líneas
        lines = full_text.split('\n')

        # 1. Extraer productos
        products = parse_products(lines)

        # 2. Construir registros
        registros = []
        for prod in products:
            registros.append({
                "username": username,
                "date": date.today().isoformat(),
                "type": "expenses",
                "category": "",  # se puede asignar luego
                "description": f"{prod.get('quantity', 1)}x {prod.get('name', 'Sin nombre')}",
                "value": prod.get("price", 0.0) * prod.get("quantity", 1)
            })

        # 3. Buscar total del ticket
        total = find_ticket_total(lines)
        # Agregarlo como un registro "Total Compra" (opcional, según tu lógica)
        registros.append({
            "username": username,
            "date": date.today().isoformat(),
            "type": "expenses",
            "category": "",
            "description": "Total Compra",
            "value": total
        })

        return registros

    except Exception as e:
        logging.error(f"Error en process_receipt: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Error interno: {str(e)}")