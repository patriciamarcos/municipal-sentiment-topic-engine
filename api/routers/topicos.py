from fastapi import APIRouter, Query
from typing import Optional
from api.database import get_connection

router = APIRouter(prefix="/topicos", tags=["Tópicos"])

@router.get("/")
def get_topicos():
    """Lista de todos os tópicos com keywords e número de documentos."""
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ta.Topic_ID,
               COUNT(*) as Total,
               MAX(ta.Topic_Keywords) as Keywords
        FROM [dbo].[TopicAssignment] ta
        WHERE ta.Topic_ID != -1
        GROUP BY ta.Topic_ID
        ORDER BY Total DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "topico_id": r[0],
            "total_documentos": r[1],
            "keywords": r[2].split(", ") if r[2] else [],
        }
        for r in rows
    ]


@router.get("/{topico_id}/posts")
def get_posts_por_topico(
    topico_id: int,
    limite: int = Query(10, description="Número máximo de posts a retornar"),
    fonte: Optional[str] = Query(None),
):
    """Posts associados a um tópico específico."""
    conn   = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT TOP (?)
            p.Original_External_ID,
            p.Title,
            p.CreatedAt,
            sn.SNetwork_Name,
            sa.Sentiment_Label,
            sa.Sentiment_Score,
            ea.Dominant_Emotion,
            ta.Topic_Probability
        FROM [dbo].[TopicAssignment] ta
        JOIN [dbo].[TextDocument] td ON ta.TextDocument_ID = td.TextDocument_ID
        JOIN [dbo].[Post] p ON td.Post_ID = p.Post_ID
        JOIN [dbo].[SocialNetwork] sn ON p.SNetwork_ID = sn.SNetwork_ID
        LEFT JOIN [dbo].[SentimentAnalysis] sa ON td.TextDocument_ID = sa.TextDocument_ID
        LEFT JOIN [dbo].[EmotionAnalysis] ea ON td.TextDocument_ID = ea.TextDocument_ID
        WHERE ta.Topic_ID = ?
    """
    params = [limite, topico_id]

    if fonte:
        from api.database import FONTE_MAP
        query += " AND LOWER(sn.SNetwork_Name) = ?"
        params.append(FONTE_MAP.get(fonte.lower(), fonte.lower()))

    query += " ORDER BY ta.Topic_Probability DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "platform_id": r[0],
            "titulo": r[1],
            "data": str(r[2]) if r[2] else None,
            "fonte": r[3],
            "sentimento": r[4],
            "sentiment_score": round(r[5], 4) if r[5] else None,
            "emocao": r[6],
            "probabilidade_topico": round(r[7], 4) if r[7] else None,
        }
        for r in rows
    ]


@router.get("/sentimento")
def get_sentimento_por_topico():
    """Distribuição de sentimentos por tópico."""
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ta.Topic_ID, sa.Sentiment_Label, COUNT(*) as Total
        FROM [dbo].[SentimentAnalysis] sa
        JOIN [dbo].[TextDocument] td ON sa.TextDocument_ID = td.TextDocument_ID
        JOIN [dbo].[TopicAssignment] ta ON td.TextDocument_ID = ta.TextDocument_ID
        WHERE ta.Topic_ID != -1
        GROUP BY ta.Topic_ID, sa.Sentiment_Label
        ORDER BY ta.Topic_ID, Total DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    result = {}
    for topic_id, sentimento, total in rows:
        if topic_id not in result:
            result[topic_id] = []
        result[topic_id].append({"sentimento": sentimento, "total": total})

    return result
