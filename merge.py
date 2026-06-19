import json
from pathlib import Path


# ============================================================
# CONFIGURAÇÃO
# ============================================================

# ficheiros de input
SENTIMENT_FILE   = "data/sentiment/all_sentiment.json"
EMOTION_FILE     = "data/emotion/all_emotion.json"
KEYWORDS_FILES   = [
    "data/keywords/news_keywords.json",
    "data/keywords/reddit_keywords.json",
    "data/keywords/bluesky_keywords.json",
    "data/keywords/youtube_keywords.json",
]
NER_FILE         = "data/ner/all_ner.json"
TOPICS_FILE      = "data/topics/all_topics.json"

# ficheiro de output
OUTPUT_FILE      = "data/merged/all_merged.json"



def normalize_platform_id(source, platform_id):
    if source == "youtube" and platform_id and not platform_id.startswith("http"):
        return f"https://www.youtube.com/watch?v={platform_id}"
    return platform_id
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


def save_json_file(data, path):
    path = Path(path)

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ============================================================
# NORMALIZAÇÃO DE IDs
# ============================================================

# os ficheiros de keywords/ner/topics usam record_id = "source_platform_id"
# os ficheiros de sentiment/emotion usam platform_id diretamente
# esta função extrai o platform_id a partir do record_id

def extract_platform_id(record_id, source):
    prefix = f"{source}_"

    if record_id and record_id.startswith(prefix):
        return record_id[len(prefix):]

    return record_id


# ============================================================
# CONSTRUIR ÍNDICES
# ============================================================

def build_sentiment_index(records):
    index = {}

    for record in records:
        platform_id = record.get("platform_id", "")
        source = record.get("source", "")

        if not platform_id:
            continue

        platform_id = normalize_platform_id(source, platform_id)

        key = f"{source}_{platform_id}"

        index[key] = record

    return index


def build_emotion_index(records):
    index = {}

    for record in records:
        platform_id = record.get("platform_id", "")
        source = record.get("source", "")

        if not platform_id:
            continue

        platform_id = normalize_platform_id(source, platform_id)

        key = f"{source}_{platform_id}"

        index[key] = record

    return index


def build_ner_index(records):
    index = {}

    for record in records:
        record_id = record.get("record_id", "")
        source = record.get("source", "")

        platform_id = extract_platform_id(record_id, source)

        key = f"{source}_{platform_id}"

        index[key] = record

    return index


def build_topics_index(records):
    index = {}

    for record in records:
        record_id = record.get("record_id", "")
        source = record.get("source", "")

        platform_id = extract_platform_id(record_id, source)

        key = f"{source}_{platform_id}"

        index[key] = record

    return index


# ============================================================
# MAIN
# ============================================================

