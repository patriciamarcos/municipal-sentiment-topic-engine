import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

BASE_DIR = Path(__file__).parent

# ============================================================
# CONFIGURAÇÃO
# ============================================================

UMAP_COORDS_FILE = BASE_DIR / "data/topics/umap_coords.json"
TOPIC_INFO_FILE  = BASE_DIR / "data/topics/topic_info.json"
OUTPUT_FILE      = BASE_DIR / "data/topics/topic_visualization.png"

COLORS = [
    "#4C6EF5", "#F59F00", "#2F9E44", "#E03131", "#7950F2",
    "#0C8599", "#D6336C", "#5C940D", "#E8590C", "#1971C2",
    "#862E9C", "#087F5B", "#C92A2A", "#364FC7", "#A61E4D",
    "#5F3DC4", "#0B7285", "#2B8A3E", "#E67700", "#748FFC",
]

OUTLIER_COLOR = "#000000"

# ============================================================
# JSON
# ============================================================

def load_json(path):
    path = Path(path)
    if not path.exists():
        print(f"AVISO: ficheiro não encontrado -> {path}")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ============================================================
# MAIN
# ============================================================

def main():
    print("A CARREGAR DADOS")

    coords_data = load_json(UMAP_COORDS_FILE)
    topic_info  = load_json(TOPIC_INFO_FILE)

    print(f"Documentos com coordenadas: {len(coords_data)}")

    topic_info_map = {
        t["Topic"]: t.get("Representation", [])
        for t in topic_info
        if t["Topic"] != -1
    }

    # extrair arrays
    xs        = np.array([r["x"] for r in coords_data])
    ys        = np.array([r["y"] for r in coords_data])
    topic_ids = [r["topic_id"] for r in coords_data]

    unique_topics = sorted(set(topic_ids))

    # mapa de cores
    color_map = {}
    color_idx = 0
    for t in unique_topics:
        if t == -1:
            color_map[t] = OUTLIER_COLOR
        else:
            color_map[t] = COLORS[color_idx % len(COLORS)]
            color_idx += 1

    # ========================================================
    # PLOT
    # ========================================================

    print("A gerar visualização")

    fig, ax = plt.subplots(figsize=(14, 8), dpi=150)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#F8F9FA")

    # outliers primeiro
    outlier_mask = np.array([t == -1 for t in topic_ids])
    if outlier_mask.any():
        ax.scatter(
            xs[outlier_mask], ys[outlier_mask],
            c=OUTLIER_COLOR, s=20, alpha=0.35,
            linewidths=0, zorder=1,
        )

    # tópicos
    for topic_id in unique_topics:
        if topic_id == -1:
            continue

        mask = np.array([t == topic_id for t in topic_ids])
        x    = xs[mask]
        y    = ys[mask]
        col  = color_map[topic_id]

        ax.scatter(x, y, c=col, s=40, alpha=0.75, linewidths=0, zorder=2)

        # label no centroide
        cx, cy = np.median(x), np.median(y)
        ax.text(
            cx, cy, f"T{topic_id}",
            fontsize=10, fontweight="bold",
            ha="center", va="center", color="white",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor=col,
                edgecolor="none",
                alpha=0.92,
            ),
            zorder=3,
        )

    # ========================================================
    # LEGENDA
    # ========================================================

    legend_patches = []
    for topic_id in sorted([t for t in unique_topics if t != -1]):
        rep   = topic_info_map.get(topic_id, [])
        label = ", ".join(rep[:3]) if rep else f"Tópico {topic_id}"
        legend_patches.append(mpatches.Patch(
            color=color_map[topic_id],
            label=f"T{topic_id}: {label}",
        ))
    legend_patches.append(mpatches.Patch(
        color=OUTLIER_COLOR,
        label="Outliers (sem tópico)",
    ))

    ax.legend(
        handles=legend_patches,
        loc="lower right",
        borderaxespad=1,
        fontsize=8,
        framealpha=0.9,
        edgecolor="#DEE2E6",
        title="Tópicos identificados",
        title_fontsize=9,
    )

    ax.set_xlabel("UMAP dimensão 1", fontsize=10, color="#495057")
    ax.set_ylabel("UMAP dimensão 2", fontsize=10, color="#495057")
    ax.set_title(
        "Projeção UMAP dos documentos por tópico (BERTopic)",
        fontsize=13, fontweight="bold", color="#212529", pad=14,
    )

    ax.tick_params(colors="#ADB5BD", labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor("#DEE2E6")
    ax.grid(True, color="#DEE2E6", linewidth=0.5, alpha=0.6)

    plt.tight_layout()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()

    print(f"\nGuardado em: {OUTPUT_FILE}")
    print("VISUALIZAÇÃO TERMINADA")


if __name__ == "__main__":
    main()