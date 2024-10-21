from fastapi import FastAPI, HTTPException, Depends
import uvicorn
from db import get_db_pool
import aiomysql
import datetime
from pydantic import BaseModel
from chatbot import send_message_to_chatgpt, reset_conversation, Feelings
from typing import Optional

app = FastAPI()

class Goal(BaseModel):
    goal: str
    user_id: str

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

@app.on_event("startup")
async def startup():
    app.state.pool = await get_db_pool()
    
@app.on_event("shutdown")
async def shutdown():
    app.state.pool.close()
    await app.state.pool.wait_closed()
    
    
# Modelo para la solicitud de mensaje
class MessageRequest(BaseModel):
    message: str
    feelings: Optional[Feelings] = None
    comment: Optional[str] = None

# Endpoint para enviar un mensaje
@app.post("/send_message")
async def send_message_endpoint(request: MessageRequest):
    response = await send_message_to_chatgpt(request.message, request.feelings, request.comment)
    return {"response": response}

# Endpoint para reiniciar la conversación
@app.post("/reset_conversation")
def reset_conversation_endpoint():
    reset_conversation()
    return {"status": "Conversación reiniciada"}        

@app.get("/goals/{user_id}")
async def get_goal(user_id: str):
    async with app.state.pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SELECT id, goal, user_id FROM goals WHERE user_id = %s AND deleted = 0", (user_id,))
            result = await cursor.fetchall()
            if result is None:
                return []
            return result
        
@app.delete("/goals/{goal_id}")
async def get_goal(goal_id: int):
    async with app.state.pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("UPDATE goals SET deleted = 1 WHERE id = %s", (goal_id,))
            await conn.commit()
            return "Success"        
                
@app.post("/goals")
async def create_goal(goal: Goal):
    date_now = datetime.datetime.now()
    async with app.state.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            query = "INSERT INTO goals (goal, user_id, created_at, updated_at) VALUES (%s, %s, %s)"
            await cursor.execute(query, (goal.goal, goal.user_id, date_now, date_now))
            await conn.commit()
            return goal 

@app.put("/goals/{goal_id}", response_model=Goal)
async def update_goal(goal_id: int, updated_goal: Goal):
    date_now = datetime.datetime.now()
    async with app.state.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # Check if the goal exists
            await cursor.execute("SELECT * FROM goals WHERE id = %s", (goal_id,))
            result = await cursor.fetchone()
            if result is None:
                raise HTTPException(status_code=404, detail="Goal not found")

            # Update the goal
            query = """
            UPDATE goals
            SET goal = %s, user_id = %s, updated_at = %s
            WHERE id = %s
            """
            await cursor.execute(query, (updated_goal.goal, updated_goal.user_id, date_now, goal_id))
            await conn.commit()  # Commit the transaction
            
            return updated_goal  # Return the updated goal       
        
         

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)