from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from errors import DomainError
from routers import router

app = FastAPI(title='WorldOfCodes — Assignment 7', version='7.0.0', description='JWT authentication and profile ownership. PostgreSQL, SQLAlchemy, Alembic. Backend only.')


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    headers = {'WWW-Authenticate': 'Bearer'} if exc.status_code == 401 else None
    return JSONResponse(status_code=exc.status_code,
                        content={'error': {'code': exc.code, 'message': exc.message}}, headers=headers)


app.include_router(router)
