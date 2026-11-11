with open(r"F:\khotiyan book\deploy_to_cloudflare.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines[310:330]):
    print(f"{i+311}: {repr(l)}")
