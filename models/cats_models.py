from pydantic import BaseModel

class CatIn(BaseModel):
    category    : str
    type        : str
    username    : str
    value       : int
    budget      : int    

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