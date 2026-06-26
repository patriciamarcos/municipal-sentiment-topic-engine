import os
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from api.auth import USERS, verify_password, create_access_token
from api.routers import sentimentos, emocoes, topicos, entidades, keywords, posts

load_dotenv()

# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Municipal Sentiment API",
    description="API de análise de sentimentos municipais da Covilhã",
    version="1.0.0",
)

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ROUTERS
# ============================================================

app.include_router(sentimentos.router)
app.include_router(emocoes.router)
app.include_router(topicos.router)
app.include_router(entidades.router)
app.include_router(keywords.router)
app.include_router(posts.router)

# ============================================================
# AUTH
# ============================================================

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

# ============================================================
# ROOT
# ============================================================

@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Municipal Sentiment API",
        "docs": "/docs",
        "version": "1.0.0",
    }
