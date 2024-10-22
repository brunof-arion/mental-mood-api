import os
import aiomysql
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from typing import Optional
from db import get_db_pool
import requests
from utils import get_secret
from dotenv import load_dotenv

load_dotenv()


router = APIRouter()


class Message(BaseModel):
    message: str
    feelings: Optional["Feelings"] = None
    comment: Optional[str] = None
    user_id: str


class Feelings(BaseModel):
    work: int
    health: int
    relations: int
    finance: int


system_prompt = """
Actúa como un coach virtual empático y servicial que ayuda a los usuarios a identificar sus sentimientos y objetivos en áreas específicas de su vida, como trabajo, salud, relaciones o finanzas. Tu objetivo es entablar una conversación amable y constructiva, haciendo preguntas abiertas que permitan al usuario reflexionar sobre sus metas y desafíos.

- Comienza saludando al usuario de manera cálida.
- Pregunta cómo se siente y qué área le gustaría abordar hoy.
- Escucha activamente y valida sus sentimientos.
- Ayuda al usuario a definir objetivos claros y alcanzables.
- Ofrece sugerencias de acciones concretas que puedan ayudarlo a avanzar.
- Mantén un tono positivo, motivador y respetuoso en todo momento.
- Evita dar consejos médicos o psicológicos profesionales.
- Si el usuario menciona temas sensibles o indica que necesita ayuda profesional, anímalo amablemente a buscar apoyo de un especialista.

El objetivo de esta conversación es poder crear un plan de acción para el usuario.
Cuando lo consideres oportuno, plantea metas y pasos para cumplirlas y pide que lo evalúe.
Esa meta debe contener items como para agregar a una to do list.
El formato de las respuestas debe ser un objeto JSON con el siguiente formato:
{
  "message": "Mensaje de respuesta del asistente",
  "list": [{
    "title": "Título de la lista",
    "list": ["Item 1", "Item 2", ...]
  },
  {
    "title": "Título de la lista 2",
    "list": ["Item 1", "Item 2", ...]
  }]
}
list viene con contenido solo si se está proponiendo una lista de tareas.
Recuerda adaptar tu lenguaje y estilo de comunicación al del usuario para crear una experiencia más personalizada y efectiva.
"""

conversation_history = [{"role": "system", "content": system_prompt}]


async def send_message_to_chatgpt(
    user_id: Optional[str], message: str, feelings: Feelings = None, comment: str = None
) -> str:

    secret_name = os.getenv("SECRET_NAME")
    region_name = os.getenv("REGION_NAME")

    secret_value = get_secret(secret_name, region_name)

    api_key = secret_value.get("OPENAI_API_KEY")
    api_url = "https://api.openai.com/v1/chat/completions"

    if not api_key:
        raise HTTPException(
            status_code=500, detail="La clave de API de OpenAI no está configurada."
        )

    # Si es el primer mensaje y hay feelings, los agregamos al historial
    if feelings and comment:
        feelings_message = f"""El usuario ha indicado sus sentimientos en las siguientes áreas:
        Trabajo: {feelings.work}/4
        Salud: {feelings.health}/4
        Relaciones: {feelings.relations}/4
        Finanzas: {feelings.finance}/4
        Descripción del sentimiento: {comment}
        Por favor, ten en cuenta esta información al iniciar la conversación y ofrecer apoyo."""
        await save_message(user_id, "user", feelings_message)
    else:
        await save_message(user_id, "user", message)

    # Construir el historial de mensajes desde la base de datos
    conversation_history = await get_conversation_history(user_id)

    payload = {"model": "gpt-4", "messages": conversation_history, "temperature": 0.7}

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:

        response = requests.post(api_url, json=payload, headers=headers)
        print("Response status:", response.status_code)

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as json_error:
            print(f"Error parsing JSON: {json_error}")
            return None

        assistant_response = data["choices"][0]["message"]["content"]

        await save_message(user_id, "llm", assistant_response)
        return assistant_response

    except Exception as e:
        print(f"Unhandled Error: {e}")


def reset_conversation():
    conversation_history.clear()
    conversation_history.append({"role": "system", "content": system_prompt})


async def save_message(user_id: int, emitter: str, message: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sql = """
                INSERT INTO conversation (user_id, emitter, message)
                VALUES ( %s, %s, %s)
            """
            await cur.execute(sql, (user_id, emitter, message))
            await conn.commit()


async def get_conversation_history(user_id: int):
    history = [{"role": "system", "content": system_prompt}]
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            sql = """
                SELECT emitter, message
                FROM conversation
                WHERE user_id = %s
                ORDER BY created_at ASC
            """
            await cur.execute(sql, (user_id,))
            rows = await cur.fetchall()
            for row in rows:
                role = "user" if row["emitter"] == "user" else "assistant"
                history.append({"role": role, "content": row["message"]})
    return history


async def reset_conversation(user_id: str):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            sql = """
                DELETE FROM conversation WHERE user_id = %s
            """
            await cur.execute(sql, (user_id,))
            await conn.commit()


@router.post("/chatbot/send_message")
async def send_message_endpoint(request: Message):
    response = await send_message_to_chatgpt(
        request.user_id, request.message, request.feelings, request.comment
    )
    return {"response": response, "user_id": request.user_id}


@router.get("/chatbot/reset_conversation/{user_id}")
async def reset_conversation_endpoint(user_id: str):
    await reset_conversation(user_id)
    return {"status": "Conversation reset"}
