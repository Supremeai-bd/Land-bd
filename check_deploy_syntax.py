import os

base_dir = os.path.dirname(os.path.abspath(__file__))
target_file = os.path.join(base_dir, "deploy_to_cloudflare.py")

with open(target_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, l in enumerate(lines[310:330]):
    print(f"{i+311}: {repr(l)}")
