import os
import sys
import boto3
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).parent

# ficheiros a descarregar do R2
R2_FILES = [
    "data/raw/news_posts.json",
    "data/raw/reddit_posts.json",
    "data/raw/bluesky_posts.json",
    "data/raw/youtube_posts.json",
]

# scripts a correr por ordem
PIPELINE_STEPS = [
    {
        "name": "Limpeza de texto",
        "script": BASE_DIR / "analysis/text_cleaning.py",
    },
    {
        "name": "Extração de keywords",
        "script": BASE_DIR / "analysis/keywords_extraction.py",
    },
    {
        "name": "Análise de sentimentos",
        "script": BASE_DIR / "analysis/sentiment_analysis.py",
    },
    {
        "name": "Análise de emoções",
        "script": BASE_DIR / "analysis/emotion_analysis.py",
    },
    {
        "name": "Extração de entidades (NER)",
        "script": BASE_DIR / "analysis/ner_extraction.py",
    },
    {
        "name": "Cruzamento multimodal (merge)",
        "script": BASE_DIR / "merge.py",
    },
]


# ============================================================
# R2
# ============================================================

def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("R2_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def download_from_r2():
    print("=" * 60)
    print("A DESCARREGAR DADOS DO R2")
    print("=" * 60)

    client = get_r2_client()
    bucket = os.getenv("R2_BUCKET_NAME")

    downloaded = 0
    skipped = 0

    for file_path in R2_FILES:
        local_path = BASE_DIR / file_path

        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # verificar tamanho do ficheiro no R2
            response = client.head_object(
                Bucket=bucket,
                Key=file_path,
            )
            r2_size = response["ContentLength"]

            # verificar se ficheiro local existe e tem o mesmo tamanho
            if local_path.exists():
                local_size = local_path.stat().st_size
                if local_size == r2_size:
                    print(f"SEM ALTERAÇÕES: {file_path}")
                    skipped += 1
                    continue

            # descarregar ficheiro
            client.download_file(
                bucket,
                file_path,
                str(local_path),
            )
            print(f"DOWNLOAD OK: {file_path}")
            downloaded += 1

        except client.exceptions.NoSuchKey:
            print(f"AVISO: {file_path} não encontrado no R2")
        except Exception as e:
            print(f"ERRO ao descarregar {file_path}: {e}")

    print(f"\nDescarregados: {downloaded}")
    print(f"Sem alterações: {skipped}")

    return downloaded


# ============================================================
# EXECUTAR SCRIPTS
# ============================================================

def run_script(name, script_path):
    print(f"\n{'=' * 60}")
    print(f"A CORRER: {name}")
    print(f"{'=' * 60}")

    if not script_path.exists():
        print(f"ERRO: script não encontrado -> {script_path}")
        return False

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(BASE_DIR),
    )

    if result.returncode != 0:
        print(f"ERRO: {name} falhou com código {result.returncode}")
        return False

    print(f"OK: {name} concluído")
    return True


# ============================================================
# MAIN
# ============================================================

def main():
    print("\n")
    print("=" * 60)
    print("MUNICIPAL SENTIMENT PIPELINE")
    print("=" * 60)

    # ========================================================
    # DOWNLOAD DO R2
    # ========================================================

    downloaded = download_from_r2()

    if downloaded == 0:
        print("\nNenhum ficheiro novo no R2.")
        print("Pipeline terminado sem processamento.")
        return

    # ========================================================
    # PIPELINE DE ANÁLISE
    # ========================================================

    print(f"\n{downloaded} ficheiro(s) novo(s) — a iniciar pipeline")

    failed = []

    for step in PIPELINE_STEPS:
        success = run_script(step["name"], step["script"])
        if not success:
            failed.append(step["name"])

    # ========================================================
    # RESUMO
    # ========================================================

    print("\n")
    print("=" * 60)
    print("PIPELINE CONCLUÍDO")
    print("=" * 60)

    total = len(PIPELINE_STEPS)
    succeeded = total - len(failed)

    print(f"Passos concluídos: {succeeded}/{total}")

    if failed:
        print(f"Passos com erro:")
        for step in failed:
            print(f"  - {step}")
        print("\nVerifica os erros acima antes de correr o db_insert.py")
    else:
        print("\nTodos os passos concluídos com sucesso.")
        print("Podes agora correr o db_insert.py para inserir na BD.")


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    main()