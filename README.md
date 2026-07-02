# Motor de Inteligência de Sentimento e Extração de Tópicos

> Sistema automático de monitorização da opinião pública municipal da Covilhã, desenvolvido no âmbito da Licenciatura em Inteligência Artificial e Ciência de Dados da Universidade da Beira Interior.

---

Este sistema recolhe automaticamente publicações de redes sociais e notícias locais sobre a Covilhã, e analisa-as usando técnicas de Processamento de Linguagem Natural (PLN) para responder a perguntas como:

- O que estão os cidadãos a dizer sobre o município?
- Qual é o sentimento geral — positivo, negativo ou neutro?
- Que emoções predominam no discurso público?
- Quais são os temas mais falados?
- Quem e o quê são mais mencionados?

Os resultados são disponibilizados através de uma API REST e visualizados num dashboard interativo.

---

## Fontes de dados

| Plataforma | Tipo de conteúdo |
|------------|-----------------|
| Google News | Notícias locais via RSS |
| Reddit | Posts e comentários |
| Bluesky | Posts |
| YouTube | Vídeos e comentários |
| Facebook | Em desenvolvimento |

---

## Como funciona?

O sistema está organizado num pipeline automático com cinco etapas:

```
Recolha → Limpeza → Análise → Armazenamento → Disponibilização
```

### 1. Recolha automática
Crawlers e APIs recolhem dados duas vezes por dia (8h e 20h UTC) e guardam-nos no Cloudflare R2.

### 2. Limpeza e pré-processamento
O texto é normalizado, removendo ruído como URLs, menções e caracteres especiais, preservando as características linguísticas necessárias para a análise.

### 3. Análise com PLN
Cada documento é analisado em cinco dimensões em paralelo:

| Análise | Modelo | Output |
|---------|--------|--------|
| Sentimentos | XLM-RoBERTa (CardiffNLP) | Positivo / Negativo / Neutro |
| Emoções | XLM-RoBERTa (Tabularisai) | 11 categorias emocionais |
| Keywords | KeyBERT | Expressões mais relevantes |
| Entidades | XLM-RoBERTa (Davlan) | Pessoas, organizações, locais |
| Tópicos | BERTopic | 20 temas recorrentes |

### 4. Armazenamento
Os resultados são guardados numa base de dados SQL Server alojada num servidor.

### 5. Disponibilização via API
Uma API REST desenvolvida em FastAPI expõe os dados ao dashboard de visualização.

---

## Estrutura do repositório

```
analysis/          Módulos de análise (sentimentos, emoções, keywords, NER, BERTopic)
api/               API REST em FastAPI
database/          Script de inserção na base de dados
data/              Outputs das análises (gerados automaticamente)
sql/               Schema da base de dados
testes/            Scripts de validação e testes de ligação
pipeline.py        Orquestra todas as análises em sequência
merge.py           Cruza os outputs de todas as análises
grafico.py         Gera visualização UMAP dos tópicos
```

---

## Automação

Todo o pipeline corre automaticamente sem intervenção manual:

| Componente | Frequência | Plataforma |
|------------|-----------|------------|
| Extração de dados | 2× por dia | GitHub Actions |
| Análise e processamento | Após cada extração | GitHub Actions |
| Retreino do BERTopic | Semanalmente | GitHub Actions |
| Inserção na base de dados | 2× por dia (12h e 00h) | Servidor |

---

## API REST

A API expõe os dados em tempo real através dos seguintes grupos de endpoints:

- **`/sentimentos`** — distribuição e evolução temporal do sentimento
- **`/emocoes`** — distribuição de emoções dominantes e ativas
- **`/topicos`** — tópicos identificados e posts associados
- **`/entidades`** — entidades mais frequentes por tipo
- **`/keywords`** — keywords mais relevantes por tópico
- **`/posts`** — lista de posts com filtros múltiplos

A documentação interativa está disponível em `/docs`.

---

## Tecnologias

![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![SQL Server](https://img.shields.io/badge/SQL_Server-CC2927?style=flat&logo=microsoft-sql-server&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=flat&logo=github-actions&logoColor=white)
![Cloudflare](https://img.shields.io/badge/Cloudflare_R2-F38020?style=flat&logo=cloudflare&logoColor=white)

---

## Repositório relacionado

A extração de dados é feita num repositório partilhado, que alimenta este projeto e um Agente de Gestão de Incidentes:

👉 [extracao-dados-covilha](https://github.com/carolinarraposo/extracao-dados-covilha)

---

## Autora

**Patrícia Marcos** — Licenciatura em Inteligência Artificial e Ciência de Dados

---

*Projeto desenvolvido no âmbito da unidade curricular de Projeto, 2025/2026.*
