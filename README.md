# API RESTful de Eventos Acadêmicos (APS 3)

Evolução da API da APS 2. Agora os dados são **persistidos em SQLite** com **SQLAlchemy ORM** e a API disponibiliza **relatórios consolidados** sobre eventos, categorias e cursos.

## Funcionalidades

- CRUD de eventos e de participantes;
- Inscrição de participantes em eventos e consulta dos inscritos;
- Persistência permanente em SQLite (os dados sobrevivem à reinicialização);
- Validação com Pydantic e tratamento de erros com códigos HTTP apropriados;
- Controle de capacidade, e-mail único e inscrições sem duplicidade (validado na aplicação **e** no banco);
- Três relatórios consolidados calculados dinamicamente com SQLAlchemy;
- Documentação e testes pelo Swagger (`/docs`) e testes automatizados com pytest.

## Estrutura do projeto

```text
api_eventos_fastapi/
├── main.py                  # Criação do app, rotas e criação das tabelas
├── database.py              # Engine, sessões, Base e dependência get_db
├── eventos.db               # Banco SQLite (gerado automaticamente na 1ª execução)
├── requirements.txt
├── README.md
│
├── controller/              # Rotas HTTP
│   ├── evento_controller.py
│   ├── participante_controller.py
│   ├── inscricao_controller.py
│   └── relatorio_controller.py
│
├── model/                   # Entidades SQLAlchemy e relacionamentos
│   ├── evento.py
│   ├── participante.py
│   └── inscricao.py
│
├── schema/                  # Validação/respostas com Pydantic
│   ├── evento_schema.py
│   ├── participante_schema.py
│   ├── inscricao_schema.py
│   └── relatorio_schema.py
│
├── service/                 # Regras de negócio, persistência e consultas
│   ├── evento_service.py
│   ├── participante_service.py
│   ├── inscricao_service.py
│   ├── relatorio_service.py
│   └── utils.py             # commit com tratamento de falhas do banco
│
└── tests/
    └── test_api.py
```

## Instalação

### Windows

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Linux/macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Execução

Na pasta do projeto:

```bash
uvicorn main:app --reload
```

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Configuração do banco de dados

- Banco: **SQLite**, arquivo `eventos.db` na **raiz do projeto** (mesma pasta de `main.py`). Ele é criado automaticamente na primeira execução; para "zerar" os dados basta apagar o arquivo com a aplicação parada.
- `database.py` concentra: criação do `engine`, `SessionLocal`, a classe `Base`, a função `criar_tabelas()` (chamada na inicialização do app) e a dependência `get_db()`, que abre uma sessão por requisição e a **fecha ao final**.
- As chaves estrangeiras do SQLite são ativadas via `PRAGMA foreign_keys=ON`.
- Não foi utilizada ferramenta de migração (Alembic), conforme permitido.

### Entidades e relacionamentos

| Tabela | Campos principais |
|---|---|
| `eventos` | id, titulo, descricao, data, horario, local, capacidade, categoria |
| `participantes` | id, nome, email (**UNIQUE**), curso |
| `inscricoes` | id, evento_id (FK), participante_id (FK), data_inscricao, **UNIQUE(evento_id, participante_id)** |

- `Evento` 1—N `Inscricao` e `Participante` 1—N `Inscricao` (`relationship` com `back_populates`).
- Inscrição duplicada é impedida pela regra no service **e** pela `UniqueConstraint`.

### Comportamento de exclusão (sem registros órfãos)

Ao excluir um **evento** ou um **participante**, as **inscrições relacionadas são excluídas em cascata** (`cascade="all, delete-orphan"` + `ON DELETE CASCADE`). Assim, os relatórios permanecem consistentes.

### Tratamento de falhas de persistência

Todo `commit` passa por `service/utils.py`: em erro de integridade é feito `rollback` e retornado `409` com mensagem amigável; em qualquer outra falha do banco, `rollback` e `500` com a mensagem genérica "Erro interno ao acessar o banco de dados." — nenhum detalhe técnico é exposto.

## Principais rotas

### Eventos

| Método | Rota | Função |
|---|---|---|
| POST | `/eventos` | Cadastrar evento |
| GET | `/eventos` | Listar eventos |
| GET | `/eventos/{id}` | Consultar evento |
| PUT | `/eventos/{id}` | Atualizar evento |
| DELETE | `/eventos/{id}` | Excluir evento (e suas inscrições) |

### Participantes

| Método | Rota | Função |
|---|---|---|
| POST | `/participantes` | Cadastrar participante |
| GET | `/participantes` | Listar participantes |
| GET | `/participantes/{id}` | Consultar participante |
| PUT | `/participantes/{id}` | Atualizar participante |
| DELETE | `/participantes/{id}` | Excluir participante (e suas inscrições) |

### Inscrições

| Método | Rota | Função |
|---|---|---|
| POST | `/eventos/{evento_id}/inscricoes/{participante_id}` | Realizar inscrição |
| GET | `/eventos/{evento_id}/inscricoes` | Listar participantes inscritos |

Ordem das verificações na inscrição: evento existe → participante existe → inscrição duplicada → vagas disponíveis.

### Relatórios

| Método | Rota | Função |
|---|---|---|
| GET | `/relatorios/eventos/ocupacao` | Ocupação de cada evento |
| GET | `/relatorios/eventos/categorias` | Consolidado por categoria |
| GET | `/relatorios/participantes/cursos` | Participação por curso |

## Relatórios e informações consolidadas

Todos são calculados na hora com SQLAlchemy (`select`, `join`, `group_by`, `count`, `sum`), sem valores fixos. Se não houver registros, retornam lista vazia (`[]`) com status `200`.

