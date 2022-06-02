from pydantic import BaseModel
from datetime import date

class GoalIn (BaseModel):
    name        : str
    username    : str
    final_value : int
    final_date  : date

class GoalUp (BaseModel):
    name        : str
    username    : str
    value       : int

class GoalDel (BaseModel):
    username    : str
    name        : str

class GoalOut (BaseModel):
    name        : str
    current_val : int
    final_value : int
    final_date  : date

    class Config:
        orm_mode = True  
    