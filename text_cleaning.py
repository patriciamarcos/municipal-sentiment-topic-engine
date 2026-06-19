import re
import html
import json
import hashlib
import unicodedata
from pathlib import Path


NEWS_SOURCES_TO_REMOVE = [
    "Rádio Clube da Covilhã",
    "Noticias da Covilhã",
    "Notícias da Covilhã",
    "Notícias do Centro",
    "Diário Imobiliário",
    "Jornal o Interior",
    "MaisBeiras Informação",
    "Universidade da Beira Interior",
    "SAPO",
    "Central Press",
    "Rádio Altitude",
    "zerozero.pt",
    "Município da Covilhã",
]


NOISE_PATTERNS = [
    "cookies necessários",
    "cookies funcionais",
    "cookies publicitários",
    "ofertas comerciais",
    "esta voz foi gerada com recurso a inteligência artificial",
    "este resumo foi criado com recurso a inteligência artificial",
    "envia o teu feedback",
    "subscreva a nossa newsletter",
    "aceitar cookies",
    "política de privacidade",
    "termos e condições",
    "assinar e-paper",
    "pesquisa premium",
    "deseja receber notificações",
]


SCRAPING_CORRECTIONS = {
    "apostouna": "apostou na",
    "procuroureduzir": "procurou reduzir",
    "servem-se": "servem-se",
    "fim-de-semana": "fim-de-semana",
}


def normalize_unicode(text):
    """
    Normaliza caracteres Unicode sem remover acentos.
    Mantém caracteres portugueses como ç, ã, õ, á, é, í, ó, ú.
    """
    if text is None:
        return ""

    text = str(text)
    return unicodedata.normalize("NFC", text)


def decode_html_entities(text):
    """
    Converte entidades HTML para texto normal.
    Exemplo:
    &amp; -> &
    &quot; -> "
    """
    if text is None:
        return ""

    return html.unescape(str(text))


def normalize_quotes_and_dashes(text):
    """
    Normaliza aspas, apóstrofos, travessões e hífens especiais.
    Isto ajuda a evitar variações causadas por scraping.
    """
    replacements = {
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "´": "'",
        "`": "'",
        "–": "-",
        "—": "-",
        "−": "-",
        "\u00a0": " ",
        "\u200b": "",
        "\ufeff": "",
    }

    for wrong, right in replacements.items():
        text = text.replace(wrong, right)

    return text


def remove_urls(text):
    """
    Remove URLs normais e alguns URLs mal formatados que aparecem no scraping.
    """
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)

    # Alguns textos extraídos aparecem como:
    # httpsdocs.google.com...
    # httpsforms.gle...
    # httpspreview.redd.it...
    text = re.sub(r"\bhttps\S+", " ", text)

    return text


def remove_emails(text):
    """
    Remove emails.
    """
    return re.sub(r"\b\S+@\S+\.\S+\b", " ", text)


def remove_mentions(text):
    """
    Remove menções de redes sociais, como @utilizador.
    """
    return re.sub(r"@\w+", " ", text)


def clean_hashtags(text):
    """
    Remove o símbolo #, mas mantém a palavra.
    Exemplo:
    #Covilhã -> Covilhã
    """
    return re.sub(r"#(\w+)", r"\1", text)


def remove_extra_whitespace(text):
    """
    Remove espaços repetidos, tabs e quebras excessivas.
    """
    return re.sub(r"\s+", " ", text).strip()


def fix_known_scraping_errors(text):
    """
    Corrige erros específicos observados no scraping.
    Esta função pode crescer à medida que fores encontrando novos problemas.
    """
    for wrong, right in SCRAPING_CORRECTIONS.items():
        text = text.replace(wrong, right)

    return text


def remove_news_source_from_title(title):
    """
    Remove a fonte no fim do título.

    Exemplo:
    'Título da notícia - Rádio Clube da Covilhã'
    fica:
    'Título da notícia'
    """
    title = str(title or "").strip()

    for source in NEWS_SOURCES_TO_REMOVE:
        suffix = f" - {source}"

        if title.endswith(suffix):
            title = title[: -len(suffix)].strip()

    return title


def is_noise_text(text):
    """
    Verifica se o texto parece ser ruído de scraping.
    """
    text_lower = str(text or "").lower()

    return any(pattern in text_lower for pattern in NOISE_PATTERNS)


def is_too_short(text, min_chars=30):
    """
    Verifica se o texto é demasiado curto para análise.
    """
    text = str(text or "").strip()
    return len(text) < min_chars


