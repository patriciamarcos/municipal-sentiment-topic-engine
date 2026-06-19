import json
from pathlib import Path
from collections import Counter
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer
from bertopic.representation import KeyBERTInspired


# ============================================================
# CONFIGURAÇÃO
# ============================================================

INPUT_FILES = [
    "data/keywords/news_keywords.json",
    "data/keywords/reddit_keywords.json",
    "data/keywords/bluesky_keywords.json",
    "data/keywords/youtube_keywords.json",
]

OUTPUT_RESULTS = "data/topics/all_topics.json"
TOPIC_INFO_OUTPUT = "data/topics/topic_info.json"
MODEL_OUTPUT_DIR = "models/bertopic_model/"
MODELO_EMBEDDINGS = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
MAX_TEXTS = None
MIN_TOPIC_SIZE = 10
NR_TOP_WORDS = 10
TOP_N_KEYWORDS_FROM_RECORD = 5


STOPWORDS_PT = [
    "a", "o", "as", "os",
    "um", "uma", "uns", "umas",
    "de", "do", "da", "dos", "das",
    "em", "no", "na", "nos", "nas",
    "por", "para", "com", "sem",
    "sobre", "entre",
    "e", "ou", "mas", "que", "se",
    "como", "ao", "aos", "à", "às",
    "foi", "foram", "ser", "ter",
    "tem", "teve", "vai", "irá",
    "está", "estão", "será", "serão",
    "este", "esta", "estes", "estas",
    "esse", "essa", "isso",
    "title", "text", "alguém", "alguem", 
    "olá", "ola", "boa", "tarde", 
    "lá", "la", "disse",
    "aquele", "aquela", "também", "ainda", "já",
    "mais", "muito", "num", "numa",
    "neste", "nesta", "durante", "segundo",
    "onde", "quando", "após",
    "dia", "dias", "ano", "anos",
    "maio", "junho", "abril",
    "janeiro", "fevereiro",
    "março", "julho",
    "agosto", "setembro",
    "outubro", "novembro", "dezembro",
    "pelo", "pela", "pelos", "pelas",
    "lhe", "lhes", "seu", "sua", "seus", "suas",
    "mesmo", "mesma",
    "forma", "âmbito",
    "nota", "imprensa", "comunicado",
    "afirmou", "referiu", "explicou", "adiantou", "adianta",

    # ruído municipal/jornalístico
    "covilhã", "covilha", "notícias", "noticias", "município", "câmara",
]

