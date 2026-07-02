import boto3
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURAÇÃO
# ============================================================

R2_ACCESS_KEY_ID     = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_ENDPOINT_URL      = os.getenv("R2_ENDPOINT_URL")
R2_BUCKET_NAME       = os.getenv("R2_BUCKET_NAME")


# ============================================================
# LIGAÇÃO
# ============================================================

def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


# ============================================================
# TESTE
# ============================================================

def main():
    print("A testar ligação ao Cloudflare R2")
    print(f"Bucket: {R2_BUCKET_NAME}")
    print(f"Endpoint: {R2_ENDPOINT_URL}")

    client = get_r2_client()

    # ========================================================
    # TESTE 1 — LISTAR FICHEIROS
    # ========================================================

    print("\n1. A listar ficheiros no bucket...")

    try:
        response = client.list_objects_v2(Bucket=R2_BUCKET_NAME)
        objects = response.get("Contents", [])
        print(f"   Ficheiros encontrados: {len(objects)}")
        for obj in objects:
            print(f"   - {obj['Key']} ({obj['Size']} bytes)")

    except Exception as e:
        print(f"   ERRO: {e}")
        return

    # ========================================================
    # TESTE 2 — UPLOAD
    # ========================================================

    print("\n2. A fazer upload de ficheiro de teste...")

    test_content = '{"test": "hello from pipeline"}'

    try:
        client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key="test/test_file.json",
            Body=test_content.encode("utf-8"),
            ContentType="application/json",
        )
        print("   Upload OK")

    except Exception as e:
        print(f"   ERRO: {e}")
        return

    # ========================================================
    # TESTE 3 — DOWNLOAD
    # ========================================================

    print("\n3. A fazer download do ficheiro de teste...")

    try:
        response = client.get_object(
            Bucket=R2_BUCKET_NAME,
            Key="test/test_file.json",
        )
        content = response["Body"].read().decode("utf-8")
        print(f"   Download OK")
        print(f"   Conteúdo: {content}")

    except Exception as e:
        print(f"   ERRO: {e}")
        return

    # ========================================================
    # TESTE 4 — APAGAR FICHEIRO DE TESTE
    # ========================================================

    print("\n4. A apagar ficheiro de teste...")

    try:
        client.delete_object(
            Bucket=R2_BUCKET_NAME,
            Key="test/test_file.json",
        )
        print("   Apagado OK")

    except Exception as e:
        print(f"   ERRO: {e}")
        return

    print("\nLIGAÇÃO AO R2 OK — tudo a funcionar corretamente")


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    main()