def remove_repeated_title_from_text(title, body):
    """
    Evita duplicar o título se o corpo do texto já começar com o título.
    """
    title = str(title or "").strip()
    body = str(body or "").strip()

    if not title:
        return body

    if not body:
        return title

    if body.lower().startswith(title.lower()):
        return body

    return f"{title}. {body}"


def clean_text_basic(text):
    """
    Limpeza geral e segura para NLP.

    Não remove acentos.
    Não transforma tudo em minúsculas.
    Não remove pontuação importante.
    Isto é importante para NER e modelos de linguagem.
    """
    text = normalize_unicode(text)
    text = decode_html_entities(text)
    text = normalize_quotes_and_dashes(text)
    text = remove_urls(text)
    text = remove_emails(text)
    text = clean_hashtags(text)
    text = remove_mentions(text)
    text = fix_known_scraping_errors(text)
    text = remove_extra_whitespace(text)

    return text


def validate_clean_text(clean_text, min_chars=30):
    """
    Valida se o texto limpo pode ser usado para análise.

    Devolve:
    - True/False
    - motivo de rejeição, se existir
    """
    if not clean_text:
        return False, "empty_text"

    if is_too_short(clean_text, min_chars=min_chars):
        return False, "too_short"

    if is_noise_text(clean_text):
        return False, "noise_text"

    return True, None


def get_record_source(record):
    """
    Obtém a fonte/plataforma do registo.
    """
    return (
        record.get("source")
        or record.get("Fonte")
        or "unknown"
    )


def get_record_platform_id(record):
    """
    Obtém o ID externo do registo, quando existe.
    """
    return str(record.get("platform_id", "") or "").strip()


def get_record_title(record):
    """
    Obtém o título do registo, aceitando campos em inglês e português.
    """
    return (
        record.get("title")
        or record.get("Título")
        or ""
    )


def get_record_text(record):
    """
    Obtém o texto principal do registo, aceitando vários nomes de campo.
    """
    return (
        record.get("text")
        or record.get("Texto")
        or record.get("content")
        or record.get("description")
        or record.get("body")
        or record.get("message")
        or ""
    )


def get_record_author(record):
    """
    Obtém o autor do registo.
    """
    return (
        record.get("author")
        or record.get("Autor")
        or record.get("author_handle")
        or ""
    )


def get_record_created_at(record):
    """
    Obtém a data de criação/publicação do registo.
    """
    return (
        record.get("created_at")
        or record.get("Data")
        or ""
    )


def get_record_url(record):
    """
    Obtém o URL do registo.
    """
    return (
        record.get("url")
        or record.get("URL")
        or ""
    )


def get_like_count(record):
    """
    Obtém likes/upvotes de acordo com a estrutura do ficheiro.
    """
    metrics = record.get("metrics", {})

    if isinstance(metrics, dict):
        return metrics.get("likes", metrics.get("upvotes", 0)) or 0

    return record.get("Upvotes", 0) or 0


def get_reply_count(record):
    """
    Obtém número de respostas/comentários de acordo com a estrutura do ficheiro.
    """
    metrics = record.get("metrics", {})

    if isinstance(metrics, dict):
        return metrics.get("replies", metrics.get("comments", 0)) or 0

    return record.get("Total Comentários", 0) or 0


def generate_record_id(record):
    """
    Gera um identificador único para cada registo.

    Prioridade:
    1. source + platform_id
    2. source + url
    3. hash baseado em source + título + texto
    """
    source = str(get_record_source(record) or "").strip()
    platform_id = get_record_platform_id(record)
    url = str(get_record_url(record) or "").strip()

    if platform_id:
        return f"{source}_{platform_id}"

    if url:
        return f"{source}_{url}"

    title = str(get_record_title(record) or "").strip()
    text = str(get_record_text(record) or "").strip()

    raw_value = f"{source}|{title}|{text}"
    return hashlib.md5(raw_value.encode("utf-8")).hexdigest()


def remove_duplicate_records(records):
    """
    Remove duplicados do ficheiro raw ANTES da limpeza.

    Critério:
    - mesmo record_id = duplicado

    Mantém apenas a primeira ocorrência.
    """
    unique_records = []
    seen_ids = set()
    duplicate_count = 0

    for record in records:
        record_id = generate_record_id(record)

        if record_id in seen_ids:
            duplicate_count += 1
            continue

        seen_ids.add(record_id)
        unique_records.append(record)

    return unique_records, duplicate_count


