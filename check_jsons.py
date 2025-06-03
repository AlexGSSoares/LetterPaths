# check_jsons.py

import os
import sys
import json
import matplotlib.pyplot as plt

# ─── CONFIGURAÇÃO ────────────────────────────────────────────────────────────────
# Base onde estão as duas subpastas “upper” e “lower”
BASE_JSON_DIR = "./assets"
SUBFOLDERS   = ["upper", "lower"]
# ───────────────────────────────────────────────────────────────────────────────


def list_all_jsons():
    """
    Percorre todas as subpastas em BASE_JSON_DIR (por padrão “upper” e “lower”)
    e retorna uma lista de tuplas (letra, full_path).
    - A letra é obtida a partir do nome do arquivo, antes de "_PointsInfo.json".
    """
    result = []
    for sub in SUBFOLDERS:
        dir_path = os.path.join(BASE_JSON_DIR, sub)
        if not os.path.isdir(dir_path):
            continue
        for fn in sorted(os.listdir(dir_path)):
            if fn.endswith("_PointsInfo.json"):
                # Exemplo de fn: "A_PointsInfo.json" ou "e_PointsInfo.json"
                letra = fn.split("_")[0]
                full_path = os.path.join(dir_path, fn)
                result.append((letra, full_path))
    return result


def plot_json(path: str):
    """
    Lê o arquivo JSON em `path` e plota cada stroke (cada lista de pontos)
    exatamente na mesma orientação em que estão no JSON, sem inverter o eixo Y.
    As coordenadas dentro do JSON já estão normalizadas em [0..1], então
    aqui simplesmente desenhamos (x, y) em um gráfico de proporção 1:1.
    """
    # Carrega
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    char = data.get("char", "?")
    strokes = data.get("strokes", [])

    plt.figure(figsize=(4,4))
    # Para cada stroke, extraímos a lista de strings “x_norm,y_norm”
    for stroke in strokes:
        raw_points = stroke.get("points", [])
        pontos = [tuple(map(float, p.split(","))) for p in raw_points]
        if not pontos:
            continue
        xs, ys = zip(*pontos)
        # Desenha linhas conectando cada ponto na ordem
        plt.plot(xs, ys, marker="o", linewidth=1, markersize=4)

    # Configurações finais: manter proporção 1:1, exibir título e ocultar eixos
    plt.title(f"Letra (campo 'char') = '{char}'\nJSON = {os.path.basename(path)}")
    plt.gca().set_aspect("equal", adjustable="box")
    plt.axis("off")
    plt.tight_layout()
    plt.show()


def main():
    # 1) Descobre todos os JSONs disponíveis
    all_jsons = list_all_jsons()
    if not all_jsons:
        print(f"Não foram encontrados arquivos em '{BASE_JSON_DIR}/upper' ou '/lower'.")
        return

    # 2) Se houver um argumento de linha de comando, interpretamos como
    #    i) nome de letra (por exemplo "A" ou "e")
    #   ii) nome exato de arquivo JSON (por exemplo "A_PointsInfo.json")
    if len(sys.argv) == 2:
        arg = sys.argv[1]
        # 2.1) Verifica se corresponde a alguma letra
        matches = [path for (ltr, path) in all_jsons if ltr == arg]
        if matches:
            plot_json(matches[0])
            return

        # 2.2) Verifica se corresponde a algum nome de arquivo exato
        matches = [path for (_, path) in all_jsons
                   if os.path.basename(path) == arg]
        if matches:
            plot_json(matches[0])
            return

        print(f"Argumento '{arg}' não corresponde a nenhuma letra nem arquivo JSON encontrado.")
        return

    # 3) Se não for passado argumento, mostra menu interativo
    print("Arquivos JSON disponíveis:")
    for idx, (ltr, path) in enumerate(all_jsons, start=1):
        nome_arquivo = os.path.basename(path)
        print(f"  {idx:2d}. Letra = '{ltr}'\tarquivo: {nome_arquivo}")

    try:
        choice = int(input("\nDigite o número da letra que deseja visualizar: "))
        if 1 <= choice <= len(all_jsons):
            _, selected_path = all_jsons[choice-1]
            plot_json(selected_path)
        else:
            print("Escolha inválida (fora do intervalo).")
    except ValueError:
        print("Entrada inválida. Por favor, digite um número correspondente à lista.")


if __name__ == "__main__":
    main()
