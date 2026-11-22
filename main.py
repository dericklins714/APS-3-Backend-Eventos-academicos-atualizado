from contextlib import asynccontextmanager

from fastapi import FastAPI

from controller.evento_controller import router as evento_router
from controller.inscricao_controller import router as inscricao_router
from controller.participante_controller import router as participante_router
from controller.relatorio_controller import router as relatorio_router
from database import criar_tabelas


@asynccontextmanager
async def lifespan(_app: FastAPI):
    criar_tabelas()
    yield


app = FastAPI(
    title="API de Eventos Acadêmicos",
    description=(
        "API RESTful para gerenciamento de eventos, participantes e inscrições, "
        "com persistência em SQLite (SQLAlchemy) e relatórios consolidados."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(evento_router)
app.include_router(participante_router)
app.include_router(inscricao_router)
app.include_router(relatorio_router)


@app.get("/", tags=["Sistema"])
def inicio():
    return {
        "mensagem": "API de Eventos Acadêmicos funcionando!",
        "documentacao": "/docs",
    }
