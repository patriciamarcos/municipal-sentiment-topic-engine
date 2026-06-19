import json
import pyodbc
from pathlib import Path
from datetime import datetime
from db_connection import get_connection

BASE_DIR = Path(__file__).parent.parent
# ============================================================
# CONFIGURAÇÃO
# ============================================================

MERGED_FILE = BASE_DIR / "data/merged/all_merged.json"
RAW_FILES = {
    "news":    BASE_DIR / "data/raw/news_posts.json",
    "reddit":  BASE_DIR / "data/raw/reddit_posts.json",
    "bluesky": BASE_DIR / "data/raw/bluesky_posts.json",
    "youtube": BASE_DIR / "data/raw/youtube_posts.json",
}

# mapeamento de source para SNetwork_ID
# deve corresponder aos IDs inseridos na tabela SocialNetwork
SNETWORK_MAP = {
    "news":     3,  # GoogleNews
    "reddit":   2,  # Reddit
    "bluesky":  1,  # Bluesky
    "youtube":  4,  # YouTube
    "facebook": 5,  # Facebook
}


# ============================================================
# JSON
# ============================================================

def load_json_file(path):
    path = Path(path)

    if not path.exists():
        print(f"AVISO: ficheiro não encontrado -> {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalize_platform_id(source, platform_id):
    if source == "youtube" and platform_id and not platform_id.startswith("http"):
        return f"https://www.youtube.com/watch?v={platform_id}"
    return platform_id


def parse_datetime(value):
    if not value:
        return None

    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue

    return None


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# INSERÇÃO
# ============================================================

def get_or_create_user(cursor, handle, snetwork_id):
    if not handle:
        return None

    cursor.execute(
        "SELECT [User_ID] FROM [dbo].[UserSN] WHERE [Handle] = ? AND [SNetwork_ID] = ?",
        handle, snetwork_id
    )
    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO [dbo].[UserSN] ([Handle], [SNetwork_ID]) OUTPUT INSERTED.[User_ID] VALUES (?, ?)",
        handle, snetwork_id
    )
    return cursor.fetchone()[0]


def insert_post(cursor, record, snetwork_id, user_id):
    platform_id = normalize_platform_id(
        record.get("source", ""),
        record.get("platform_id", "")
    )

    metrics = record.get("metrics", {}) or {}

    cursor.execute("""
        INSERT INTO [dbo].[Post] (
            [Original_External_ID],
            [User_ID],
            [SNetwork_ID],
            [CreatedAt],
            [Title],
            [Content],
            [URL],
            [ViewCount],
            [LikeCount],
            [ReplyCount]
        )
        OUTPUT INSERTED.[Post_ID]
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        platform_id,
        user_id,
        snetwork_id,
        parse_datetime(record.get("created_at")),
        record.get("title", "")[:500] if record.get("title") else None,
        record.get("text", ""),
        record.get("url") or record.get("link"),
        safe_int(metrics.get("views", 0)),
        safe_int(metrics.get("likes", metrics.get("upvotes", 0))),
        safe_int(metrics.get("comments", metrics.get("replies", 0))),
    )

    return cursor.fetchone()[0]


def insert_comment(cursor, comment, post_id, snetwork_id):
    comment_text = (
        comment.get("comment_text")
        or comment.get("text", "")
    )

    author = (
        comment.get("comment_author")
        or comment.get("author", "")
    )

    cursor.execute("""
        INSERT INTO [dbo].[Comment] (
            [Post_ID],
            [Author_Handle],
            [Comment_Text],
            [Likes_Upvotes],
            [CreatedAt]
        )
        OUTPUT INSERTED.[Comment_ID]
        VALUES (?, ?, ?, ?, ?)
    """,
        post_id,
        author or None,
        comment_text,
        safe_int(
            comment.get("likes_upvotes")
            or comment.get("comment_upvotes")
            or comment.get("likes", 0)
        ),
        parse_datetime(comment.get("created_at")),
    )

    return cursor.fetchone()[0]


def insert_text_document(cursor, post_id, snetwork_id, original_text, clean_text, created_at):
    cursor.execute("""
        INSERT INTO [dbo].[TextDocument] (
            [Source_Type],
            [Post_ID],
            [SNetwork_ID],
            [Original_Text],
            [Clean_Text],
            [Municipality],
            [CreatedAt]
        )
        OUTPUT INSERTED.[TextDocument_ID]
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        "POST",
        post_id,
        snetwork_id,
        original_text,
        clean_text,
        "Covilhã",
        parse_datetime(created_at),
    )

    return cursor.fetchone()[0]


