import json
from pathlib import Path
from collections import Counter
from tqdm import tqdm
from transformers import pipeline
import torch


# ============================================================
# CONFIGURAÇÃO
# ============================================================

INPUT_FILES = [
    "data/raw/news_posts.json",
    "data/raw/reddit_posts.json",
    "data/raw/bluesky_posts.json",
    "data/raw/youtube_posts.json",
]

OUTPUT_FILE = "data/sentiment/all_sentiment.json"

MODEL_NAME = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
MODEL_VERSION = "1.0"

MAX_TEXTS = None

MAX_TOKENS = 400


# ============================================================
# JSON
# ============================================================

def load_json_file(path):

    path = Path(path)

    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(data, path):

    path = Path(path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(path, "w", encoding="utf-8") as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )


# ============================================================
# TEXTO FINAL
# ============================================================

def build_sentiment_text(record):

    parts = []

    title = str(
        record.get("title", "")
    ).strip()

    text = str(
        record.get("text", "")
    ).strip()

    if title:
        parts.append(title)

    if text:
        parts.append(text)

    return "\n\n".join(parts)

# ============================================================
# CHUNKS
# ============================================================

def split_text_into_chunks(
    text,
    tokenizer,
    max_tokens=400
):

    tokens = tokenizer.encode(
        text,
        add_special_tokens=False
    )

    chunks = []

    for i in range(
        0,
        len(tokens),
        max_tokens
    ):

        chunk_tokens = tokens[
            i:i + max_tokens
        ]

        chunk_text = tokenizer.decode(
            chunk_tokens,
            skip_special_tokens=True
        )

        chunks.append(chunk_text)

    return chunks


# ============================================================
# LABELS
# ============================================================

LABEL_MAPPING = {
    "negative": "NEGATIVE",
    "neutral": "NEUTRAL",
    "positive": "POSITIVE"
}

# ============================================================
# PROCESSAMENTO INCREMENTAL
# ============================================================

def get_existing_processed_ids(existing_results):
    ids = set()

    for item in existing_results:
        platform_id = item.get("platform_id")
        source = item.get("source", "")

        unique_id = f"{source}_{platform_id}"

        ids.add(unique_id)

    return ids

def normalize_platform_id(record):
    source = record.get("source", "")
    platform_id = record.get("platform_id", "")

    if source == "youtube" and platform_id and not platform_id.startswith("http"):
        record["platform_id"] = f"https://www.youtube.com/watch?v={platform_id}"

    return record
# ============================================================
# MAIN
# ============================================================

