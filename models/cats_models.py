from pydantic import BaseModel
from datetime import date

class CatIn(BaseModel):
    category    : str
    type        : str
    username    : str
    budget      : int
    value       : int    
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
    value       : int

class CatOut(BaseModel):
    category    : str
    type        : str
    act_value   : int
    
    class Config:
        orm_mode = True  