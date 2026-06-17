import os

tests_dir = "D:/MarketMind Ai/tests"
count = 0
for root, dirs, files in os.walk(tests_dir):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if "from models import" in content:
                new_content = content.replace("from models import", "from app.models import")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"Updated: {file}")
                count += 1
print(f"Total files updated: {count}")
