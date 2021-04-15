from datetime import date, datetime
from fastapi import Depends, APIRouter, HTTPException
from pydantic.networks import HttpUrl
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import user
from db.db_connection import get_db
from db.users_db import UserInDB
from db.regs_db import RegsInDb
from db.cats_db import CatsInDb
from db.goals_db import GoalsInDb
from models.reg_models import RegIn, RegConsult, RegOut
from models.user_models import UserOut, UserIn
from models.goal_models import GoalIn, GoalUp, GoalDel, GoalOut

router = APIRouter()

@router.post("/user/goals/set/")
async def set_goal(goal_in:GoalIn, db : Session = Depends(get_db)):
    user_in_db = db.query(UserInDB).get(goal_in.username)
    goals = db.query(GoalsInDb).all()
    user_goals = []
    
    for goal in goals:
        if goal.username == goal_in.username:
            user_goals.append(goal.name)
    if goal_in.name in user_goals:
        raise HTTPException(status_code=403, detail="Ya tienes una meta llamada " + goal_in.name)
    if user_in_db == None:
        raise HTTPException(status_code=404, detail="El usuario " + goal_in.username +  " no existe")
    if goal_in.name not in user_goals:
        user_goals.append(goal_in.name)
        new_goal = GoalsInDb(**goal_in.dict(),
                            current_val = 0
                            )
        db.add(new_goal)
        db.commit()
        db.refresh(new_goal)
        return user_goals    

@router.put("/user/goals/update")
async def goal_update(goal_up : GoalUp, db : Session = Depends(get_db)):
    all_goals = db.query(GoalsInDb).all()
    goals_in_db = db.query(GoalsInDb).get(goal_up.name)
    user_goals = []
    for goal in all_goals:
        if goal_up.username == goal.username:
            user_goals.append(goal.name)
    if goal_up.name not in user_goals:
        raise HTTPException(status_code=404, detail="No tienes una meta llamada " + goal_up.name)
    goals_in_db.current_val = goals_in_db.current_val + goal_up.value
    db.commit()
    db.refresh(goals_in_db)
    
    remain_val = (goals_in_db.final_value - goals_in_db.current_val)/(goals_in_db.final_value)*100  
    return {"message": "Aun te queda " + str(remain_val) + "%"}

@router.get ("/user/goals/track/{username}")
async def goals_track(username : str, db : Session = Depends(get_db)):
    all_goals = db.query(GoalsInDb).all()
    user_goals = []
    for goal in all_goals:
        if username == goal.username:
            today = datetime.date(datetime.today())
            delta = goal.final_date - today
            user_goals.append({"nombre"         : goal.name,
                                "porc"          : round((goal.current_val / goal.final_value) * 100),
                                "meta"          : goal.final_value,
                                "actual"        : goal.current_val, 
                                "dias"          : delta.days
                                })
    return user_goals

@router.delete("/user/goals/delete")
async def delete_goal(goal_del:GoalDel, db: Session= Depends(get_db)):
    goal = db.query(GoalsInDb).get(goal_del.name)    
    if goal_del.username == goal.username:
        db.delete(goal)
        db.commit()
        db.flush(goal)
        return {"Message" : goal.name + " borrado de tu lista de metas"}
    else: 
        return {"Message" : goal.name + " no se ha podido borrar"}