def insert_sentiment(cursor, text_document_id, merged):
    cursor.execute("""
        INSERT INTO [dbo].[SentimentAnalysis] (
            [TextDocument_ID],
            [Sentiment_Label],
            [Sentiment_Score],
            [Negative],
            [Neutral],
            [Positive],
            [Comments_Polarity],
            [Model_Name],
            [Model_Version]
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        text_document_id,
        merged.get("sentiment"),
        merged.get("sentiment_score"),
        merged.get("negative"),
        merged.get("neutral"),
        merged.get("positive"),
        merged.get("comments_polarity"),
        "cardiffnlp/twitter-xlm-roberta-base-sentiment",
        "1.0",
    )


def insert_emotion(cursor, text_document_id, merged):
    if not merged.get("dominant_emotion"):
        return

    active_emotions = merged.get("active_emotions", [])
    emotion_scores  = merged.get("emotion_scores", {})

    cursor.execute("""
        INSERT INTO [dbo].[EmotionAnalysis] (
            [TextDocument_ID],
            [Dominant_Emotion],
            [Confidence],
            [Active_Emotions],
            [Emotion_Scores],
            [Model_Name],
            [Model_Version]
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        text_document_id,
        merged.get("dominant_emotion"),
        merged.get("emotion_confidence"),
        ", ".join(active_emotions) if active_emotions else None,
        json.dumps(emotion_scores, ensure_ascii=False) if emotion_scores else None,
        "tabularisai/multilingual-emotion-classification",
        "1.0",
    )


def insert_keywords(cursor, text_document_id, keywords):
    for kw in keywords:
        cursor.execute("""
            INSERT INTO [dbo].[Keyword] (
                [TextDocument_ID],
                [Keyword_Text],
                [Score]
            )
            VALUES (?, ?, ?)
        """,
            text_document_id,
            kw.get("keyword", "")[:500],
            kw.get("score"),
        )


def insert_entities(cursor, text_document_id, entities):
    for entity in entities:
        cursor.execute("""
            INSERT INTO [dbo].[NamedEntity] (
                [TextDocument_ID],
                [Entity_Text],
                [Entity_Label]
            )
            VALUES (?, ?, ?)
        """,
            text_document_id,
            entity.get("text", "")[:500],
            entity.get("label", "MISC"),
        )


def insert_topic(cursor, text_document_id, merged):
    topic_id = merged.get("topic_id")

    if topic_id is None:
        return

    topic_keywords = merged.get("topic_keywords", [])

    # apagar tópico existente para este documento
    cursor.execute("""
        DELETE FROM [dbo].[TopicAssignment]
        WHERE [TextDocument_ID] = ?
    """, text_document_id)

    # inserir tópico atualizado
    cursor.execute("""
        INSERT INTO [dbo].[TopicAssignment] (
            [TextDocument_ID],
            [Topic_ID],
            [Topic_Probability],
            [Topic_Keywords],
            [Model_Version]
        )
        VALUES (?, ?, ?, ?, ?)
    """,
        text_document_id,
        topic_id,
        merged.get("topic_probability"),
        ", ".join(topic_keywords) if topic_keywords else None,
        "1.0",
    )

# ============================================================
# VERIFICAR JÁ INSERIDOS
# ============================================================

def get_existing_platform_ids(cursor):
    cursor.execute(
        "SELECT [Original_External_ID] FROM [dbo].[Post]"
    )
    return {row[0] for row in cursor.fetchall()}


# ============================================================
# MAIN
# ============================================================

def main():
    print("A CARREGAR DADOS")

    merged_records = load_json_file(MERGED_FILE)
    print(f"Registos merged: {len(merged_records)}")

    # índice de raw records por platform_id para obter texto original
    raw_index = {}
    for source, path in RAW_FILES.items():
        records = load_json_file(path)
        for record in records:
            pid = normalize_platform_id(
                source,
                str(record.get("platform_id", ""))
            )
            raw_index[pid] = record

    print(f"Registos raw indexados: {len(raw_index)}")

    # ========================================================
    # LIGAÇÃO
    # ========================================================

    print("\nA LIGAR À BASE DE DADOS")

    conn = get_connection()

    if conn is None:
        print("ERRO: não foi possível ligar à BD.")
        return

    cursor = conn.cursor()

    # ========================================================
    # VERIFICAR JÁ INSERIDOS
    # ========================================================

    existing_ids = get_existing_platform_ids(cursor)
    print(f"Posts já existentes na BD: {len(existing_ids)}")

    # ========================================================
    # INSERÇÃO
    # ========================================================

    print("\nA INSERIR DADOS")

    inserted      = 0
    skipped       = 0
    errors        = 0

    for merged in merged_records:

        platform_id = normalize_platform_id(
            merged.get("source", ""),
            merged.get("platform_id", "")
        )

        # saltar se já existe
        if platform_id in existing_ids:
            skipped += 1
            continue

        source      = merged.get("source", "")
        snetwork_id = SNETWORK_MAP.get(source)

        if not snetwork_id:
            print(f"AVISO: source desconhecido -> {source}")
            errors += 1
            continue

        # raw record para texto original
        raw_record = raw_index.get(platform_id, {})

        try:
            # ================================================
            # USER
            # ================================================
            author  = raw_record.get("author") or None
            user_id = get_or_create_user(cursor, author, snetwork_id)

            # ================================================
            # POST
            # ================================================
            post_id = insert_post(cursor, raw_record or merged, snetwork_id, user_id)

            # ================================================
            # COMENTARIOS
            # ================================================
            comments = raw_record.get("comments", [])
            for comment in comments:
                insert_comment(cursor, comment, post_id, snetwork_id)

            # ================================================
            # TEXT DOCUMENT
            # ================================================
            original_text = raw_record.get("text", "")
            clean_text    = merged.get("title", "") or original_text

            text_document_id = insert_text_document(
                cursor,
                post_id,
                snetwork_id,
                original_text,
                clean_text,
                merged.get("created_at"),
            )

            # ================================================
            # ANÁLISES
            # ================================================
            insert_sentiment(cursor, text_document_id, merged)
            insert_emotion(cursor, text_document_id, merged)
            insert_keywords(cursor, text_document_id, merged.get("keywords", []))
            insert_entities(cursor, text_document_id, merged.get("entities", []))
            insert_topic(cursor, text_document_id, merged)

            conn.commit()

            existing_ids.add(platform_id)
            inserted += 1

            if inserted % 100 == 0:
                print(f"  Inseridos: {inserted}")

        except Exception as e:
            conn.rollback()
            print(f"\nERRO ao inserir {platform_id}:")
            print(e)
            errors += 1
            continue

    # ========================================================
    # ESTATÍSTICAS
    # ========================================================

    print(f"\nINSERÇÃO CONCLUÍDA")
    print(f"Inseridos:  {inserted}")
    print(f"Ignorados:  {skipped}")
    print(f"Erros:      {errors}")

    # ========================================================
    # VALIDAÇÃO
    # ========================================================

    print("\nVALIDAÇÃO")

    cursor.execute("SELECT COUNT(*) FROM [dbo].[Post]")
    print(f"Posts na BD:              {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM [dbo].[Comment]")
    print(f"Comentários na BD:        {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM [dbo].[TextDocument]")
    print(f"TextDocuments na BD:      {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM [dbo].[SentimentAnalysis]")
    print(f"Sentimentos na BD:        {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM [dbo].[EmotionAnalysis]")
    print(f"Emoções na BD:            {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM [dbo].[Keyword]")
    print(f"Keywords na BD:           {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM [dbo].[NamedEntity]")
    print(f"Entidades na BD:          {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM [dbo].[TopicAssignment]")
    print(f"Tópicos na BD:            {cursor.fetchone()[0]}")

    conn.close()

    print("\nDB INSERT TERMINADO")


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    main()