def build_text_from_news_record(record):
    """
    Constrói o texto final a partir de um registo de notícia.
    Usa title + text, porque há notícias em que o campo text está vazio.
    """
    title = remove_news_source_from_title(record.get("title", ""))
    body = str(record.get("text", "") or "").strip()

    return remove_repeated_title_from_text(title, body)


def clean_news_record(record, min_chars=30):
    """
    Limpa um registo de notícia e devolve um dicionário preparado
    para análise posterior.

    Se o texto for ruído ou demasiado curto, devolve None.
    """
    record_id = generate_record_id(record)

    original_title = str(record.get("title", "") or "").strip()
    clean_title = remove_news_source_from_title(original_title)

    original_text = build_text_from_news_record(record)
    clean_text = clean_text_basic(original_text)

    is_valid, reason = validate_clean_text(clean_text, min_chars=min_chars)

    if not is_valid:
        return None

    return {
        "record_id": record_id,
        "source": record.get("source", ""),
        "platform_id": record.get("platform_id", ""),
        "source_type": "POST",
        "author": record.get("author", ""),
        "title_original": original_title,
        "title_clean": clean_title,
        "url": record.get("url", ""),
        "created_at": record.get("created_at", ""),
        "original_text": original_text,
        "clean_text": clean_text,
        "language": "pt",
        "like_count": get_like_count(record),
        "reply_count": get_reply_count(record),
    }


def clean_post_record(record, min_chars=30):
    """
    Limpa um post genérico de rede social.
    Pode ser usado para Bluesky, Reddit, Facebook, etc.
    Aceita campos em inglês e português.
    """
    record_id = generate_record_id(record)

    source = get_record_source(record)
    platform_id = get_record_platform_id(record)
    title = get_record_title(record)
    original_text = get_record_text(record)

    if not original_text and title:
        original_text = title

    clean_text = clean_text_basic(original_text)

    is_valid, reason = validate_clean_text(clean_text, min_chars=min_chars)

    if not is_valid:
        return None

    return {
        "record_id": record_id,
        "source": source,
        "platform_id": platform_id,
        "source_type": "POST",
        "author": get_record_author(record),
        "title_original": str(title or "").strip(),
        "title_clean": clean_text_basic(title) if title else "",
        "url": get_record_url(record),
        "created_at": get_record_created_at(record),
        "original_text": str(original_text or "").strip(),
        "clean_text": clean_text,
        "language": "pt",
        "like_count": get_like_count(record),
        "reply_count": get_reply_count(record),
    }


def clean_comment_record(record, min_chars=10):
    """
    Limpa comentários/respostas.
    O min_chars pode ser mais baixo porque comentários costumam ser curtos.
    Esta função é para comentários já separados num ficheiro próprio.
    """
    record_id = generate_record_id(record)

    original_text = (
        record.get("comment_text")
        or record.get("Texto")
        or record.get("text")
        or record.get("content")
        or record.get("body")
        or record.get("message")
        or ""
    )

    clean_text = clean_text_basic(original_text)

    is_valid, reason = validate_clean_text(clean_text, min_chars=min_chars)

    if not is_valid:
        return None

    return {
        "record_id": record_id,
        "source": get_record_source(record),
        "platform_id": get_record_platform_id(record),
        "source_type": "COMMENT",
        "external_comment_id": record.get("comment_id", record.get("external_comment_id", "")),
        "parent_comment_id": record.get("parent_comment_id", ""),
        "author_handle": (
            record.get("comment_author")
            or record.get("author_handle")
            or record.get("author")
            or record.get("Autor")
            or ""
        ),
        "url": get_record_url(record),
        "created_at": get_record_created_at(record),
        "original_text": str(original_text or "").strip(),
        "clean_text": clean_text,
        "language": "pt",
        "like_count": (
            record.get("comment_likes")
            or record.get("comment_upvotes")
            or record.get("Upvotes")
            or 0
        ),
    }


def clean_records(records, record_type="news", min_chars=30):
    """
    Limpa uma lista de registos.

    record_type pode ser:
    - 'news'
    - 'post'
    - 'comment'

    Devolve:
    - lista de registos limpos
    - lista de registos ignorados
    """
    cleaned_records = []
    skipped_records = []

    for i, record in enumerate(records):
        record_id = generate_record_id(record)

        if record_type == "news":
            cleaned = clean_news_record(record, min_chars=min_chars)

        elif record_type == "post":
            cleaned = clean_post_record(record, min_chars=min_chars)

        elif record_type == "comment":
            cleaned = clean_comment_record(record, min_chars=min_chars)

        else:
            raise ValueError("record_type deve ser 'news', 'post' ou 'comment'.")

        if cleaned is not None:
            cleaned_records.append(cleaned)
        else:
            skipped_records.append({
                "record_id": record_id,
                "index": i,
                "record_type": record_type,
                "reason": "invalid_or_noise_text",
                "original_record": record,
            })

    return cleaned_records, skipped_records


