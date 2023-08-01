from datetime import datetime, timedelta
from io import BytesIO

import openpyxl
import pandas as pd
from celery import Celery
from fastapi import FastAPI, Depends, UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import REDIS_HOST, REDIS_PORT
from schemas import Client
from database import get_async_session
from models import client, message
# from tasks import generate_table

app = FastAPI(
    title='Alfa test'
)
celery_app = Celery(
    'tasks',
    broker=f"redis://{REDIS_HOST}:{REDIS_PORT}"
)


@celery_app.task
def generate_table():
    now = datetime.now()
    if now.hour >= 22 or now.hour < 9:
        return

    with get_async_session() as session:
        table_creation(session)


# Delayed start of a task every hour during the week
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        timedelta(hours=1),
        generate_table.s(),
        expires=timedelta(weeks=1)
    )

@app.get("/run-task")
def run_task():
    generate_table.delay()
    return {"message": "Task is scheduled"}

@app.get("/clients")
async def get_clients(session: AsyncSession = Depends(get_async_session)):
    query = select(client)
    clients = await session.execute(query)
    result = [dict(r._mapping) for r in clients]
    return result


@app.get("/messages")
async def get_messages(session: AsyncSession = Depends(get_async_session)):
    query = select(message)
    messages = await session.execute(query)
    result = [dict(r._mapping) for r in messages]
    return result


async def table_creation(session: AsyncSession = None):
    if session is None:
        async with get_async_session() as session:
            print(2)
            query_client = select(client).with_only_columns(client.c.phone)
            clients = await session.execute(query_client)
            data_clients = clients.fetchall()

            query_message = select(message).order_by(message.c.id.desc()).with_only_columns(message.c.text)
            messages = await session.execute(query_message)
            data_messages = messages.fetchall()

            df1 = pd.DataFrame(data_clients)
            df2 = pd.DataFrame(list(data_messages[0]), columns=messages.keys())

            combined_df = pd.concat([df1, df2], axis=1)
            output_file = 'client_message_data.xlsx'
            combined_df.to_excel(output_file, index=False)

        return output_file
    else:

        query_client = select(client).with_only_columns(client.c.phone)
        clients = await session.execute(query_client)
        data_clients = clients.fetchall()

        query_message = select(message).order_by(message.c.id.desc()).with_only_columns(message.c.text)
        messages = await session.execute(query_message)
        data_messages = messages.fetchall()

        df1 = pd.DataFrame(data_clients)
        df2 = pd.DataFrame(list(data_messages[0]), columns=messages.keys())

        combined_df = pd.concat([df1, df2], axis=1)
        output_file = 'client_message_data.xlsx'
        combined_df.to_excel(output_file, index=False)
        return output_file

@app.post("/uploadFile/")
async def create_upload_file(file: UploadFile):
    if file.filename.endswith('.xlsx'):
        data_file = await file.read()
        xlsx = BytesIO(data_file)
        wb = openpyxl.load_workbook(xlsx)
        sheet = wb.active
        clients = list()
        messages = list()

        for row in range(1, sheet.max_row):
            phone_number = sheet[row + 1][0].value
            text_message = sheet[row+1][1].value
            try:
                client = Client(phone_number=phone_number)
                clients.append(client)
            except Exception:
                print(f"In row {row} -Invalid number ({phone_number})")

            if text_message:
                messages.append(text_message)
        return clients, messages
