import json
import re
import random
from pathlib import Path
from collections import Counter

FILES_TO_VALIDATE = [
    {
        "name": "NEWS",
        "cleaned_path": "data/clean/news/news_cleaned.json",
        "skipped_path": "data/clean/news/news_skipped.json",
    },
    {
        "name": "BLUESKY",
        "cleaned_path": "data/clean/bluesky/bluesky_cleaned.json",
        "skipped_path": "data/clean/bluesky/bluesky_skipped.json",
    },
    {
        "name": "REDDIT",
        "cleaned_path": "data/clean/reddit/reddit_cleaned.json",
        "skipped_path": "data/clean/reddit/reddit_skipped.json",
    },
]


# =========================================================
# UTILIDADES
# =========================================================

def load_json(path):
    path = Path(path)

    if not path.exists():
        print(f"FICHEIRO NÃO ENCONTRADO: {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_encoding_problems(text):
    """
    Procura problemas comuns de encoding.
    """
    patterns = [
        "Ã",
        "�",
        "â€™",
        "â€œ",
        "â€",
    ]

    return any(p in text for p in patterns)


def detect_remaining_urls(text):
    """
    Verifica se ainda existem URLs no texto limpo.
    """
    return bool(re.search(r"https?://|www\.", text))


def detect_noise_patterns(text):
    """
    Procura padrões de ruído que possam ter escapado.
    """
    noise_patterns = [
        "cookies",
        "newsletter",
        "aceitar cookies",
        "política de privacidade",
        "termos e condições",
    ]

    text_lower = text.lower()

    return any(pattern in text_lower for pattern in noise_patterns)


def find_duplicate_clean_texts(records):
    """
    Procura textos limpos duplicados.
    """
    clean_texts = []

    for record in records:
        clean_text = record.get("clean_text", "").strip()

        if clean_text:
            clean_texts.append(clean_text)

    counter = Counter(clean_texts)

    duplicates = {
        text: count
        for text, count in counter.items()
        if count > 1
    }

    return duplicates


# =========================================================
# VALIDAÇÃO PRINCIPAL
# =========================================================

def validate_dataset(name, cleaned_path, skipped_path):

    print("\n" + "=" * 120)
    print(f"VALIDAÇÃO -> {name}")

    cleaned_records = load_json(cleaned_path)
    skipped_records = load_json(skipped_path)

    total_cleaned = len(cleaned_records)
    total_skipped = len(skipped_records)

    print(f"\nTotal cleaned: {total_cleaned}")
    print(f"Total skipped: {total_skipped}")

    # -----------------------------------------------------
    # TEXTOS MUITO CURTOS
    # -----------------------------------------------------

    short_records = []

    for record in cleaned_records:
        clean_text = record.get("clean_text", "")

        if len(clean_text.strip()) < 20:
            short_records.append(record)

    print(f"\nTextos muito curtos (<20 chars): {len(short_records)}")

    # -----------------------------------------------------
    # URLS RESTANTES
    # -----------------------------------------------------

    records_with_urls = []

    for record in cleaned_records:
        clean_text = record.get("clean_text", "")

        if detect_remaining_urls(clean_text):
            records_with_urls.append(record)

    print(f"Textos com URLs restantes: {len(records_with_urls)}")

    # -----------------------------------------------------
    # PROBLEMAS DE ENCODING
    # -----------------------------------------------------

    encoding_problems = []

    for record in cleaned_records:
        clean_text = record.get("clean_text", "")

        if detect_encoding_problems(clean_text):
            encoding_problems.append(record)

    print(f"Problemas de encoding: {len(encoding_problems)}")

    # -----------------------------------------------------
    # RUÍDO RESTANTE
    # -----------------------------------------------------

    noisy_records = []

    for record in cleaned_records:
        clean_text = record.get("clean_text", "")

        if detect_noise_patterns(clean_text):
            noisy_records.append(record)

    print(f"Possível ruído restante: {len(noisy_records)}")

    # -----------------------------------------------------
    # DUPLICADOS
    # -----------------------------------------------------

    duplicates = find_duplicate_clean_texts(cleaned_records)

    print(f"Textos limpos duplicados: {len(duplicates)}")

    # -----------------------------------------------------
    # MOSTRAR ALGUNS DUPLICADOS
    # -----------------------------------------------------

    if duplicates:
        print("\nEXEMPLOS DE DUPLICADOS:")

        for i, (text, count) in enumerate(list(duplicates.items())[:5], start=1):
            print("\n" + "-" * 80)
            print(f"DUPLICADO {i}")
            print(f"Ocorrências: {count}")
            print(text[:300])

    # -----------------------------------------------------
    # EXEMPLOS ALEATÓRIOS
    # -----------------------------------------------------

    print("\n" + "=" * 120)
    print("EXEMPLOS ALEATÓRIOS")

    sample_size = min(5, len(cleaned_records))

    random_samples = random.sample(cleaned_records, sample_size)

    for i, record in enumerate(random_samples, start=1):

        print("\n" + "-" * 100)
        print(f"EXEMPLO {i}")
        print("-" * 100)

        print("\nSOURCE:")
        print(record.get("source", ""))

        print("\nTITLE:")
        print(record.get("title_clean", ""))

        print("\nTEXT:")
        print(record.get("clean_text", "")[:700])

        print("\nLIKES:")
        print(record.get("like_count", 0))

        print("\nREPLIES:")
        print(record.get("reply_count", 0))

    # -----------------------------------------------------
    # EXEMPLOS DE PROBLEMAS
    # -----------------------------------------------------

    if records_with_urls:
        print("\n" + "=" * 120)
        print("EXEMPLOS COM URLS RESTANTES")

        for record in records_with_urls[:3]:
            print("\n")
            print(record.get("clean_text", "")[:500])

    if encoding_problems:
        print("\n" + "=" * 120)
        print("EXEMPLOS COM ENCODING PARTIDO")

        for record in encoding_problems[:3]:
            print("\n")
            print(record.get("clean_text", "")[:500])

    if noisy_records:
        print("\n" + "=" * 120)
        print("EXEMPLOS COM POSSÍVEL RUÍDO")

        for record in noisy_records[:3]:
            print("\n")
            print(record.get("clean_text", "")[:500])

    # -----------------------------------------------------
    # SKIPPED EXAMPLES
    # -----------------------------------------------------

    if skipped_records:

        print("\n" + "=" * 120)
        print("EXEMPLOS IGNORADOS")

        for skipped in skipped_records[:5]:

            original = skipped.get("original_record", {})

            text = (
                original.get("text")
                or original.get("content")
                or original.get("message")
                or ""
            )

            print(f"REASON: {skipped.get('reason')}")

            print("\nTEXT:")
            print(str(text)[:500])


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print("\n")
    print("INÍCIO DA VALIDAÇÃO DE LIMPEZA")

    for config in FILES_TO_VALIDATE:

        validate_dataset(
            name=config["name"],
            cleaned_path=config["cleaned_path"],
            skipped_path=config["skipped_path"],
        )

    print("\n")
    print("VALIDAÇÃO TERMINADA")