def main():

    print("A CARREGAR DADOS")

    records = []

    for file_path in INPUT_FILES:

        current_records = load_json_file(
            file_path
        )

        print(file_path)
        print(
            f"Registos carregados: "
            f"{len(current_records)}"
        )

        records.extend(
            current_records
        )

    print(
        f"TOTAL DE REGISTOS: "
        f"{len(records)}"
    )

    # ========================================================
    # RESULTADOS EXISTENTES
    # ========================================================

    existing_results = load_json_file(OUTPUT_FILE)

    processed_ids = get_existing_processed_ids(
        existing_results
    )

    print(f"Registos já processados: {len(processed_ids)}")

    # ========================================================
    # FILTRAR APENAS NOVOS
    # ========================================================

    new_records = []

    for record in records:

        platform_id = record.get("platform_id")
        source = record.get("source", "")

        unique_id = f"{source}_{platform_id}"

        if unique_id in processed_ids:
            continue

        new_records.append(record)

    print(f"Novos registos encontrados: {len(new_records)}")

    if not new_records:
        print("\nNenhum novo registo para analisar.")
        return

    # ========================================================
    # LIMITADOR
    # ========================================================

    if MAX_TEXTS is not None:

        new_records = new_records[:MAX_TEXTS]

        print(
            f"A usar {len(new_records)} textos"
        )

    # ========================================================
    # DEVICE
    # ========================================================

    device = (
        0
        if torch.cuda.is_available()
        else -1
    )

    print(
        f"Dispositivo usado: "
        f"{'cuda' if device == 0 else 'cpu'}"
    )

    # ========================================================
    # MODELO
    # ========================================================
    print(
        "A CARREGAR MODELO "
        "DE SENTIMENTOS"
    )

    sentiment_pipeline = pipeline(
        "text-classification",
        model=MODEL_NAME,
        tokenizer=MODEL_NAME,
        device=device,
        top_k=None
    )

    tokenizer = sentiment_pipeline.tokenizer

    # ========================================================
    # PROCESSAMENTO
    # ========================================================

    print("A ANALISAR SENTIMENTOS")

    new_results = []

    sentiment_counter = Counter()

    for record in tqdm(new_records):
        record = normalize_platform_id(record)

        text = build_sentiment_text(
            record
        )

        if len(text.strip()) < 5:
            continue

        chunks = split_text_into_chunks(
            text,
            tokenizer,
            max_tokens=MAX_TOKENS
        )

        negative_scores = []
        neutral_scores = []
        positive_scores = []

        for chunk in chunks:

            try:
                prediction = sentiment_pipeline(
                    chunk
                )[0]
                
            except Exception as e:

                print(
                    "\nERRO AO PROCESSAR"
                )
                print(e)

                continue

            scores = {}

            for item in prediction:

                label = LABEL_MAPPING[
                    item["label"]
                ]

                scores[label] = (
                    item["score"]
                )

            negative_scores.append(
                scores["NEGATIVE"]
            )

            neutral_scores.append(
                scores["NEUTRAL"]
            )

            positive_scores.append(
                scores["POSITIVE"]
            )

        if not positive_scores:
            continue

        negative = (
            sum(negative_scores)
            / len(negative_scores)
        )

        neutral = (
            sum(neutral_scores)
            / len(neutral_scores)
        )

        positive = (
            sum(positive_scores)
            / len(positive_scores)
        )

        final_sentiment = max(
            [
                ("NEGATIVE", negative),
                ("NEUTRAL", neutral),
                ("POSITIVE", positive)
            ],
            key=lambda x: x[1]
        )[0]

        sentiment_score = (
            positive - negative
        )

        sentiment_counter[
            final_sentiment
        ] += 1

        comment_sentiments = []
        comments_polarity = None

        if record.get("source") == "reddit":

            comments = record.get(
                "comments",
                []
            )

            for comment in comments:

                comment_text = str(
                    comment.get(
                        "comment_text",
                        ""
                    )
                ).strip()

                if len(comment_text) < 5:
                    continue

                try:

                    prediction = sentiment_pipeline(
                        comment_text
                    )[0]

                except Exception:
                    continue

                scores = {}

                for item in prediction:

                    label = LABEL_MAPPING[
                        item["label"]
                    ]

                    scores[label] = (
                        item["score"]
                    )

                polarity = (
                    scores["POSITIVE"]
                    -
                    scores["NEGATIVE"]
                )

                comment_sentiments.append({

                    "author":
                        comment.get(
                            "comment_author",
                            ""
                        ),

                    "negative":
                        round(
                            scores["NEGATIVE"],
                            4
                        ),

                    "neutral":
                        round(
                            scores["NEUTRAL"],
                            4
                        ),

                    "positive":
                        round(
                            scores["POSITIVE"],
                            4
                        ),

                    "polarity":
                        round(
                            polarity,
                            4
                        )

                })

            if comment_sentiments:

                comments_polarity = round(

                    sum(
                        item["polarity"]
                        for item in comment_sentiments
                    )
                    /
                    len(comment_sentiments),

                    4
                )

        result = {

            "platform_id":
                record.get(
                    "platform_id",
                    ""
                ),

            "source":
                record.get(
                    "source",
                    ""
                ),

            "created_at":
                record.get(
                    "created_at",
                    ""
                ),

            "title":
                record.get(
                    "title",
                    ""
                ),

            "sentiment":
                final_sentiment,

            "negative":
                round(
                    negative,
                    4
                ),

            "neutral":
                round(
                    neutral,
                    4
                ),

            "positive":
                round(
                    positive,
                    4
                ),

            "sentiment_score":
                round(
                    sentiment_score,
                    4
                ),
            
            "comments_polarity":
                comments_polarity,

            "comments_sentiment":
                comment_sentiments,

            "model_name":
                MODEL_NAME,

            "model_version":
                MODEL_VERSION,
        }

        new_results.append(
            result
        )

    # ========================================================
    # JUNTAR COM RESULTADOS ANTIGOS
    # ========================================================

    final_results = existing_results + new_results

    # ========================================================
    # GUARDAR
    # ========================================================
    print(
        "A GUARDAR RESULTADOS"
    )

    save_json_file(
        final_results,
        OUTPUT_FILE
    )

    print(
        f"Resultados guardados em:\n"
        f"{OUTPUT_FILE}"
    )

    # ========================================================
    # ESTATÍSTICAS
    # ========================================================

    print("\n")
    print(
        "DISTRIBUIÇÃO "
        "DE SENTIMENTOS"
    )

    total = sum(sentiment_counter.values())

    for sentiment, count in (
        sentiment_counter.most_common()
    ):
        percentage = round(
            (count / total) * 100, 1
        )

        print(
            f"{sentiment} -> {count} ({percentage}%)"
        )

    # ========================================================
    # EXEMPLOS
    # ========================================================

    print("\nEXEMPLOS")

    for item in new_results[:5]:
        print(
            item.get(
                "title",
                ""
            )
        )

        print(
            f"Sentimento: "
            f"{item['sentiment']}"
        )

        print(
            f"Score: "
            f"{item['sentiment_score']}"
        )

    print("\nANÁLISE DE SENTIMENTOS TERMINADA")


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    main()