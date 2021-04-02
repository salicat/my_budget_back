from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.users_router import router as router_users
from routers.reg_router import router as router_transactions
from routers.cat_router import router as router_categories
from routers.goal_router import router as router_goals

my_budget = FastAPI()

origins = [
    "http://localhost.tiangolo.com", "https://localhost.tiangolo.com",
    "http://localhost", "http://https://https://mybudgetvue.herokuapp.com/", 
    "postgres://postgres:1317@localhost:5432/CARLOS",
]

my_budget.add_middleware(
    CORSMiddleware, allow_origins=origins,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

my_budget.include_router(router_users)
my_budget.include_router(router_transactions)
my_budget.include_router(router_categories)
my_budget.include_router(router_goals)
