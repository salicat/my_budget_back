from pydantic import BaseModel
from datetime import date

class GoalIn (BaseModel):
    name        : str
    username    : str
    final_value : float
    final_date  : date

class GoalUp (BaseModel):
    name        : str
    username    : str
    value       : float

class GoalDel (BaseModel):
    username    : str
    name        : str

class GoalOut (BaseModel):
    name        : str
    current_val : float
    final_value : float
    final_date  : date

    class Config:
        from_attributes = True
    