def main():
    print("A CARREGAR DADOS")

    # ========================================================
    # CARREGAR TODOS OS FICHEIROS
    # ========================================================

    sentiment_records = load_json_file(SENTIMENT_FILE)
    print(f"Sentimentos: {len(sentiment_records)}")

    emotion_records = load_json_file(EMOTION_FILE)
    print(f"Emoções: {len(emotion_records)}")

    keywords_records = []
    for path in KEYWORDS_FILES:
        keywords_records.extend(load_json_file(path))
    print(f"Keywords: {len(keywords_records)}")

    ner_records = load_json_file(NER_FILE)
    print(f"NER: {len(ner_records)}")

    topics_records = load_json_file(TOPICS_FILE)
    print(f"Tópicos: {len(topics_records)}")

    # ========================================================
    # CONSTRUIR ÍNDICES
    # ========================================================

    print("\nA CONSTRUIR ÍNDICES")

    sentiment_index = build_sentiment_index(sentiment_records)
    emotion_index   = build_emotion_index(emotion_records)
    ner_index       = build_ner_index(ner_records)
    topics_index    = build_topics_index(topics_records)

    # índice de keywords (pode haver múltiplos ficheiros, mesmo record_id)
    keywords_index = {}
    for record in keywords_records:
        record_id = record.get("record_id", "")
        source    = record.get("source", "")

        platform_id = extract_platform_id(record_id, source)

        key = f"{source}_{platform_id}"

        keywords_index[key] = record

    print(f"Índice sentimentos: {len(sentiment_index)}")
    print(f"Índice emoções:     {len(emotion_index)}")
    print(f"Índice keywords:    {len(keywords_index)}")
    print(f"Índice NER:         {len(ner_index)}")
    print(f"Índice tópicos:     {len(topics_index)}")

    # ========================================================
    # MERGE
    # ========================================================

    # usa sentiment como âncora — tem todos os documentos
    print("\nA FAZER MERGE")

    merged_results = []

    matched_emotion   = 0
    matched_keywords  = 0
    matched_ner       = 0
    matched_topics    = 0

    for sentiment_record in sentiment_records:

        platform_id = sentiment_record.get("platform_id", "")
        source      = sentiment_record.get("source", "")
        key         = f"{source}_{platform_id}"

        # ====================================================
        # SENTIMENTOS
        # ====================================================

        sentiment_data = {
            "sentiment":         sentiment_record.get("sentiment"),
            "sentiment_score":   sentiment_record.get("sentiment_score"),
            "negative":          sentiment_record.get("negative"),
            "neutral":           sentiment_record.get("neutral"),
            "positive":          sentiment_record.get("positive"),
            "comments_polarity": sentiment_record.get("comments_polarity"),
        }

        # ====================================================
        # EMOÇÕES
        # ====================================================

        emotion_record = emotion_index.get(key, {})

        if emotion_record:
            matched_emotion += 1

        emotion_data = {
            "dominant_emotion": emotion_record.get("dominant_emotion"),
            "emotion_confidence": emotion_record.get("confidence"),
            "active_emotions":  emotion_record.get("active_emotions", []),
            "emotion_scores":   emotion_record.get("emotion_scores", {}),
        }

        # ====================================================
        # KEYWORDS
        # ====================================================

        keywords_record = keywords_index.get(key, {})

        if keywords_record:
            matched_keywords += 1

        keywords_data = {
            "keywords": keywords_record.get("keywords", []),
        }

        # ====================================================
        # NER
        # ====================================================

        ner_record = ner_index.get(key, {})

        if ner_record:
            matched_ner += 1

        ner_data = {
            "entities": ner_record.get("entities", []),
        }

        # ====================================================
        # TÓPICOS
        # ====================================================

        topics_record = topics_index.get(key, {})

        if topics_record:
            matched_topics += 1

        topics_data = {
            "topic_id":          topics_record.get("topic_id"),
            "topic_probability": topics_record.get("topic_probability"),
            "topic_keywords":    topics_record.get("topic_keywords", []),
        }

        # ====================================================
        # RESULTADO FINAL
        # ====================================================

        merged = {
            "platform_id": platform_id,
            "source":      source,
            "created_at":  sentiment_record.get("created_at"),
            "title":       sentiment_record.get("title"),

            # análises
            **sentiment_data,
            **emotion_data,
            **keywords_data,
            **ner_data,
            **topics_data,
        }

        merged_results.append(merged)

    # ========================================================
    # GUARDAR
    # ========================================================

    print("\nA GUARDAR RESULTADOS")

    save_json_file(merged_results, OUTPUT_FILE)

    print(f"Resultados guardados em:\n{OUTPUT_FILE}")

    # ========================================================
    # ESTATÍSTICAS
    # ========================================================

    total = len(merged_results)

    print(f"\nTOTAL DE DOCUMENTOS MERGED: {total}")
    print(f"Com emoções:   {matched_emotion} ({round(matched_emotion/total*100, 1)}%)")
    print(f"Com keywords:  {matched_keywords} ({round(matched_keywords/total*100, 1)}%)")
    print(f"Com NER:       {matched_ner} ({round(matched_ner/total*100, 1)}%)")
    print(f"Com tópicos:   {matched_topics} ({round(matched_topics/total*100, 1)}%)")

    # ========================================================
    # EXEMPLOS
    # ========================================================

    print("\nEXEMPLOS")

    for item in merged_results[:3]:
        print("\n----------------")
        print(item.get("title", ""))
        print(f"Sentimento:  {item['sentiment']} (score: {item['sentiment_score']})")
        print(f"Emoção:      {item['dominant_emotion']}")
        print(f"Emoções ativas: {', '.join(item['active_emotions']) if item['active_emotions'] else 'nenhuma'}")
        print(f"Tópico:      {item['topic_id']} — {', '.join(item['topic_keywords'][:3]) if item['topic_keywords'] else 'sem tópico'}")
        print(f"Keywords:    {', '.join(kw['keyword'] for kw in item['keywords'][:3]) if item['keywords'] else 'sem keywords'}")
        print(f"Entidades:   {', '.join(e['text'] for e in item['entities'][:3]) if item['entities'] else 'sem entidades'}")

    print("\nMERGE TERMINADO")


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    main()