from fastapi import APIRouter, Query
from typing import Optional
from api.database import get_connection

router = APIRouter(prefix="/keywords", tags=["Keywords"])

@router.get("/mais-frequentes")
def get_mais_frequentes(
    limite: int = Query(20),
    fonte: Optional[str] = Query(None),
    topico_id: Optional[int] = Query(None),
):
    """Keywords mais frequentes no corpus."""
    conn   = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT TOP (?) k.Keyword_Text, COUNT(*) as Total
        FROM [dbo].[Keyword] k
        JOIN [dbo].[TextDocument] td ON k.TextDocument_ID = td.TextDocument_ID
        JOIN [dbo].[Post] p ON td.Post_ID = p.Post_ID
        JOIN [dbo].[SocialNetwork] sn ON p.SNetwork_ID = sn.SNetwork_ID
    """
    params = [limite]
    conditions = []

    if fonte:
        from api.database import FONTE_MAP
        query += " AND LOWER(sn.SNetwork_Name) = ?"
        params.append(FONTE_MAP.get(fonte.lower(), fonte.lower()))
    if topico_id is not None:
        query += " JOIN [dbo].[TopicAssignment] ta ON td.TextDocument_ID = ta.TextDocument_ID"
        conditions.append("ta.Topic_ID = ?")
        params.append(topico_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY k.Keyword_Text ORDER BY Total DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [{"keyword": r[0], "total": r[1]} for r in rows]


@router.get("/por-topico")
def get_keywords_por_topico(limite: int = Query(10)):
    """Top keywords por tópico."""
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ta.Topic_ID, k.Keyword_Text, COUNT(*) as Total
        FROM [dbo].[Keyword] k
        JOIN [dbo].[TextDocument] td ON k.TextDocument_ID = td.TextDocument_ID
        JOIN [dbo].[TopicAssignment] ta ON td.TextDocument_ID = ta.TextDocument_ID
        WHERE ta.Topic_ID != -1
        GROUP BY ta.Topic_ID, k.Keyword_Text
        ORDER BY ta.Topic_ID, Total DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    result = {}
    for topic_id, keyword, total in rows:
        if topic_id not in result:
            result[topic_id] = []
        if len(result[topic_id]) < limite:
            result[topic_id].append({"keyword": keyword, "total": total})

    return result
