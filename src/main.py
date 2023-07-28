from fastapi import FastAPI, APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.client.models import client, message

app = FastAPI(
    title='Alfa test'
)


@app.get("/clients")
async def get_clients(session: AsyncSession = Depends(get_async_session)):
    query = select(client)
    clients = await session.execute(query)
    result = [dict(r._mapping) for r in clients]
    return result


@app.get("/messages")
async def get_messages(session: AsyncSession = Depends(get_async_session)):
    query = select(message)
    messages= await session.execute(query)
    result = [dict(r._mapping) for r in messages]
    return result
