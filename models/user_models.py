from pydantic import BaseModel

class UserIn(BaseModel):
    username    : str
    password    : str

class UserOut(BaseModel):
    username    : str
    incomes     : int
    expenses    : int
    liabilities : int
    passives    : int
    
    class Config:
        orm_mode = True  

