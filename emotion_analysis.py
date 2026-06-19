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

OUTPUT_FILE = "data/emotion/all_emotion.json"

MODEL_NAME = "tabularisai/multilingual-emotion-classification"
MODEL_VERSION = "1.0"

MAX_TEXTS = None

MAX_TOKENS = 400

MIN_CHARS = 5

EMOTION_THRESHOLD = 0.15
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

def build_emotion_text(record):
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

def split_text_into_chunks(text, tokenizer, max_tokens=400):
    tokens = tokenizer.encode(
        text,
        add_special_tokens=False
    )

    chunks = []

    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]

        chunk_text = tokenizer.decode(
            chunk_tokens,
            skip_special_tokens=True
        )

        chunks.append(chunk_text)

    return chunks


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
        current_records = load_json_file(file_path)

        print(file_path)
        print(f"Registos carregados: {len(current_records)}")

        records.extend(current_records)

    print(f"TOTAL DE REGISTOS: {len(records)}")

    # ========================================================
    # RESULTADOS EXISTENTES
    # ========================================================

    existing_results = load_json_file(OUTPUT_FILE)

    processed_ids = get_existing_processed_ids(existing_results)

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
        print(f"A usar {len(new_records)} textos")

    # ========================================================
    # DEVICE
    # ========================================================

    device = 0 if torch.cuda.is_available() else -1

    print(
        f"Dispositivo usado: "
        f"{'cuda' if device == 0 else 'cpu'}"
    )

    # ========================================================
    # MODELO
    # ========================================================

    print("A CARREGAR MODELO DE EMOÇÕES")

    emotion_pipeline = pipeline(
        "text-classification",
        model=MODEL_NAME,
        tokenizer=MODEL_NAME,
        device=device,
        top_k=None,
    )

    tokenizer = emotion_pipeline.tokenizer

    # ========================================================
    # PROCESSAMENTO
    # ========================================================

    print("A ANALISAR EMOÇÕES")

    new_results = []

    emotion_counter = Counter()

    for record in tqdm(new_records):
        record = normalize_platform_id(record)

        text = build_emotion_text(record)

        if len(text.strip()) < MIN_CHARS:
            continue

        chunks = split_text_into_chunks(
            text,
            tokenizer,
            max_tokens=MAX_TOKENS
        )

        # acumulador: label -> lista de scores por chunk
        chunk_scores = {}

        for chunk in chunks:

            try:
                predictions = emotion_pipeline(chunk)[0]

            except Exception as e:
                print(f"\nERRO AO PROCESSAR")
                print(e)
                continue

            for pred in predictions:
                label = pred["label"].upper()
                score = pred["score"]

                if label not in chunk_scores:
                    chunk_scores[label] = []

                chunk_scores[label].append(score)

        if not chunk_scores:
            continue

        # média de scores por emoção entre chunks
        avg_scores = {
            label: sum(scores) / len(scores)
            for label, scores in chunk_scores.items()
        }

        # emoção dominante
        dominant_emotion = max(
            avg_scores,
            key=lambda k: avg_scores[k]
        )

        dominant_confidence = round(
            avg_scores[dominant_emotion], 4
        )

        emotion_counter[dominant_emotion] += 1

        # todos os scores arredondados
        all_scores = {
            label: round(score, 4)
            for label, score in sorted(
                avg_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )
        }

        # emoções ativas acima do threshold
        active_emotions = [
            label
            for label, score in avg_scores.items()
            if score >= EMOTION_THRESHOLD
        ]

        result = {
            "platform_id": record.get("platform_id", ""),
            "source": record.get("source", ""),
            "created_at": record.get("created_at", ""),
            "title": record.get("title", ""),
            "dominant_emotion": dominant_emotion,
            "confidence": dominant_confidence,
            "active_emotions": active_emotions,
            "emotion_scores": all_scores,
            "model_name": MODEL_NAME,
            "model_version": MODEL_VERSION,
        }

        new_results.append(result)

    # ========================================================
    # JUNTAR COM RESULTADOS ANTIGOS
    # ========================================================

    final_results = existing_results + new_results

    # ========================================================
    # GUARDAR
    # ========================================================

    print("A GUARDAR RESULTADOS")

    save_json_file(final_results, OUTPUT_FILE)

    print(f"Resultados guardados em:\n{OUTPUT_FILE}")

    # ========================================================
    # ESTATÍSTICAS
    # ========================================================

    print("\nDISTRIBUIÇÃO DE EMOÇÕES")

    total = sum(emotion_counter.values())

    for emotion, count in emotion_counter.most_common():
        percentage = round((count / total) * 100, 1)
        print(f"{emotion} -> {count} ({percentage}%)")

    # ========================================================
    # EXEMPLOS
    # ========================================================

    print("\nEXEMPLOS")

    for item in new_results[:5]:
        print("\n----------------")
        print(item.get("title", ""))
        print(f"Emoção: {item['dominant_emotion']}")
        print(f"Confiança: {item['confidence']}")
        print(f"Emoções ativas: {', '.join(item['active_emotions'])}")
        print("Scores:")
        for emotion, score in item["emotion_scores"].items():
            print(f"  {emotion}: {score}")

    print("\nANÁLISE DE EMOÇÕES TERMINADA")


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    main()