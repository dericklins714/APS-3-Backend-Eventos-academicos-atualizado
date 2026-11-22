from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from schema.evento_schema import EventoCreate, EventoResponse, EventoUpdate
from service import evento_service

router = APIRouter(prefix="/eventos", tags=["Eventos"])


@router.post("", response_model=EventoResponse, status_code=status.HTTP_201_CREATED)
def cadastrar_evento(dados: EventoCreate, db: Session = Depends(get_db)):
    return evento_service.cadastrar_evento(db, dados)


@router.get("", response_model=list[EventoResponse])
def listar_eventos(db: Session = Depends(get_db)):
    return evento_service.listar_eventos(db)


@router.get("/{evento_id}", response_model=EventoResponse)
def consultar_evento(evento_id: int, db: Session = Depends(get_db)):
    return evento_service.buscar_evento(db, evento_id)


@router.put("/{evento_id}", response_model=EventoResponse)
def atualizar_evento(evento_id: int, dados: EventoUpdate, db: Session = Depends(get_db)):
    return evento_service.atualizar_evento(db, evento_id, dados)


@router.delete("/{evento_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_evento(evento_id: int, db: Session = Depends(get_db)):
    evento_service.excluir_evento(db, evento_id)
