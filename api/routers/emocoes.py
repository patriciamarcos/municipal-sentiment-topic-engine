from fastapi import APIRouter, Query
from typing import Optional
from api.database import get_connection

router = APIRouter(prefix="/emocoes", tags=["Emoções"])

@router.get("/distribuicao")
def get_distribuicao(
    fonte: Optional[str] = Query(None),
    data_inicio: Optional[str] = Query(None),
    data_fim: Optional[str] = Query(None),
):
    """Distribuição de emoções dominantes."""
    conn   = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT ea.Dominant_Emotion, COUNT(*) as Total
        FROM [dbo].[EmotionAnalysis] ea
        JOIN [dbo].[TextDocument] td ON ea.TextDocument_ID = td.TextDocument_ID
        JOIN [dbo].[Post] p ON td.Post_ID = p.Post_ID
        JOIN [dbo].[SocialNetwork] sn ON p.SNetwork_ID = sn.SNetwork_ID
        WHERE 1=1
    """
    params = []

    if fonte:
        from api.database import FONTE_MAP
        query += " AND LOWER(sn.SNetwork_Name) = ?"
        params.append(FONTE_MAP.get(fonte.lower(), fonte.lower()))
    if data_inicio:
        query += " AND p.CreatedAt >= ?"
        params.append(data_inicio)
    if data_fim:
        query += " AND p.CreatedAt <= ?"
        params.append(data_fim)

    query += " GROUP BY ea.Dominant_Emotion ORDER BY Total DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    total = sum(r[1] for r in rows)
    return [
        {
            "emocao": r[0],
            "total": r[1],
            "percentagem": round(r[1] / total * 100, 1) if total > 0 else 0,
        }
        for r in rows
    ]


@router.get("/ativas")
def get_emocoes_ativas(
    fonte: Optional[str] = Query(None),
    excluir_neutral: bool = Query(True, description="Excluir NEUTRAL das emoções ativas"),
):
    """Distribuição de emoções ativas (incluindo secundárias)."""
    conn   = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT value as Emocao, COUNT(*) as Total
        FROM [dbo].[EmotionAnalysis] ea
        JOIN [dbo].[TextDocument] td ON ea.TextDocument_ID = td.TextDocument_ID
        JOIN [dbo].[Post] p ON td.Post_ID = p.Post_ID
        JOIN [dbo].[SocialNetwork] sn ON p.SNetwork_ID = sn.SNetwork_ID
        CROSS APPLY STRING_SPLIT(ea.Active_Emotions, ',')
        WHERE LTRIM(RTRIM(value)) != ''
    """
    params = []

    if excluir_neutral:
        query += " AND LTRIM(RTRIM(value)) != 'NEUTRAL'"
    if fonte:
        from api.database import FONTE_MAP
        query += " AND LOWER(sn.SNetwork_Name) = ?"
        params.append(FONTE_MAP.get(fonte.lower(), fonte.lower()))

    query += " GROUP BY value ORDER BY Total DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [{"emocao": r[0].strip(), "total": r[1]} for r in rows]


@router.get("/por-topico")
def get_emocoes_por_topico():
    """Distribuição de emoções dominantes por tópico."""
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ta.Topic_ID, ea.Dominant_Emotion, COUNT(*) as Total
        FROM [dbo].[EmotionAnalysis] ea
        JOIN [dbo].[TextDocument] td ON ea.TextDocument_ID = td.TextDocument_ID
        JOIN [dbo].[TopicAssignment] ta ON td.TextDocument_ID = ta.TextDocument_ID
        WHERE ta.Topic_ID != -1
        GROUP BY ta.Topic_ID, ea.Dominant_Emotion
        ORDER BY ta.Topic_ID, Total DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    result = {}
    for topic_id, emocao, total in rows:
        if topic_id not in result:
            result[topic_id] = []
        result[topic_id].append({"emocao": emocao, "total": total})

    return result
