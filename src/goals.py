from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import datetime
import aiomysql

router = APIRouter()


class Goal(BaseModel):
    goal: str
    user_id: str


@router.get("/goals/{user_id}")
async def get_goals(user_id: str, request: Request):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                "SELECT id, goal, user_id FROM goals WHERE user_id = %s AND deleted = 0",
                (user_id,),
            )
            result = await cursor.fetchall()
            if result is None:
                return []
            return result


@router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: int, request: Request):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                "UPDATE goals SET deleted = 1 WHERE id = %s", (goal_id,)
            )
            await conn.commit()
            return {"status": "Success"}


@router.post("/goals")
async def create_goal(goal: Goal, request: Request):
    date_now = datetime.datetime.now()
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            query = "INSERT INTO goals (goal, user_id, created_at, updated_at) VALUES (%s, %s, %s, %s)"
            await cursor.execute(query, (goal.goal, goal.user_id, date_now, date_now))
            await conn.commit()
            return goal


@router.put("/goals/{goal_id}", response_model=Goal)
async def update_goal(goal_id: int, updated_goal: Goal, request: Request):
    date_now = datetime.datetime.now()
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM goals WHERE id = %s", (goal_id,))
            result = await cursor.fetchone()
            if result is None:
                raise HTTPException(status_code=404, detail="Goal not found")

            query = """
            UPDATE goals
            SET goal = %s, user_id = %s, updated_at = %s
            WHERE id = %s
            """
            await cursor.execute(
                query, (updated_goal.goal, updated_goal.user_id, date_now, goal_id)
            )
            await conn.commit()
            return updated_goal
