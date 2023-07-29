import pandas as pd
from fastapi import FastAPI, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.models import client, message

app = FastAPI(
    title='Alfa test'
)


@app.get("/clients")
async def get_clients(session: AsyncSession = Depends(get_async_session)):
    query = select(client)
    clients = await session.execute(query)
    result = [dict(r._mapping)for r in clients]
    return result


@app.get("/messages")
async def get_messages(session: AsyncSession = Depends(get_async_session)):
    query = select(message)
    messages= await session.execute(query)
    result = [dict(r._mapping) for r in messages]
    return result


@app.get("/gen_table")
async def table_creation(session: AsyncSession = Depends(get_async_session)):

    query_client = select(client).with_only_columns(client.c.phone)
    clients = await session.execute(query_client)
    data_clients = clients.fetchall()

    query_message = select(message).order_by(message.c.id.desc()).with_only_columns(message.c.text)
    messages = await session.execute(query_message)
    data_messages = messages.fetchall()

    # print(random.SystemRandom().choice(list(messages)))
    # idx = [r[0] for r in list(clients)]

    df1 = pd.DataFrame(data_clients)
    df2 = pd.DataFrame(list(data_messages[0]), columns=messages.keys())

    combined_df = pd.concat([df1, df2], axis=1)
    output_file = 'client_message_data.xlsx'
    combined_df.to_excel(output_file, index=False)


