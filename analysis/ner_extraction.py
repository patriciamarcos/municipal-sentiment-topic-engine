import json
import re
import unicodedata
from pathlib import Path
from collections import Counter
from tqdm import tqdm
from transformers import pipeline
import torch


BASE_DIR = Path(__file__).parent.parent
# ============================================================
# CONFIGURAÇÃO
# ============================================================

INPUT_FILES = [
    BASE_DIR / "data/keywords/news_keywords.json",
    BASE_DIR / "data/keywords/reddit_keywords.json",
    BASE_DIR / "data/keywords/bluesky_keywords.json",
    BASE_DIR / "data/keywords/youtube_keywords.json",
]

OUTPUT_FILE = BASE_DIR / "data/ner/all_ner.json"

MODEL_NAME = "Davlan/xlm-roberta-base-ner-hrl"

MAX_TEXTS = None

VALID_LABELS = [
    "PER",
    "ORG",
    "LOC",
    "MISC",
]

# tamanho seguro para XLM-Roberta
MAX_TOKENS = 400

# mínimo de caracteres totais
MIN_ENTITY_LENGTH = 3

# mínimo de caracteres alfabéticos
MIN_ENTITY_CHARS = 4

ENTITY_NORMALIZATION = {
    # Câmara Municipal
    "câmara": "Câmara Municipal da Covilhã",
    "camara": "Câmara Municipal da Covilhã",
    "cm covilhã": "Câmara Municipal da Covilhã",
    "cm covilha": "Câmara Municipal da Covilhã",
    "câmara da covilhã": "Câmara Municipal da Covilhã",
    "câmara da covilha": "Câmara Municipal da Covilhã",
    "câmara municipal": "Câmara Municipal da Covilhã",
    "câmara municipal da covilhã": "Câmara Municipal da Covilhã",

    # Município
    "município": "Município da Covilhã",
    "municipio": "Município da Covilhã",
    "município da covilhã": "Município da Covilhã",
    "municipio da covilha": "Município da Covilhã",

    # Universidade
    "ubi": "Universidade da Beira Interior",
    "universidade da beira": "Universidade da Beira Interior",
    "universidade beira interior": "Universidade da Beira Interior",
}

GENERIC_ENTITIES = {
    "câmara", "camara",
    "município", "municipio",
    "governo", "assembleia",
    "serra", "presidente",
    "município da", "câmara da",
}
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

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(path, "w", encoding="utf-8") as file:

        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )


# ============================================================
# TEXTO FINAL
# ============================================================

def build_ner_text(record):

    title = str(
        record.get("title_clean", "")
    ).strip()

    clean_text = str(
        record.get("clean_text", "")
    ).strip()

    final_text = f"""
    {title}

    {clean_text}
    """

    return final_text.strip()


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

    for i in range(0, len(tokens), max_tokens):

        chunk_tokens = tokens[i:i + max_tokens]

        chunk_text = tokenizer.decode(
            chunk_tokens,
            skip_special_tokens=True
        )

        chunks.append(chunk_text)

    return chunks


# ============================================================
# LIMPEZA DE TEXTO
# ============================================================

def clean_entity_text(text):

    # remover lixo sentencepiece
    text = text.replace("▁", " ")

    # remover wordpieces
    text = text.replace("##", "")

    # remover espaços duplicados
    text = " ".join(text.split())

    # remover símbolos extremos
    text = text.strip(
        " ,.-:;()[]{}\"'`´"
    )

    return text.strip()


# ============================================================
# NORMALIZAÇÃO AUTOMÁTICA
# ============================================================

def normalize_entity(entity_text):

    entity_text = entity_text.strip()

    # remover múltiplos espaços
    entity_text = " ".join(entity_text.split())

    # remover acentos para comparação
    normalized = unicodedata.normalize(
        "NFKD",
        entity_text
    )

    normalized = "".join(
        c for c in normalized
        if not unicodedata.combining(c)
    )

    normalized = normalized.lower()

    return normalized


# ============================================================
# DETETAR ENTIDADES FRAGMENTADAS
# ============================================================

