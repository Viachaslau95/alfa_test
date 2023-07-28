from sqlalchemy import MetaData, Integer, String,  Table, Column

metadata = MetaData()

client = Table(
    "client",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("phone", String, nullable=False),
    Column("firstname", String, nullable=False),
    Column("lastname", String, nullable=False),
)

message = Table(
    "message",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("text", String, nullable=False, default='default message')
)


