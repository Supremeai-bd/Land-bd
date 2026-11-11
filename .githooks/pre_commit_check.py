import sys
import subprocess
import os
import re

# Maximum allowed file size for git tracking (in bytes) - 20 MB warning, 50 MB block
MAX_FILE_SIZE = 50 * 1024 * 1024 

# Patterns that indicate sensitive secrets
SECRET_PATTERNS = [
    (r'(?i)CLOUDFLARE_GLOBAL_API_KEY\s*=\s*[a-zA-Z0-9_\-]{20,}', "Cloudflare Global API Key"),
    (r'(?i)CLOUDFLARE_API_TOKEN\s*=\s*[a-zA-Z0-9_\-]{20,}', "Cloudflare API Token"),
    (r'(?i)CLOUDFLARE_R2_SECRET_ACCESS_KEY\s*=\s*[a-zA-Z0-9_\-]{20,}', "R2 Secret Access Key"),
    (r'(?i)ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
    (r'(?i)gho_[a-zA-Z0-9]{36}', "GitHub OAuth Token"),
    (r'(?i)AIza[0-9A-Za-z\-_]{35}', "Google API Key"),
    (r'(?i)sk-proj-[a-zA-Z0-9\-_]{40,}', "OpenAI API Key"),
    (r'(?i)sk-ant-[a-zA-Z0-9\-_]{40,}', "Anthropic API Key"),
    (r'-----BEGIN (RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----', "Private Cryptographic Key"),
]

BLOCKED_FILES = [
    ".env",
    ".env.local",
    "02_BACKUP_AND_RAW_DATA",
    "raipur_cadastre_voters.db",
    "raipur_all_voters.json",
    "raipur_voters_database.js"
]

def get_staged_files():
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    if res.returncode != 0:
        return []
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]

def get_staged_diff(file_path):
    cmd = ["git", "diff", "--cached", "-U0", "--", file_path]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore")
    return res.stdout

def check_security():
    staged_files = get_staged_files()
    if not staged_files:
        sys.exit(0)

    violations = []

    for file_path in staged_files:
        # 1. Check blocked filename
        base_name = os.path.basename(file_path)
        if base_name in BLOCKED_FILES or base_name.endswith(".db") or base_name.endswith(".sqlite"):
            violations.append(f"[BLOCKED FILE] '{file_path}' is a sensitive or raw database file and MUST NOT be committed!")

        # 2. Check file size
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            if size > MAX_FILE_SIZE:
                violations.append(f"[OVERSIZED FILE] '{file_path}' is {size / (1024*1024):.2f} MB (Limit: 50 MB). Use R2 storage instead!")

        # 3. Check staged content for secret leaks (skip example/template files)
        if base_name in [".env.example", "wrangler.toml.example"]:
            continue

        diff_content = get_staged_diff(file_path)
        for line in diff_content.splitlines():
            # Only examine added lines in git diff
            if line.startswith("+") and not line.startswith("+++"):
                for pattern, secret_type in SECRET_PATTERNS:
                    if re.search(pattern, line):
                        violations.append(f"[SECRET DETECTED] Possible {secret_type} in '{file_path}':\n    Line: {line.strip()[:60]}...")

    if violations:
        print("\n" + "="*70)
        print("🚨 COMMIT REJECTED: PRE-COMMIT SECURITY VIOLATION DETECTED!")
        print("="*70)
        for v in violations:
            print(f"❌ {v}")
        print("\nAction required:")
        print("  - Remove sensitive credentials or oversized files before committing.")
        print("  - Make sure secrets are kept only in your local '.env' file.")
        print("="*70 + "\n")
        sys.exit(1)

    print("🛡️  Pre-commit Security Check: Passed successfully (No secrets or oversized files).")
    sys.exit(0)

if __name__ == "__main__":
    check_security()

