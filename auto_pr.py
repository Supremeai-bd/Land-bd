import sys
import subprocess
import re

def run_command(cmd, shell=False):
    res = subprocess.run(cmd, shell=shell, text=True, capture_output=True, encoding="utf-8", errors="replace")
    return res.returncode, res.stdout.strip(), res.stderr.strip()

def main():
    print("=" * 70)
    print("   SupremeAI Land-bd: Automated Git Branch, Commit & Pull Request")
    print("=" * 70)
    print()

    # 1. Check git and gh
    rc, _, _ = run_command(["git", "--version"])
    if rc != 0:
        print("[ERROR] Git is not installed or not in PATH!")
        input("\nPress Enter to exit...")
        sys.exit(1)

    rc, _, _ = run_command(["gh", "--version"])
    if rc != 0:
        print("[ERROR] GitHub CLI (gh) is not installed or not in PATH!")
        input("\nPress Enter to exit...")
        sys.exit(1)

    # 2. Check changes
    print("[INFO] Local modified/added files:")
    rc, out, _ = run_command(["git", "status", "--short"])
    if out:
        print(out)
    else:
        print("  (No modified files detected)")
    print()

    # 3. Prompt user
    try:
        user_input = input("Enter Task / Feature Name (e.g. khatian search speed optimization): ").strip()
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)

    if not user_input:
        print("[ERROR] Task name cannot be empty!")
        input("\nPress Enter to exit...")
        sys.exit(1)

    # Convert to clean branch slug
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', user_input).strip('-').lower()
    if not slug:
        slug = "feature-patch"

    print("\n" + "=" * 70)
    print(f"  Branch Name : {slug}")
    print(f"  Commit / PR : {user_input}")
    print("=" * 70 + "\n")

    # 4. Git checkout -b
    print(f"[1/4] Switching to branch '{slug}'...")
    rc, _, _ = run_command(["git", "checkout", "-b", slug])
    if rc != 0:
        run_command(["git", "checkout", slug])

    # 5. Git add .
    print("[2/4] Staging files...")
    run_command(["git", "add", "."])

    # 6. Git commit
    print("[3/4] Committing changes (Running Pre-commit Security Checks)...")
    rc, cout, cerr = run_command(["git", "commit", "-m", user_input])
    if rc != 0:
        print("\n[ERROR] Commit failed or rejected by security checks!")
        if cout: print(cout)
        if cerr: print(cerr)
        input("\nPress Enter to exit...")
        sys.exit(1)
    else:
        if cout: print(cout)

    # 7. Git push
    print(f"\n[4/4] Pushing branch '{slug}' to GitHub...")
    rc, pout, perr = run_command(["git", "push", "-u", "origin", slug])
    if rc != 0:
        print(f"\n[ERROR] Git push failed:\n{perr or pout}")
        input("\nPress Enter to exit...")
        sys.exit(1)

    # 8. GitHub PR
    print("[INFO] Creating Pull Request against 'main'...")
    rc, pr_out, pr_err = run_command([
        "gh", "pr", "create",
        "--title", user_input,
        "--body", f"Automated Pull Request for: **{user_input}**",
        "--base", "main",
        "--head", slug
    ])

    if rc == 0:
        print("\n" + "=" * 70)
        print("  🎉 SUCCESS: Branch pushed and Pull Request created successfully!")
        print(f"  PR Link: {pr_out}")
        print("=" * 70)
    else:
        print(f"\n[INFO] {pr_err or pr_out}")

    print()
    input("Press Enter to finish...")

if __name__ == "__main__":
    main()
