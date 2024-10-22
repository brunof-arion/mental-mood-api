from fastapi import FastAPI
import uvicorn
from db import get_db_pool

from goals import router as goals_router
from chatbot import router as chatbot_router

app = FastAPI()

app.include_router(goals_router)
app.include_router(chatbot_router)

@app.get("/")
def read_root():
    return {"App": "Mental Mood"}

@app.on_event("startup")
async def startup():
    app.state.pool = await get_db_pool()
    
@app.on_event("shutdown")
async def shutdown():
    app.state.pool.close()
    await app.state.pool.wait_closed()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