# ============================================================
# JSON
# ============================================================
def load_json_file(path):
    path = Path(path)

    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json_file(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


# ============================================================
# FILTRAR KEYWORDS RUINS
# ============================================================

def filter_keywords(keywords):

    filtered = []

    for kw in keywords:

        keyword = kw.get("keyword", "").strip()

        if not keyword:
            continue

        # remover keywords demasiado curtas
        if len(keyword) <= 2:
            continue

        # remover keywords com números
        if any(char.isdigit() for char in keyword):
            continue

        # remover nomes próprios simples
        words = keyword.split()

        if len(words) == 1 and words[0][0].isupper():
            continue

        filtered.append(keyword)

    return filtered

# ============================================================
# TEXTO FINAL PARA BERTopic
# ============================================================

def build_document_text(record):

    source = record.get("source", "")

    title = str(record.get("title_clean", "")).strip()

    clean_text = str(record.get("clean_text", "")).strip()

    keywords = record.get("keywords", [])

    filtered_keywords = filter_keywords(keywords)

    keyword_text = ", ".join(
        filtered_keywords[:TOP_N_KEYWORDS_FROM_RECORD]
    )

    # NEWS
    if source == "news":

        final_text = f"""
        {title}

        {clean_text}

        {keyword_text}
        """
    # REDES SOCIAIS
    else:

        final_text = f"""
       
        {keyword_text}
        """

    return final_text.strip()


# ============================================================
# PROCESSAMENTO INCREMENTAL
# ============================================================

def get_existing_processed_ids(existing_results):
    ids = set()

    for item in existing_results:
        record_id = item.get("record_id")
        source = item.get("source", "")

        unique_id = f"{source}_{record_id}"

        ids.add(unique_id)

    return ids


# ============================================================
# MAIN
# ============================================================

def main():
    print("A CARREGAR DADOS")

    records = []

    for file_path in INPUT_FILES:

        current_records = load_json_file(file_path)

        print(f"\n{file_path}")
        print(f"Registos carregados: {len(current_records)}")

        records.extend(current_records)

    print(f"\nTOTAL DE REGISTOS: {len(records)}")

    # ========================================================
    # RESULTADOS EXISTENTES
    # ========================================================

    existing_results = load_json_file(OUTPUT_RESULTS)

    processed_ids = get_existing_processed_ids(existing_results)

    print(f"Registos já processados: {len(processed_ids)}")

    # ========================================================
    # FILTRAR APENAS NOVOS
    # ========================================================

    new_records = []

    for record in records:

        record_id = record.get("record_id")
        source = record.get("source", "")

        unique_id = f"{source}_{record_id}"

        if unique_id in processed_ids:
            continue

        new_records.append(record)

    print(f"Novos registos encontrados: {len(new_records)}")

    if not new_records:
        print("\nNenhum novo registo para analisar.")
        return

    # ========================================================
    # LIMITADOR OPCIONAL
    # ========================================================

    if MAX_TEXTS is not None:
        new_records = new_records[:MAX_TEXTS]

        print(f"\nA usar apenas {len(new_records)} textos")

    # ========================================================
    # DEVICE
    # ========================================================

    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"\nDispositivo usado: {device}")

    # ========================================================
    # EMBEDDING MODEL
    # ========================================================

    print("\n")
    print("A CARREGAR SENTENCE TRANSFORMER")

    embedding_model = SentenceTransformer(
        MODELO_EMBEDDINGS,
        device=device
    )


    print("\nA CRIAR VECTORIZER")

    vectorizer_model = CountVectorizer(
        stop_words=STOPWORDS_PT,
        ngram_range=(1, 3),
        min_df=3
    )


    print("A CRIAR REPRESENTATION MODEL")
    representation_model = KeyBERTInspired()
    # ========================================================
    # DOCUMENTOS
    # ========================================================
    print("A PREPARAR DOCUMENTOS")

    documents = []

    valid_records = []

    for record in tqdm(new_records):

        text = build_document_text(record)

        if len(text) < 10:
            continue

        documents.append(text)

        valid_records.append(record)

    print(f"\nDocumentos válidos: {len(documents)}")

    if not documents:
        print("\nNenhum documento válido.")
        return

    # ========================================================
    # UMAP
    # ========================================================

    umap_model = UMAP(
        n_neighbors=10,
        n_components=5,
        min_dist=0.0,
        metric="cosine",
        random_state=42,
    )

    # ========================================================
    # HDBSCAN
    # ========================================================

    hdbscan_model = HDBSCAN(
        min_cluster_size=MIN_TOPIC_SIZE,
        min_samples=2,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )

    # ========================================================
    # BERTopic
    # ========================================================
    print("A CRIAR BERTopic")

    topic_model = BERTopic(
        embedding_model=embedding_model,
        vectorizer_model=vectorizer_model,
        representation_model=representation_model,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        language="multilingual",
        calculate_probabilities=True,
        verbose=True,
        nr_topics=20,
        top_n_words=NR_TOP_WORDS,
        min_topic_size=MIN_TOPIC_SIZE,
    )

    # ========================================================
    # FIT TRANSFORM
    # ========================================================
    print("A TREINAR BERTopic")

    topics, probs = topic_model.fit_transform(documents)

    # ========================================================
    # RESULTADOS
    # ========================================================

    print("\n")
    print("A GUARDAR RESULTADOS")

    new_results = []

    for idx, record in enumerate(valid_records):

        topic_id = int(topics[idx])

        probability = None

        try:
            if probs[idx] is not None:
                probability = float(max(probs[idx]))
        except:
            probability = None

        topic_keywords = []

        if topic_id != -1:

            topic_words = topic_model.get_topic(topic_id)

            if topic_words:

                topic_keywords = [
                    word
                    for word, score in topic_words
                ]

        result = {
            "record_id": record.get("record_id", ""),
            "source": record.get("source", ""),
            "created_at": record.get("created_at", ""),
            "title_clean": record.get("title_clean", ""),
            "topic_id": topic_id,
            "topic_probability": probability,
            "topic_keywords": topic_keywords,
        }

        new_results.append(result)

    # ========================================================
    # JUNTAR COM RESULTADOS ANTIGOS
    # ========================================================

    final_results = existing_results + new_results

    save_json_file(final_results, OUTPUT_RESULTS)

    print(f"Resultados guardados em:")
    print(OUTPUT_RESULTS)

    # ========================================================
    # INFO DOS TÓPICOS
    # ========================================================

    topic_info_df = topic_model.get_topic_info()

    topic_info = topic_info_df.to_dict(orient="records")

    save_json_file(topic_info, TOPIC_INFO_OUTPUT)

    print(f"\nInformação dos tópicos guardada em:")
    print(TOPIC_INFO_OUTPUT)

    # ========================================================
    # GUARDAR MODELO
    # ========================================================

    print("\n")
    print("A GUARDAR MODELO BERTopic")

    Path(MODEL_OUTPUT_DIR).mkdir(
        parents=True,
        exist_ok=True
    )

    Path(MODEL_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    topic_model.save(
        MODEL_OUTPUT_DIR,
        serialization="safetensors",
        save_ctfidf=True,
        save_embedding_model=False
    )

    print(f"\nModelo guardado em:")
    print(MODEL_OUTPUT_DIR)

    # ========================================================
    # ESTATÍSTICAS
    # ========================================================

    print("\n")
    print("TOP TÓPICOS")

    topic_counter = Counter(topics)

    for topic_id, count in topic_counter.most_common(20):

        if topic_id == -1:
            continue

        topic_words = topic_model.get_topic(topic_id)

        if topic_words:

            topic_name = ", ".join(
                word
                for word, score in topic_words[:5]
            )

        else:
            topic_name = "SEM NOME"

        print(f"TOPIC {topic_id}")
        print(f"Total documentos: {count}")
        print(f"Keywords: {topic_name}")

    # ========================================================
    # EXEMPLOS
    # ========================================================

    print("\n")
    print("EXEMPLOS")

    for idx in range(min(5, len(new_results))):

        item = new_results[idx]

        print(f"\nTITLE:")
        print(item["title_clean"])

        print(f"\nTOPIC ID:")
        print(item["topic_id"])

        print(f"\nPROBABILITY:")
        print(item["topic_probability"])

        print(f"\nTOPIC KEYWORDS:")
        print(", ".join(item["topic_keywords"]))

    print("BERTopic TERMINADO")


if __name__ == "__main__":
    main()