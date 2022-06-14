from pydantic import BaseModel
from datetime import date

class CatIn(BaseModel):
    id          : int
    category    : str
    type        : str
    username    : str
    budget      : float
    value       : float  
    recurrency  : bool
    day         : date

class CatDel(BaseModel):
    category    : str
    type        : str 
    username    : str

class CatTypes(BaseModel):
    username    : str
    type        : str

class CatUpDate(BaseModel):
    category    : str
    username    : str
    value       : float

class CatOut(BaseModel):
    category    : str
    type        : str
    act_value   : float
    
    class Config:
        orm_mode = True  