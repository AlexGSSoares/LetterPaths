import os, json
import matplotlib.pyplot as plt

# Ajuste para a pasta onde estão seus JSONs
JSON_DIR = "./points_info"

for fn in sorted(os.listdir(JSON_DIR)):
    if not fn.endswith("_PointsInfo.json"):
        continue
    data = json.load(open(os.path.join(JSON_DIR, fn), encoding="utf-8"))
    char = data["char"]
    plt.figure(figsize=(2,2))
    for stroke in data["strokes"]:
        pts = [tuple(map(float,p.split(","))) for p in stroke["points"]]
        xs, ys = zip(*pts)
        plt.plot(xs, ys, marker="o")   # plota pontos e linhas
    plt.title(f"Letra: {char}")
    plt.axis("equal")
    plt.axis("off")
    plt.show()
