import json
import re
from pathlib import Path
from collections import Counter
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
import torch
from tqdm import tqdm


# ============================================================
# CONFIGURAÇÃO
# ============================================================

FILES_TO_PROCESS = [
    {
        "name": "news",
        "input_path": "data/clean/news/news_cleaned.json",
        "output_path": "data/keywords/news_keywords.json",
        "top_n": 10,
        "min_chars": 20,
    },
    {
        "name": "bluesky",
        "input_path": "data/clean/bluesky/bluesky_cleaned.json",
        "output_path": "data/keywords/bluesky_keywords.json",
        "top_n": 8,
        "min_chars": 10,
    },
    {
        "name": "reddit",
        "input_path": "data/clean/reddit/reddit_cleaned.json",
        "output_path": "data/keywords/reddit_keywords.json",
        "top_n": 10,
        "min_chars": 20,
    },
    {
        "name": "youtube",
        "input_path": "data/clean/youtube/youtube_cleaned.json",
        "output_path": "data/keywords/youtube_keywords.json",
        "top_n": 10,
        "min_chars": 20,
    },
]


MODELO_KEYBERT = "paraphrase-multilingual-MiniLM-L12-v2"
MOSTRAR_EXEMPLOS = 2

# ============================================================
# BLACKLIST
# ============================================================

BLACKLIST_KEYWORDS = [
    # locais/fontes
    "covilhã",
    "covilha",
    "beira interior",
    "município",
    "município da covilhã",
    "câmara municipal",
    "presidente câmara",
    "cm covilhã",

    # jornais/fontes
    "notícias",
    "noticias",
    "rádio",
    "clube",
    "rádio clube",
    "clube da covilhã",
    "noticias da covilhã",
    "notícias da covilhã",
    "notícias do centro",
    "diário imobiliário",
    "jornal o interior",
    "maisbeiras informação",
    "central press",
    "sapo",
    "zerozero.pt",
    "universidade da beira",

    # lixo editorial
    "publicação comentários",
    "artigos espaço comentário",
    "espaço comentário",
    "comentário considera",
    "comentários são",
    "possível efectuar comentários",
    "advenham publicação comentários",
    "comentar leitor declarar",
    "entanto redação",
    "redação",
    "comentários",
    "comentário",
    "refletem opinião posição correio",
    "opiniões ideias apela leitores",
    "comentar independentemente",
    "considera essencial reflexão debate",
    "livre veiculação opiniões",
    "conteúdos comentários são",

    # futebol spam
    "goal",
    "scores for",
    "fulltime",

    # genéricos
    "candidato",
    "futebol",
    "data",
]


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
    "aquele", "aquela",
    "também", "ainda", "já",
    "mais", "muito",
    "num", "numa",
    "neste", "nesta",
    "durante", "segundo",
    "onde", "quando", "após",
    "dia", "dias", "ano", "anos",
    "maio", "junho", "abril",
    "janeiro", "fevereiro",
    "março", "julho",
    "agosto", "setembro",
    "outubro", "novembro",
    "dezembro",
    "pelo", "pela",
    "pelos", "pelas",
    "lhe", "lhes",
    "seu", "sua",
    "seus", "suas",
    "mesmo", "mesma",
    "forma", "âmbito",
    "nota", "imprensa",
    "comunicado",
    "afirmou", "referiu",
    "explicou", "adiantou",
    "adianta",
]


PALAVRAS_FRACAS = [
    "foi", "foram", "ser", "ter",
    "tem", "teve", "terá",
    "vai", "irá", "está",
    "estão", "ficou", "fica",
    "disse", "afirmou",
    "referiu", "explicou",
    "adianta", "segundo",
    "apesar", "após",
    "antes", "durante",
    "nesta", "neste",
    "nessa", "nesse",
    "desta", "deste",
    "este", "esta",
    "estes", "estas",
]


