from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import datetime
import aiomysql
from typing import List

router = APIRouter()


class Goal(BaseModel):
    goal: str
    user_id: str
    goals: List[str]


@router.get("/goals/{user_id}")
async def get_goals(user_id: str, request: Request):
    pool = request.app.state.pool
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                "SELECT id, goal, user_id, parent, status FROM goals WHERE user_id = %s AND deleted = 0",
                (user_id,),
            )
            data = await cursor.fetchall()
            if data is None:
                return []

            results = []

            for item in data:
                if item['parent'] is None:
                    # Crear un nuevo diccionario para el goal sin parent
                    goal_with_subgoals = item.copy()
                    goal_with_subgoals['goals'] = []
                    
                    # Agregar sub-goals a este goal
                    for sub_item in data:
                        if sub_item['parent'] == item['id']:
                            goal_with_subgoals['goals'].append(sub_item)
                    
                    # Agregar el goal principal a los resultados
                    results.append(goal_with_subgoals)
            return results

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
            inserted_id = cursor.lastrowid
            await conn.commit()
            for n in goal.goals:
                query = "INSERT INTO goals (goal, user_id, created_at, updated_at, parent) VALUES (%s, %s, %s, %s, %s)"
                await cursor.execute(query, (n, goal.user_id, date_now, date_now, inserted_id))
                await conn.commit()
            return inserted_id


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
