from calendar import month
from pickletools import float8
from unicodedata import category
from pydantic import BaseModel
from datetime import date

class RegIn(BaseModel):
    username    : str
    date        : date
    type        : str
    category    : str
    description : str
    value       : float

class RegConsult(BaseModel):
    username    : str
    month       : int
    year        : int

class RegMonth(BaseModel):
    category    : str
    budget      : float
    value       : float
    
class RegDel(BaseModel):
    id          : list
    username    : str

class RegTrack(BaseModel):
    username    : str
    month       : int
    category    : str

class RegOut(BaseModel):
    username    : str
    date        : date
    type        : str
    category    : str
    value       : float
    
class ChatbotQuery(BaseModel):
    query: str

    class Config:
        from_attributes = True
    






