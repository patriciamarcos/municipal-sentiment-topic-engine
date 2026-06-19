import json
from pathlib import Path
from text_cleaning import clean_news_record

INPUT_FILE = Path("news_posts.json")
OUTPUT_FILE = Path("news_posts_cleaned.json")

LIMIT = None


def load_json(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return value

        return [data]

    return []


def save_json(data, file_path: Path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Ficheiro não encontrado: {INPUT_FILE}")

    records = load_json(INPUT_FILE)

    print(f"Total de registos encontrados: {len(records)}")

    cleaned_records = []
    ignored_records = 0

    for record in records:
        cleaned = clean_news_record(record, min_chars=30)

        if cleaned is None:
            ignored_records += 1
            continue

        cleaned_records.append(cleaned)

        if LIMIT is not None and len(cleaned_records) >= LIMIT:
            break

    print(f"Registos limpos válidos: {len(cleaned_records)}")
    print(f"Registos ignorados: {ignored_records}")

    for i, item in enumerate(cleaned_records[:5], start=1):
        print("\n" + "=" * 100)
        print(f"REGISTO {i}")
        print("=" * 100)

        print("\nTÍTULO ORIGINAL:")
        print(item["title_original"])

        print("\nTÍTULO LIMPO:")
        print(item["title_clean"])

        if "has_body_text" in item:
            print("\nTEM CORPO DE TEXTO:")
            print(item["has_body_text"])

        print("\nTEXTO LIMPO:")
        print(item["clean_text"][:1000])

    save_json(cleaned_records, OUTPUT_FILE)

    print("\n" + "=" * 100)
    print("RESUMO")
    print("=" * 100)
    print(f"Total original: {len(records)}")
    print(f"Total limpo guardado: {len(cleaned_records)}")
    print(f"Total ignorado: {ignored_records}")
    print(f"Ficheiro gerado: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()