def is_fragmented_entity(entity_text):

    words = entity_text.split()

    # apenas uma sílaba pequena
    if len(entity_text) <= 4:
        return True

    # terminações muito suspeitas
    suspicious_suffixes = [
        "ção",
        "ções",
        "dade",
        "mento",
    ]

    # fragmentos comuns
    bad_fragments = {
        "vilhã",
        "vilha",
        "fund",
        "mont",
        "bel",
        "co",
        "hã",
        "oso",
        "ata",
        "bia",
        "wel",
        "mo",
        "al",
        "amento",
        "cent",
        "ro",
    }

    if entity_text.lower() in bad_fragments:
        return True

    # palavras muito pequenas
    short_words = 0

    for word in words:

        if len(word) <= 2:
            short_words += 1

    if short_words >= len(words):
        return True

    # entidade sem vogais suficientes
    letters = re.findall(
        r"[a-zà-ÿA-ZÀ-Ÿ]",
        entity_text
    )

    vowels = re.findall(
        r"[aeiouáàâãéêíóôõú]",
        entity_text.lower()
    )

    if len(letters) > 0:

        vowel_ratio = len(vowels) / len(letters)

        if vowel_ratio < 0.2:
            return True

    return False


# ============================================================
# VALIDAR ENTIDADE
# ============================================================

def is_valid_entity(entity_text):

    if not entity_text:
        return False

    entity_text = entity_text.strip()

    # ========================================================
    # TAMANHO MÍNIMO
    # ========================================================

    alpha_chars = re.findall(
        r"[A-Za-zÀ-ÿ]",
        entity_text
    )

    if len(alpha_chars) < MIN_ENTITY_CHARS:
        return False

    # ========================================================
    # APENAS NÚMEROS
    # ========================================================

    if entity_text.isdigit():
        return False

    # ========================================================
    # STOPWORDS / LIXO
    # ========================================================

    invalid_terms = {
        "co",
        "vil",
        "hã",
        "fund",
        "bel",
        "mont",
        "hos",
        "pena",
        "da",
        "de",
        "do",
        "dos",
        "das",
        "em",
        "na",
        "no",
        "nos",
        "nas",
        "sul",
        "norte",
        "centro",
        "este",
        "oeste",
        "ata",
        "oso",
        "era",
        "bia",
        "wel",
        "mo",
        "center",
        "welcome",
        "presidente",
        "presidente da",
        "municipal",
        "local",
        "comunidade"
    }

    if entity_text.lower() in invalid_terms:
        return False

    # ========================================================
    # MUITO CURTO E MINÚSCULO
    # ========================================================

    if re.fullmatch(r"[a-zà-ÿ]+", entity_text.lower()):

        if len(entity_text) <= 4:
            return False

    # ========================================================
    # FRAGMENTOS ESTRANHOS
    # ========================================================
    # começa minúscula
    if entity_text[0].islower():
        return False

    # ========================================================
    # MUITOS SÍMBOLOS
    # ========================================================

    symbol_count = len(
        re.findall(r"[^A-Za-zÀ-ÿ0-9\s\-]", entity_text)
    )

    if symbol_count > 3:
        return False

    # ========================================================
    # UMA ÚNICA LETRA MAIÚSCULA
    # ========================================================

    words = entity_text.split()

    if len(words) == 1:

        if len(words[0]) <= 3:
            return False

    return True

# ============================================================
# REMOVER DUPLICADOS + NORMALIZAR
# ============================================================
def normalize_entity_text(text):
    key = text.lower().strip()
    return ENTITY_NORMALIZATION.get(key, text)


def remove_substring_duplicates(entities):
    texts = [e["text"] for e in entities]
    final = []

    for entity in entities:
        is_substring = any(
            entity["text"] != other
            and entity["text"] in other
            for other in texts
        )
        if not is_substring:
            final.append(entity)

    return final

