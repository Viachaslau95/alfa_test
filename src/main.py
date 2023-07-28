from fastapi import FastAPI

app = FastAPI(
    title='Trading App'
)


@app.get('/test')
def get_clients():
    return 'Many clients'