def load_json_file(input_path):
    """
    Carrega um ficheiro JSON.
    Assume que o ficheiro contém uma lista de registos.
    """
    input_path = Path(input_path)

    with open(input_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["data", "records", "items", "results"]:
            if key in data and isinstance(data[key], list):
                return data[key]

    raise ValueError("Formato JSON não reconhecido. Esperava uma lista de registos.")


def save_json_file(data, output_path):
    """
    Guarda uma lista de dicionários num ficheiro JSON.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def clean_json_file(
    input_path,
    output_path,
    skipped_output_path,
    record_type="news",
    min_chars=30
):
    """
    Limpa todos os registos de um ficheiro JSON.
    Esta função é útil para testes, mas reprocessa tudo sempre.
    """
    records = load_json_file(input_path)

    cleaned_records, skipped_records = clean_records(
        records=records,
        record_type=record_type,
        min_chars=min_chars
    )

    save_json_file(cleaned_records, output_path)
    save_json_file(skipped_records, skipped_output_path)

    print("===== LIMPEZA CONCLUÍDA =====")
    print(f"Ficheiro de entrada: {input_path}")
    print(f"Total de registos encontrados: {len(records)}")
    print(f"Registos limpos válidos: {len(cleaned_records)}")
    print(f"Registos ignorados: {len(skipped_records)}")
    print(f"Ficheiro limpo guardado em: {output_path}")
    print(f"Ficheiro de ignorados guardado em: {skipped_output_path}")


def clean_json_file_incremental(input_path, output_path, skipped_output_path, record_type="news", min_chars=30):
    """
    Limpa apenas registos novos.

    Lê:
    - ficheiro original atualizado
    - ficheiro limpo acumulado, se existir
    - ficheiro de ignorados acumulado, se existir

    Guarda:
    - ficheiro limpo acumulado atualizado
    - ficheiro de ignorados acumulado atualizado
    """
    raw_records = load_json_file(input_path)

    unique_raw_records, duplicate_count = remove_duplicate_records(raw_records)

    output_path = Path(output_path)
    skipped_output_path = Path(skipped_output_path)

    if output_path.exists():
        cleaned_records = load_json_file(output_path)
    else:
        cleaned_records = []

    if skipped_output_path.exists():
        skipped_records = load_json_file(skipped_output_path)
    else:
        skipped_records = []

    already_processed_ids = set()

    for record in cleaned_records:
        record_id = record.get("record_id")

        if record_id:
            already_processed_ids.add(record_id)

    for skipped in skipped_records:
        record_id = skipped.get("record_id")

        if not record_id:
            original_record = skipped.get("original_record", {})
            record_id = generate_record_id(original_record)

        if record_id:
            already_processed_ids.add(record_id)

    new_cleaned_records = []
    new_skipped_records = []

    already_processed_count = 0

    for i, record in enumerate(unique_raw_records):
        record_id = generate_record_id(record)

        if record_id in already_processed_ids:
            already_processed_count += 1

            continue

        if record_type == "news":
            cleaned = clean_news_record(record, min_chars=min_chars)

        elif record_type == "post":
            cleaned = clean_post_record(record, min_chars=min_chars)

        elif record_type == "comment":
            cleaned = clean_comment_record(record, min_chars=min_chars)

        else:
            raise ValueError("record_type deve ser 'news', 'post' ou 'comment'.")

        if cleaned is not None:
            new_cleaned_records.append(cleaned)
            already_processed_ids.add(record_id)
        else:
            new_skipped_records.append({
                "record_id": record_id,
                "index": i,
                "record_type": record_type,
                "reason": "invalid_or_noise_text",
                "original_record": record,
            })
            already_processed_ids.add(record_id)

    final_cleaned_records = cleaned_records + new_cleaned_records
    final_skipped_records = skipped_records + new_skipped_records

    save_json_file(final_cleaned_records, output_path)
    save_json_file(final_skipped_records, skipped_output_path)

    print("===== LIMPEZA INCREMENTAL CONCLUÍDA =====")
    print(f"Ficheiro de entrada: {input_path}")
    print(f"Total de registos no ficheiro original: {len(raw_records)}")
    print(f"Duplicados removidos do raw: {duplicate_count}")
    print(f"Registos únicos considerados: {len(unique_raw_records)}")
    print(f"Registos que já estavam processados: {already_processed_count}")
    print(f"Novos registos limpos: {len(new_cleaned_records)}")
    print(f"Novos registos ignorados: {len(new_skipped_records)}")
    print(f"Total acumulado de registos limpos: {len(final_cleaned_records)}")
    print(f"Total acumulado de registos ignorados: {len(final_skipped_records)}")
    print(f"Ficheiro limpo atualizado em: {output_path}")
    print(f"Ficheiro de ignorados atualizado em: {skipped_output_path}")


def clean_multiple_json_files(files_to_clean):
    """
    Limpa vários ficheiros JSON usando a mesma lógica.
    Cada ficheiro pode ter um tipo diferente: news, post ou comment.
    """
    for file_config in files_to_clean:
        input_path = file_config["input_path"]

        if not Path(input_path).exists():
            print("\n" + "=" * 100)
            print(f"FICHEIRO NÃO ENCONTRADO: {input_path}")
            print("Este ficheiro foi ignorado.")
            print("=" * 100)
            continue

        print("\n" + "=" * 100)
        print(f"A PROCESSAR: {input_path}")
        print("=" * 100)

        clean_json_file_incremental(
            input_path=file_config["input_path"],
            output_path=file_config["output_path"],
            skipped_output_path=file_config["skipped_output_path"],
            record_type=file_config["record_type"],
            min_chars=file_config["min_chars"]
        )


def show_examples_from_json(file_path, limit=2):
    """
    Mostra alguns exemplos de um ficheiro JSON no terminal.
    Serve para validares rapidamente os resultados da limpeza.
    """
    if not Path(file_path).exists():
        print(f"Ficheiro não encontrado: {file_path}")
        return

    records = load_json_file(file_path)

    for i, record in enumerate(records[:limit], start=1):
        print("=" * 100)
        print(f"REGISTO {i}")
        print("=" * 100)

        print("\nFONTE:")
        print(record.get("source", ""))

        print("\nAUTOR:")
        print(record.get("author", record.get("author_handle", "")))

        print("\nTÍTULO ORIGINAL:")
        print(record.get("title_original", ""))

        print("\nTÍTULO LIMPO:")
        print(record.get("title_clean", ""))

        print("\nTEXTO LIMPO:")
        print(record.get("clean_text", ""))

        print("\nLIKES/UPVOTES:")
        print(record.get("like_count", ""))

        print("\nRESPOSTAS/COMENTÁRIOS:")
        print(record.get("reply_count", ""))

        print()


if __name__ == "__main__":
    FILES_TO_CLEAN = [
        {
            "input_path": "data/raw/news_posts.json",
            "output_path": "data/clean/news/news_cleaned.json",
            "skipped_output_path": "data/clean/news/news_skipped.json",
            "record_type": "news",
            "min_chars": 30,
        },
        {
            "input_path": "data/raw/bluesky_posts.json",
            "output_path": "data/clean/bluesky/bluesky_cleaned.json",
            "skipped_output_path": "data/clean/bluesky/bluesky_skipped.json",
            "record_type": "post",
            "min_chars": 20,
        },
        {
            "input_path": "data/raw/reddit_posts.json",
            "output_path": "data/clean/reddit/reddit_cleaned.json",
            "skipped_output_path": "data/clean/reddit/reddit_skipped.json",
            "record_type": "post",
            "min_chars": 20,
        },
        {
            "input_path": "data/raw/youtube_posts.json",
            "output_path": "data/clean/youtube/youtube_cleaned.json",
            "skipped_output_path": "data/clean/youtube/youtube_skipped.json",
            "record_type": "post",
            "min_chars": 20,
        },
    ]

    clean_multiple_json_files(FILES_TO_CLEAN)

    print("\n\n===== EXEMPLOS DE NOTÍCIAS LIMPAS =====")
    show_examples_from_json("data/clean/news/news_cleaned.json", limit=3)

    print("\n\n===== EXEMPLOS DE BLUESKY LIMPOS =====")
    show_examples_from_json("data/clean/bluesky/bluesky_cleaned.json", limit=3)

    print("\n\n===== EXEMPLOS DE REDDIT LIMPOS =====")
    show_examples_from_json("data/clean/reddit/reddit_cleaned.json", limit=3)

    print("\n\n===== EXEMPLOS DE YOUTUBE LIMPOS =====")
    show_examples_from_json("data/clean/youtube/youtube_cleaned.json", limit=3)