def remove_duplicate_entities(entities):

    seen = set()

    final_entities = []

    for entity in entities:

        normalized_text = normalize_entity(
            entity["text"]
        )

        key = (
            normalized_text,
            entity["label"]
        )

        if key in seen:
            continue

        seen.add(key)

        final_entities.append(entity)

    return final_entities


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

        records.extend(current_records)

    print(
        f"TOTAL DE REGISTOS: "
        f"{len(records)}"
    )

    # ========================================================
    # LIMITADOR OPCIONAL
    # ========================================================

    if MAX_TEXTS is not None:

        records = records[:MAX_TEXTS]

        print(
            f"A usar {len(records)} textos"
        )

    # ========================================================
    # DEVICE
    # ========================================================

    device = 0 if torch.cuda.is_available() else -1

    print("\n")
    print(
        f"Dispositivo usado: "
        f"{'cuda' if device == 0 else 'cpu'}"
    )

    # ========================================================
    # MODELO
    # ========================================================

    print("\n")
    print("A CARREGAR MODELO NER")

    ner_pipeline = pipeline(
        "ner",
        model=MODEL_NAME,
        tokenizer=MODEL_NAME,
        aggregation_strategy="simple",
        device=device
    )

    tokenizer = ner_pipeline.tokenizer

    # ========================================================
    # PROCESSAMENTO
    # ========================================================

    print("\n")
    print("A EXTRAIR ENTIDADES")

    results = []

    entity_counter = Counter()

    label_counter = Counter()

    for record in tqdm(records):

        text = build_ner_text(record)

        if len(text) < 20:
            continue

        # ====================================================
        # CHUNKS
        # ====================================================

        chunks = split_text_into_chunks(
            text,
            tokenizer,
            max_tokens=MAX_TOKENS
        )

        entities = []

        # ====================================================
        # PROCESSAR CHUNKS
        # ====================================================

        for chunk in chunks:

            try:

                predictions = ner_pipeline(
                    chunk
                )

            except Exception as e:

                print("\nERRO AO PROCESSAR CHUNK")
                print(e)

                continue

            for pred in predictions:

                label = pred["entity_group"]

                if label not in VALID_LABELS:
                    continue

                entity_text = clean_entity_text(
                    pred["word"]
                )

                if not is_valid_entity(
                    entity_text
                ):
                    continue

                # normalizar variantes para forma canónica
                entity_text = normalize_entity_text(entity_text)

                entity = {
                    "text": entity_text,
                    "label": label
                }

                entities.append(entity)

        # ====================================================
        # REMOVER DUPLICADOS
        # ====================================================

        entities = remove_duplicate_entities(entities)
        entities = remove_substring_duplicates(entities)

        # ====================================================
        # CONTADORES
        # ====================================================

        for entity in entities:

            entity_counter[
                entity["text"]
            ] += 1

            label_counter[
                entity["label"]
            ] += 1

        # ====================================================
        # RESULTADO FINAL
        # ====================================================

        result = {
            "record_id": record.get(
                "record_id",
                ""
            ),
            "source": record.get(
                "source",
                ""
            ),
            "created_at": record.get(
                "created_at",
                ""
            ),
            "title_clean": record.get(
                "title_clean",
                ""
            ),
            "entities": entities
        }

        results.append(result)

    # ========================================================
    # GUARDAR RESULTADOS
    # ========================================================

    print("\n")
    print("A GUARDAR RESULTADOS")

    save_json_file(
        results,
        OUTPUT_FILE
    )

    print("Resultados guardados em:")
    print(OUTPUT_FILE)

    # ========================================================
    # ESTATÍSTICAS
    # ========================================================

    print("\n")
    print("TOP ENTIDADES")

    for entity, count in entity_counter.most_common(30):

        print(f"{entity} -> {count}")

    print("\n")
    print("TOP LABELS")

    for label, count in label_counter.most_common():

        print(f"{label} -> {count}")

    # ========================================================
    # EXEMPLOS
    # ========================================================

    print("\n")
    print("EXEMPLOS")

    for idx in range(min(5, len(results))):

        item = results[idx]

        print("\nTITLE:")
        print(item["title_clean"])

        print("\nENTITIES:")

        if not item["entities"]:

            print("Sem entidades")

        else:

            for ent in item["entities"]:

                print(
                    f"{ent['text']} "
                    f"({ent['label']})"
                )

    print("\nNER TERMINADO")


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    main()