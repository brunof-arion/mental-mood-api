# chatbot.py

import os
import random
import httpx
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from typing import Optional

# Definir el router
router = APIRouter()

# Modelo para representar un mensaje
class Message(BaseModel):
    message: str
    feelings: Optional['Feelings'] = None
    comment: Optional[str] = None

class Feelings(BaseModel):
    work: int
    health: int
    relations: int
    finance: int
    description: str

# Prompt del sistema
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
Cuando lo consideres oportuno, plantea una meta al usuario y pide que lo evalúe.
Esa meta debe contener items como para agregar a una to do list.
El formato de las respuestas debe ser un objeto JSON con el siguiente formato:
{
  "message": "Mensaje de respuesta del asistente",
  "list": {
    "title": "Título de la lista",
    "list": ["Item 1", "Item 2", "Item 3", ...]
  }
}
list viene con contenido solo si se está proponiendo una lista de tareas.
Recuerda adaptar tu lenguaje y estilo de comunicación al del usuario para crear una experiencia más personalizada y efectiva.
"""

# Historial de la conversación
conversation_history = [
    {"role": "system", "content": system_prompt}
]

# Función para enviar mensajes a ChatGPT
async def send_message_to_chatgpt(message: str, feelings: Feelings = None, comment: str = None) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    api_url = "https://api.openai.com/v1/chat/completions"

    if not api_key:
        raise HTTPException(status_code=500, detail="La clave de API de OpenAI no está configurada.")

    if feelings and len(conversation_history) == 1:
        feelings_message = f"""El usuario ha indicado sus sentimientos en las siguientes áreas:
Trabajo: {feelings.work}/4
Salud: {feelings.health}/4
Relaciones: {feelings.relations}/4
Finanzas: {feelings.finance}/4
Descripción del sentimiento: {comment}
Por favor, ten en cuenta esta información al iniciar la conversación y ofrecer apoyo."""
        conversation_history.append({"role": "user", "content": feelings_message})
    else:
        conversation_history.append({"role": "user", "content": message})

    payload = {
        "model": "gpt-4",
        "messages": conversation_history,
        "temperature": 0.7
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            assistant_response = data["choices"][0]["message"]["content"]
            conversation_history.append({"role": "assistant", "content": assistant_response})
            return assistant_response
    except httpx.HTTPError as exc:
        print(f"Error al enviar mensaje a ChatGPT: {exc}")
        mock_responses = [
            "Lo siento, estoy teniendo problemas para procesar tu solicitud en este momento. ¿Podrías intentarlo de nuevo más tarde?",
            "Parece que hay un problema de conexión. Mientras tanto, ¿puedo ayudarte con algo más general?",
            "Disculpa, no pude acceder a la información que necesitas ahora mismo. ¿Hay algo más en lo que pueda asistirte?",
            "Estoy experimentando dificultades técnicas. ¿Te importaría reformular tu pregunta de otra manera?",
            "Ups, algo salió mal por mi lado. ¿Podrías darme un poco más de contexto sobre tu pregunta mientras intento resolverlo?"
        ]
        random_response = random.choice(mock_responses)
        conversation_history.append({"role": "assistant", "content": random_response})
        return random_response

# Función para reiniciar la conversación
def reset_conversation():
    conversation_history.clear()
    conversation_history.append({"role": "system", "content": system_prompt})

# Endpoint para enviar un mensaje
@router.post("/chatbot/send_message")
async def send_message_endpoint(request: Message):
    response = await send_message_to_chatgpt(
        request.message, request.feelings, request.comment
    )
    return {"response": response}

# Endpoint para reiniciar la conversación
@router.post("/chatbot/reset_conversation")
def reset_conversation_endpoint():
    reset_conversation()
    return {"status": "Conversación reiniciada"}