### 1. Ocupação dos eventos — `GET /relatorios/eventos/ocupacao`

Usa `OUTER JOIN` entre eventos e inscrições, então **eventos sem inscrições aparecem** com 0 inscritos. `percentual_ocupacao = inscritos / capacidade × 100` (arredondado em 2 casas, com proteção contra divisão por zero); `vagas_disponiveis = capacidade − inscritos`.

```json
[
  {
    "evento_id": 1,
    "titulo": "Workshop de Python",
    "capacidade": 4,
    "total_inscritos": 3,
    "vagas_disponiveis": 1,
    "percentual_ocupacao": 75.0
  }
]
```

### 2. Eventos por categoria — `GET /relatorios/eventos/categorias`

Agrupa por categoria: total de eventos, soma das capacidades e total de inscrições. As inscrições são contadas por evento em uma subconsulta antes de agrupar, para que a capacidade **não seja multiplicada** pelo JOIN.

```json
[
  { "categoria": "Palestra", "total_eventos": 1, "capacidade_total": 5, "total_inscricoes": 0 },
  { "categoria": "Workshop", "total_eventos": 2, "capacidade_total": 14, "total_inscricoes": 4 }
]
```

### 3. Participação por curso — `GET /relatorios/participantes/cursos`

Agrupa participantes por curso. `total_participantes` usa `COUNT(DISTINCT participante.id)`, evitando contar o mesmo participante várias vezes quando ele tem múltiplas inscrições; `total_inscricoes` conta as inscrições do curso. Cursos sem inscrições aparecem com 0.

```json
[
  { "curso": "ADS", "total_participantes": 2, "total_inscricoes": 3 },
  { "curso": "Direito", "total_participantes": 1, "total_inscricoes": 0 }
]
```

## Exemplos de utilização

Cadastrar evento — `POST /eventos`:

```json
{
  "titulo": "Workshop de Python",
  "descricao": "Introdução ao desenvolvimento com Python e FastAPI.",
  "data": "2026-10-15",
  "horario": "19:00:00",
  "local": "Laboratório 2",
  "capacidade": 30,
  "categoria": "Workshop"
}
```

Cadastrar participante — `POST /participantes`:

```json
{
  "nome": "João da Silva",
  "email": "joao@email.com",
  "curso": "Análise e Desenvolvimento de Sistemas"
}
```

Inscrição — `POST /eventos/1/inscricoes/1` → `201 Created`:

```json
{
  "mensagem": "Inscrição realizada com sucesso.",
  "id": 1,
  "evento_id": 1,
  "participante_id": 1,
  "data_inscricao": "2026-11-22"
}
```

## Erros

| Situação | Código | `detail` |
|---|---|---|
| Evento inexistente | 404 | "Evento não encontrado." |
| Participante inexistente | 404 | "Participante não encontrado." |
| Inscrição duplicada | 409 | "Participante já está inscrito neste evento." |
| Evento sem vagas | 409 | "Não existem vagas disponíveis para este evento." |
| E-mail já cadastrado | 409 | "Já existe um participante cadastrado com este e-mail." |
| Reduzir capacidade abaixo do nº de inscritos | 409 | "A capacidade não pode ser menor que o número de inscritos no evento." |
| Dados inválidos (e-mail, capacidade ≤ 0, categoria etc.) | 422 | Detalhes de validação do Pydantic |
| Falha inesperada no banco | 500 | "Erro interno ao acessar o banco de dados." |

## Códigos HTTP utilizados

`200 OK`, `201 Created`, `204 No Content`, `404 Not Found`, `409 Conflict`, `422 Unprocessable Entity`, `500 Internal Server Error`.

## Arquitetura MVC

- **Model** (`model/`): entidades e relacionamentos SQLAlchemy.
- **Schema** (`schema/`): validação de entrada e formato das respostas (Pydantic).
- **Controller** (`controller/`): apenas rotas HTTP; recebem a requisição e delegam ao service.
- **Service** (`service/`): regras de negócio, persistência e consultas de consolidação.
- **Database** (`database.py`): conexão, sessões e criação das tabelas.

## Como reproduzir os testes

### Testes manuais no Swagger (`/docs`)

1. Criar um evento (`POST /eventos`) e consultá-lo (`GET /eventos/{id}`);
2. Criar um participante e consultá-lo;
3. Atualizar (`PUT`) e excluir (`DELETE`) registros;
4. Inscrever o participante no evento;
5. Repetir a inscrição → `409` (duplicada);
6. Inscrever em evento inexistente (ex.: `/eventos/999/inscricoes/1`) → `404`;
7. Criar evento com capacidade 1, inscrever um participante e tentar um segundo → `409` (sem vagas);
8. **Persistência:** parar o servidor (Ctrl+C), executar `uvicorn main:app --reload` novamente e conferir com `GET /eventos`, `GET /participantes` e `GET /eventos/{id}/inscricoes`;
9. Consultar `/relatorios/eventos/ocupacao`;
10. Consultar `/relatorios/eventos/categorias`;
11. Consultar `/relatorios/participantes/cursos`;
12. Inserir, atualizar e excluir registros (inclusive excluir um participante inscrito) e consultar os relatórios novamente para ver os valores mudarem.

### Testes automatizados

```bash
pytest -v
```

Os testes usam um banco SQLite temporário em memória e **não alteram** o `eventos.db`. Cobrem CRUD, validações, e-mail duplicado, inscrição (duplicada, sem vagas, inexistentes), exclusão em cascata e os três relatórios (inclusive eventos/cursos sem inscrições e listas vazias).
