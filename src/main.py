from datetime import datetime, timedelta
from asyncio import sleep
from io import BytesIO

import openpyxl
import pandas as pd
from celery import Celery
import requests
import uvicorn
from fastapi import FastAPI, Depends, UploadFile, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import REDIS_HOST, REDIS_PORT
from schemas import Client
from database import get_async_session
from models import client, message
# from tasks import generate_table
from src.config import AUTH_TOKEN, WEBHOOK_URL, TEST_NUMBER
from src.schemas import Client, Message
from src.database import get_async_session
from src.models import client, message

from viberbot import Api
from viberbot.api.bot_configuration import BotConfiguration
from viberbot.api.messages import (
        TextMessage,
        ContactMessage,
)
from viberbot.api.messages.data_types.contact import Contact


viber = Api(BotConfiguration(
    name='Alfa-Viber',
    avatar='http://viber.com/avatar.jpg',
    auth_token=AUTH_TOKEN
))
# webhook_url = "https://2474-46-216-154-9.ngrok-free.app"
# viber.set_webhook(webhook_url)

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
            text_message = sheet[row + 1][1].value
            try:
                client = Client(phone_number=phone_number)
                clients.append(client)
            except Exception:
                print(f"In row {row} -Invalid number ({phone_number})")

            if text_message:
                messages.append(text_message)
        # await send_viber_sms(Client(phone_number='+375445781372'), Message(text='test'))
        text_message_request = {"text_message": "text test"}
        contact_message_request = {"name": "TEST viber", "phone_number": TEST_NUMBER}
        response = requests.post(
            "http://localhost:8000/send-viber-sms", json={
                "text_message_request": text_message_request,
                "contact_message_request": contact_message_request
            })
        return clients, messages


@app.post('/send-viber-sms')
async def send_viber_sms(contact_request: Client, text_message_request: Message):
    try:
        text_message = TextMessage(text=text_message_request.text)
        contact = Contact(name='test', phone_number=contact_request.phone_number)
        contact_message = ContactMessage(contact=contact)

        viber.send_messages(messages=[text_message, contact_message], to=contact.phone_number)

        response = {
            "message": "SMS sent successfully",
            "text_message": text_message,
            "recipient_phone_number": contact_request.phone_number
        }

        return response

    except Exception as e:
        return JSONResponse(status_code=422, content={"message": str(e)})


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)