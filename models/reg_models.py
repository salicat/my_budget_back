from pydantic import BaseModel
from datetime import date

class RegIn(BaseModel):
    username    : str
    type        : str
    category    : str
    description : str
    value       : int

class RegConsult(BaseModel):
    username: str
    type: str
    category :str    

class RegDel(BaseModel):
    id : list
    username : str


class RegOut(BaseModel):
    username    : str
    date        : date
    type        : str
    category    : str
    value       : int

    class Config:
        orm_mode = True  
    





