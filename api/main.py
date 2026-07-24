import os
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from api.auth import USERS, verify_password, create_access_token, require_admin, list_users, create_user, delete_user
from api.routers import sentimentos, emocoes, topicos, entidades, keywords, posts, consultas, exportacoes, regras, notificacoes

load_dotenv()


app = FastAPI(
    title="Municipal Sentiment API",
    description="API de análise de sentimentos municipais da Covilhã",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(sentimentos.router)
app.include_router(emocoes.router)
app.include_router(topicos.router)
app.include_router(entidades.router)
app.include_router(keywords.router)
app.include_router(posts.router)
app.include_router(consultas.router)
app.include_router(exportacoes.router)
app.include_router(regras.router)
app.include_router(notificacoes.router)

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/auth/login", tags=["Autenticação"])
def login(body: LoginRequest):
    """Login — devolve token JWT."""
    user = USERS.get(body.email)
    if not user or not verify_password(body.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou password incorretos.",
        )
    token = create_access_token({"sub": body.email, "role": user["role"]})
    return {"access_token": token, "token_type": "bearer"}


class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: str = "tecnico"

@app.get("/users", tags=["Utilizadores"])
def get_users(user: dict = Depends(require_admin)):
    """Lista todos os utilizadores. Requer autenticação de admin."""
    return list_users()

@app.post("/users", tags=["Utilizadores"])
def add_user(body: CreateUserRequest, user: dict = Depends(require_admin)):
    """Cria um novo utilizador. Requer autenticação de admin."""
    success = create_user(body.email, body.password, body.role)
    if not success:
        raise HTTPException(status_code=400, detail="Utilizador já existe.")
    return {"message": f"Utilizador {body.email} criado com sucesso."}

@app.delete("/users/{email}", tags=["Utilizadores"])
def remove_user(email: str, user: dict = Depends(require_admin)):
    """Remove um utilizador. Requer autenticação de admin."""
    if email == "admin@municipalsentiment.pt":
        raise HTTPException(status_code=400, detail="Não é possível remover o utilizador admin.")
    success = delete_user(email)
    if not success:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado.")
    return {"message": f"Utilizador {email} removido com sucesso."}


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Municipal Sentiment API",
        "docs": "/docs",
        "version": "1.0.0",
    }