INICIOS_INVALIDOS = [
    "pela", "pelo", "pelos", "pelas",
    "para", "com", "sem",
    "de", "da", "do",
    "das", "dos",
    "na", "no",
    "nas", "nos",
    "que", "foi",
    "será", "terá",
    "este", "esta",
    "estes", "estas",
    "segundo",
    "apesar",
    "após",
]


FINAIS_INVALIDOS = [
    "pela", "pelo",
    "pelos", "pelas",
    "para", "com",
    "sem", "de",
    "da", "do",
    "das", "dos",
    "na", "no",
    "nas", "nos",
    "foi", "será",
    "terá", "está",
    "estão",
]


# ============================================================
# JSON
# ============================================================

def load_json_file(file_path):
    file_path = Path(file_path)

    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return data

    raise ValueError("JSON inválido.")


def load_existing_keywords(output_path):

    output_path = Path(output_path)

    if not output_path.exists():
        return []

    with open(output_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return data

    return []


def save_json_file(data, output_path):
    output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


# ============================================================
# LIMPEZA DE TEXTO
# ============================================================

def normalize_text(text):
    text = str(text or "")
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"\S+@\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def texto_tem_ruido(texto):
    texto = texto.lower()

    termos_ruido = [
        "cookies necessários",
        "cookies funcionais",
        "ofertas comerciais",
        "envia o teu feedback",
        "esta voz foi gerada",
        "aceitar cookies",
        "política de privacidade",
        "termos e condições",
        "publicação comentários",
        "espaço comentário",
        "comentários são da exclusiva responsabilidade",
        "o conteúdo dos comentários",
        "menu record",
        "assinar e-paper",
        "pesquisa premium",
        "os comentários refletem",
        "opiniões expressas",
        "espaço de comentário",
        "livre veiculação",
        "apela aos leitores",
        "posição editorial",
        "comentário considera",
        "conteúdos comentários",
        "possível efectuar comentários",
        "comentar leitor",
        "reflexão debate",
        "redação reserva",
        "regras de participação",
    ]

    return any(t in texto for t in termos_ruido)

# ============================================================
# QUALIDADE DAS KEYWORDS
# ============================================================

def keyword_valida(keyword):
    keyword = keyword.lower().strip()

    if len(keyword) < 4:
        return False

    if keyword in BLACKLIST_KEYWORDS:
        return False

    for termo in BLACKLIST_KEYWORDS:
        if termo in keyword:
            return False

    palavras = keyword.split()

    if len(palavras) > 4:
        return False

    invalidas = [
        "foi", "ser", "tem", "teve", "vai",
        "está", "estão", "desde", "após",
        "durante", "segundo", "sobre", "para",
        "com", "sem",
    ]

    if palavras[0] in invalidas:
        return False

    if palavras[-1] in invalidas:
        return False

    return True


def keyword_tem_qualidade(keyword):
    keyword_lower = keyword.lower().strip()

    palavras = keyword_lower.split()

    if len(keyword_lower) < 4:
        return False

    if len(palavras) > 4:
        return False

    if palavras[0] in INICIOS_INVALIDOS:
        return False

    if palavras[-1] in FINAIS_INVALIDOS:
        return False

    if any(p in PALAVRAS_FRACAS for p in palavras):
        return False

    if all(p.isdigit() for p in palavras):
        return False

    return True

# ============================================================
# EXTRAÇÃO
# ============================================================

def extract_keywords(text, model, top_n=10):
    keywords = model.extract_keywords(
        text,
        keyphrase_ngram_range=(2, 4),
        stop_words=STOPWORDS_PT,
        top_n=top_n * 5,
        use_mmr=True,
        diversity=0.4,
    )

    final_keywords = []

    seen = set()

    for keyword, score in keywords:
        keyword = keyword.strip()

        keyword_normalized = keyword.lower()

        if keyword_normalized in seen:
            continue

        if not keyword_valida(keyword):
            continue

        if not keyword_tem_qualidade(keyword):
            continue

        final_keywords.append({
            "keyword": keyword,
            "score": round(float(score), 4),
        })

        seen.add(keyword_normalized)

        if len(final_keywords) >= top_n:
            break

    return final_keywords


# ============================================================
# PROCESSAMENTO
# ============================================================

def process_record(record, model, top_n=10, min_chars=80):
    text = str(record.get("clean_text", "")).strip()
    text = normalize_text(text)

    if not text:
        return None

    if len(text) < min_chars:
        return None

    if texto_tem_ruido(text):
        return None

    keywords = extract_keywords(
        text=text,
        model=model,
        top_n=top_n,
    )

    if not keywords:
        return None

    return {
        "record_id": record.get("record_id", ""),
        "source": record.get("source", ""),
        "created_at": record.get("created_at", ""),
        "title_clean": record.get("title_clean", ""),
        "clean_text": text,
        "keywords": keywords,
    }

# ============================================================
# ESTATÍSTICAS
# ============================================================

def show_statistics(results):
    keyword_counter = Counter()

    for record in results:
        for kw in record["keywords"]:
            keyword_counter[kw["keyword"].lower()] += 1

    print("\n")
    print("TOP KEYWORDS")

    for keyword, count in keyword_counter.most_common(20):
        print(f"{keyword} -> {count}")


def show_examples(results, limit=5):
    print("\n")
    print("EXEMPLOS")

    for i, record in enumerate(results[:limit], start=1):
        print("\n")
        print(f"EXEMPLO {i}")

        print("\nTITLE:")
        print(record["title_clean"])

        print("KEYWORDS:")

        for kw in record["keywords"]:
            print(f"- {kw['keyword']} ({kw['score']})")


# ============================================================
# MAIN
# ============================================================
def process_file(file_config, model):

    input_path = Path(file_config["input_path"])

    if not input_path.exists():
        print(f"\nFicheiro não encontrado: {input_path}")
        return

    print("\n")
    print(f"PROCESSAMENTO -> {file_config['name'].upper()}")

    records = load_json_file(input_path)

    print(f"\nRegistos carregados: {len(records)}")

    # ============================================================
    # CARREGAR RESULTADOS EXISTENTES
    # ============================================================

    existing_results = load_existing_keywords(
        file_config["output_path"]
    )

    processed_ids = {
        r.get("record_id")
        for r in existing_results
    }

    print(f"Registos já processados: {len(processed_ids)}")

    # ============================================================
    # PROCESSAMENTO INCREMENTAL
    # ============================================================

    new_results = []

    skipped_existing = 0

    for record in tqdm(records):

        record_id = record.get("record_id")

        if record_id in processed_ids:
            skipped_existing += 1
            continue

        processed = process_record(
            record=record,
            model=model,
            top_n=file_config["top_n"],
            min_chars=file_config["min_chars"],
        )

        if processed is not None:
            new_results.append(processed)

    # ============================================================
    # JUNTAR RESULTADOS
    # ============================================================

    final_results = existing_results + new_results

    save_json_file(
        final_results,
        file_config["output_path"]
    )

    print(f"\nRegistos já existentes ignorados: {skipped_existing}")
    print(f"Novos registos processados: {len(new_results)}")
    print(f"Total acumulado: {len(final_results)}")

    print(f"\nGuardado em: {file_config['output_path']}")

    show_statistics(final_results)

    show_examples(new_results, limit=MOSTRAR_EXEMPLOS)


def main():
    print("\n")
    print("A CARREGAR KEYBERT")

    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"\nDispositivo usado: {device}")

    sentence_model = SentenceTransformer(
        MODELO_KEYBERT,
        device=device
    )

    model = KeyBERT(model=sentence_model)

    for file_config in FILES_TO_PROCESS:
        process_file(file_config, model)

    print("\n")
    print("EXTRAÇÃO DE KEYWORDS TERMINADA")


if __name__ == "__main__":
    main()