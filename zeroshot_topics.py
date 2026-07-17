import json
from pathlib import Path
from transformers import pipeline
from tqdm import tqdm

# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────

INPUT_FILES = [
    "data/keywords/news_keywords.json",
    "data/keywords/reddit_keywords.json",
    "data/keywords/bluesky_keywords.json",
    "data/keywords/youtube_keywords.json",
]

OUTPUT_RESULTS = "data/topics/all_topics_zeroshot.json"

MODELO_ZEROSHOT = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

# Limiar mínimo de confiança para aceitar um tópico
# Se o score for abaixo disto, o documento é marcado como baixa confiança
THRESHOLD = 0.30

TOP_N_KEYWORDS = 5

# ─────────────────────────────────────────────
# TÓPICOS DEFINIDOS MANUALMENTE
# ─────────────────────────────────────────────

TOPICOS = [
    "Feira e Festival",
    "Cultura, arte e espetáculos",
    "Turismo e património histórico",
    "Mercado",
    "Ação social e voluntariado",
    "Eleições e política autárquica",
    "Desporto e competições",
    "Incêndios e bombeiros",
    "Saúde e hospital",
    "Obras e infraestruturas",
    "Comércio e lojas",
    "Crimes e polícia",
    "Universidade e vida académica",
    "Natal e festividades",
    "Falecimentos",
    "Tecnologia",
    "Habitação",
    "Transportes",
]

# ─────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────────

def load_json(path):
    path = Path(path)
    if not path.exists():
        print(f"Ficheiro não encontrado: {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def build_document_text(record):
    source = record.get("source", "")
    title = str(record.get("title_clean", "")).strip()
    keywords = record.get("keywords", [])

    keyword_text = ", ".join(
        kw.get("keyword", "")
        for kw in keywords[:TOP_N_KEYWORDS]
        if kw.get("keyword", "").strip()
    )

    if source == "news":
        # Usar título + keywords, ou só título se não houver keywords
        if keyword_text:
            return f"{title}. {keyword_text}".strip()
        else:
            return title.strip()
    else:
        # Para redes sociais usar keywords, ou título se não houver keywords
        if keyword_text:
            return keyword_text.strip()
        elif title:
            return title.strip()
        else:
            return ""


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("ZERO-SHOT TOPIC CLASSIFICATION")

    # Carregar todos os documentos
    records = []
    for file_path in INPUT_FILES:
        current = load_json(file_path)
        print(f"{file_path}: {len(current)} registos")
        records.extend(current)

    print(f"\nTotal de registos: {len(records)}")

    # Carregar resultados já existentes
    existing_results = load_json(OUTPUT_RESULTS)
    processed_ids = {r["record_id"] for r in existing_results}
    print(f"Documentos já classificados: {len(processed_ids)}")

    # Filtrar apenas documentos novos com texto válido
    valid_records = []
    valid_texts = []

    for record in records:
        record_id = record.get("record_id", "")
        if record_id in processed_ids:
            continue
        text = build_document_text(record)
        if len(text) < 10:
            continue
        valid_records.append(record)
        valid_texts.append(text)

    print(f"Documentos novos a classificar: {len(valid_records)}")

    if not valid_records:
        print("\nNenhum documento novo para classificar.")
        return

    # Carregar modelo Zero-Shot
    print(f"\nA carregar modelo: {MODELO_ZEROSHOT}")
    classifier = pipeline(
        "zero-shot-classification",
        model=MODELO_ZEROSHOT,
        device=0
    )

    print(f"\nTópicos definidos ({len(TOPICOS)}):")
    for i, t in enumerate(TOPICOS):
        print(f"  {i}: {t}")

    print(f"\nLimiar de confiança: {THRESHOLD}")
    print("\nA classificar documentos...\n")

    new_results = []

    for record, text in tqdm(zip(valid_records, valid_texts), total=len(valid_records)):
        try:
            output = classifier(
                text,
                candidate_labels=TOPICOS,
                multi_label=False
            )

            best_topic = output["labels"][0]
            best_score = output["scores"][0]
            topic_id = TOPICOS.index(best_topic)

            all_scores = {
                label: round(score, 4)
                for label, score in zip(output["labels"], output["scores"])
            }

            result = {
                "record_id": record.get("record_id", ""),
                "source": record.get("source", ""),
                "created_at": record.get("created_at", ""),
                "title_clean": record.get("title_clean", ""),
                "topic_id": topic_id,
                "topic_label": best_topic,
                "topic_probability": round(best_score, 4),
                "low_confidence": best_score < THRESHOLD,
                "all_scores": all_scores,
            }

        except Exception as e:
            print(f"\nErro no registo {record.get('record_id', '')}: {e}")
            result = {
                "record_id": record.get("record_id", ""),
                "source": record.get("source", ""),
                "created_at": record.get("created_at", ""),
                "title_clean": record.get("title_clean", ""),
                "topic_id": -1,
                "topic_label": "Erro",
                "topic_probability": 0.0,
                "low_confidence": True,
                "all_scores": {},
            }

        new_results.append(result)

    # Juntar resultados existentes com os novos
    final_results = existing_results + new_results
    save_json(final_results, OUTPUT_RESULTS)
    print(f"\nResultados guardados em: {OUTPUT_RESULTS}")

    # Estatísticas finais
    print("\n")
    print("DISTRIBUIÇÃO POR TÓPICO")

    from collections import Counter
    topic_counter = Counter(r["topic_label"] for r in final_results)
    low_confidence_count = sum(1 for r in new_results if r["low_confidence"])

    for topic, count in topic_counter.most_common():
        print(f"  {topic}: {count} docs")

    print(f"\nDocumentos novos com baixa confiança (< {THRESHOLD}): {low_confidence_count}")
    print(f"Total no ficheiro: {len(final_results)}")


if __name__ == "__main__":
    main()