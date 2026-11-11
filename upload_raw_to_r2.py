"""
================================================================================
Raipur Land Cadastre - Automated Cloudflare R2 Upload Script
================================================================================
Purpose:
  Upload heavy raw files (291 Survey PDFs, 552 Voter PDFs, Master JSONs, 
  and JS databases) to Cloudflare R2 Storage using S3-compatible API (boto3).
  Enables external AI providers (Gemini, Claude, OpenAI) to access raw files
  via high-speed, zero-egress cloud storage.
================================================================================
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError:
    print("[!] Error: 'boto3' is required. Install via: pip install boto3")
    sys.exit(1)

# Load configuration from .env
load_dotenv()

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY")
BUCKET_NAME = os.getenv("CLOUDFLARE_R2_BUCKET_NAME", "raipur-land-raw-data")
PUBLIC_DOMAIN = os.getenv("CLOUDFLARE_R2_PUBLIC_DOMAIN", "") # e.g. "https://data.supremeai.bd" or pub-xxx.r2.dev

ENDPOINT_URL = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"

def get_r2_client():
    if not ACCOUNT_ID or not R2_ACCESS_KEY_ID or not R2_SECRET_ACCESS_KEY:
        print("\n" + "="*70)
        print("⚠️  MISSING R2 CREDENTIALS IN .env")
        print("="*70)
        print("Please add the following variables to your .env file:")
        print("  CLOUDFLARE_R2_ACCESS_KEY_ID=your_r2_access_key_id")
        print("  CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_r2_secret_access_key")
        print("  CLOUDFLARE_R2_BUCKET_NAME=raipur-land-raw-data")
        print("  CLOUDFLARE_R2_PUBLIC_DOMAIN=https://your-public-bucket-domain (Optional)")
        print("\nHow to get R2 API Token:")
        print("1. Go to Cloudflare Dashboard -> R2 Object Storage")
        print("2. Click 'Manage R2 API Tokens' -> 'Create API Token'")
        print("3. Permissions: Object Read & Write")
        print("4. Copy 'Access Key ID' and 'Secret Access Key'")
        print("="*70 + "\n")
        return None

    return boto3.client(
        service_name="s3",
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4", retries={"max_attempts": 5, "mode": "adaptive"}),
        region_name="auto"
    )

def ensure_bucket_exists(client, bucket_name):
    try:
        client.head_bucket(Bucket=bucket_name)
        print(f"[✓] Bucket '{bucket_name}' exists.")
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code in ["404", "NoSuchBucket"]:
            print(f"[+] Creating bucket '{bucket_name}'...")
            try:
                client.create_bucket(Bucket=bucket_name)
                print(f"[✓] Bucket '{bucket_name}' created successfully.")
                return True
            except Exception as ce:
                print(f"[!] Failed to create bucket: {ce}")
                return False
        else:
            print(f"[!] Head bucket error: {e}")
            return False

def get_existing_objects(client, bucket_name):
    """Returns a dict of {key: size} of all existing items in R2 bucket."""
    existing = {}
    paginator = client.get_paginator("list_objects_v2")
    try:
        for page in paginator.paginate(Bucket=bucket_name):
            for obj in page.get("Contents", []):
                existing[obj["Key"]] = obj["Size"]
    except Exception as e:
        print(f"[!] Warning: Could not list existing objects: {e}")
    return existing

def collect_target_files(include_sensitive=False):
    """Return public-safe files by default; PII sources require explicit safeguards."""
    base_dir = Path(".").resolve()
    targets = []

    # Registry rates are public/reference material. Citizen and land records are
    # deliberately excluded from the default upload set.
    rates = base_dir / "raipur_registry_rates_2025_2026.json"
    if rates.is_file():
        targets.append((rates, "public/raipur_registry_rates_2025_2026.json"))
    if not include_sensitive:
        return targets

    # 1. Partitioned AI-Ready Data (khatians, voters, manifest)
    data_dir = base_dir / "data"
    if data_dir.exists():
        for file_path in data_dir.rglob("*"):
            if file_path.is_file():
                rel_key = str(file_path.relative_to(base_dir)).replace("\\", "/")
                targets.append((file_path, rel_key))

    # 2. 02_BACKUP_AND_RAW_DATA Directory (all files)
    raw_dir = base_dir / "02_BACKUP_AND_RAW_DATA"
    if raw_dir.exists():
        for file_path in raw_dir.rglob("*"):
            if file_path.is_file():
                rel_key = str(file_path.relative_to(base_dir)).replace("\\", "/")
                targets.append((file_path, rel_key))

    # 2. Root heavy files (databases & large json files)
    root_files = [
        "raipur_cadastre_voters.db",
        "raipur_all_voters.json",
        "raipur_master_khatians.json",
        "raipur_voters_database.js",
        "raipur_full_database.js",
        "core_7_database.js",
        "raipur_registry_rates_2025_2026.json"
    ]
    for rf in root_files:
        p = base_dir / rf
        if p.exists() and p.is_file():
            # Avoid duplicate if already added
            key = f"raw_root/{rf}"
            targets.append((p, key))

    return targets

def upload_files(client, bucket_name, include_sensitive=False):
    if not ensure_bucket_exists(client, bucket_name):
        return

    print("[*] Fetching existing files in bucket to avoid re-uploading...")
    existing = get_existing_objects(client, bucket_name)
    print(f"[✓] Found {len(existing)} existing files in bucket.")

    targets = collect_target_files(include_sensitive=include_sensitive)
    total_files = len(targets)
    total_bytes = sum(p.stat().st_size for p, _ in targets)

    print("\n" + "="*70)
    print(f"📊 SUMMARY OF FILES TO SYNC:")
    print(f"   Total Files: {total_files}")
    print(f"   Total Size : {total_bytes / (1024*1024):.2f} MB (~{total_bytes / (1024*1024*1024):.2f} GB)")
    print("="*70)

    uploaded_count = 0
    skipped_count = 0
    failed_count = 0
    start_time = time.time()

    for idx, (path, key) in enumerate(targets, 1):
        file_size = path.stat().st_size
        size_mb = file_size / (1024 * 1024)

        if file_size > 50 * 1024 * 1024:
            print(f"[SKIP] {key} ({size_mb:.2f} MB) exceeds 50MB limit; skipping upload.")
            skipped_count += 1
            continue

        # Check if already uploaded with same size
        if key in existing and existing[key] == file_size:
            print(f"[{idx}/{total_files}] ⏩ Skipped (Already in R2): {key}")
            skipped_count += 1
            continue

        print(f"[{idx}/{total_files}] ⬆️  Uploading ({size_mb:.2f} MB): {key} ...")
        try:
            extra_args = {}
            if path.suffix.lower() == ".pdf":
                extra_args["ContentType"] = "application/pdf"
            elif path.suffix.lower() == ".json":
                extra_args["ContentType"] = "application/json"
            elif path.suffix.lower() == ".js":
                extra_args["ContentType"] = "application/javascript"

            client.upload_file(str(path), bucket_name, key, ExtraArgs=extra_args)
            uploaded_count += 1
        except Exception as e:
            print(f"[{idx}/{total_files}] ❌ Failed: {key} -> {e}")
            failed_count += 1

    elapsed = time.time() - start_time
    print("\n" + "="*70)
    print("🎉 SYNC COMPLETED!")
    print(f"   Uploaded: {uploaded_count} files")
    print(f"   Skipped : {skipped_count} files (already up-to-date)")
    print(f"   Failed  : {failed_count} files")
    print(f"   Time Taken: {elapsed:.1f} seconds")
    print("="*70)

    if include_sensitive:
        print("Sensitive files were uploaded only after explicit private-bucket confirmation.")

def generate_presigned_url(client, bucket_name, key, expires_in=3600):
    """Generate a temporary URL for AI providers to fetch private files."""
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": key},
            ExpiresIn=expires_in
        )
        return url
    except Exception as e:
        print(f"[!] Error generating presigned URL: {e}")
        return None

if __name__ == "__main__":
    include_sensitive = "--include-sensitive" in sys.argv
    confirm_private = "--confirm-private-bucket" in sys.argv
    if include_sensitive and (PUBLIC_DOMAIN or not confirm_private):
        print("ERROR: refusing sensitive-data upload: remove the public-domain setting and pass --confirm-private-bucket only after verifying bucket access is private.")
        sys.exit(2)
    print("🚀 Initializing Cloudflare R2 Raw Data Sync...")
    client = get_r2_client()
    if client:
        upload_files(client, BUCKET_NAME, include_sensitive=include_sensitive)

