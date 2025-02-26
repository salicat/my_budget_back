from pydantic import BaseModel

class UserIn(BaseModel):
    username    : str
    password    : str

class UserOut(BaseModel):
    username    : str
    incomes     : float
    expenses    : float
    liabilities : float
    passives    : float
    
    class Config:
        from_attributes = True

