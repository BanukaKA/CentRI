"""Generate the research-backed CentRI architecture Excalidraw artifact.

Run from the repository root:
    python scripts/generate_architecture_diagram.py

The generated file is intentionally self-contained so it can be opened directly
in Excalidraw or imported into compatible editors.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUT = Path(__file__).resolve().parents[1] / "docs" / "centri-architecture.excalidraw"

NAVY = "#20304a"
INK = "#243247"
MUTED = "#64748b"
BLUE = "#3b82f6"
BLUE_FILL = "#dbeafe"
TEAL = "#0f766e"
TEAL_FILL = "#ccfbf1"
PURPLE = "#7c3aed"
PURPLE_FILL = "#ede9fe"
AMBER = "#d97706"
AMBER_FILL = "#fef3c7"
GREEN = "#16a34a"
GREEN_FILL = "#dcfce7"
RED = "#dc2626"
RED_FILL = "#fee2e2"
SLATE_FILL = "#f1f5f9"
WHITE = "#ffffff"


class Diagram:
    def __init__(self) -> None:
        self.elements: list[dict[str, Any]] = []
        self.counter = 0

    def _id(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}-{self.counter:03d}"

    def _base(self, element_id: str, kind: str, x: float, y: float, w: float, h: float) -> dict[str, Any]:
        return {
            "id": element_id,
            "type": kind,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "angle": 0,
            "strokeColor": INK,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "index": None,
            "roundness": {"type": 3} if kind == "rectangle" else None,
            "seed": self.counter * 7919,
            "version": 1,
            "versionNonce": self.counter * 104729,
            "isDeleted": False,
            "boundElements": [],
            "updated": 1,
            "link": None,
            "locked": False,
        }

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: str = WHITE,
        stroke: str = INK,
        radius: bool = True,
    ) -> str:
        element_id = self._id("rect")
        item = self._base(element_id, "rectangle", x, y, w, h)
        item["backgroundColor"] = fill
        item["strokeColor"] = stroke
        if not radius:
            item["roundness"] = None
        self.elements.append(item)
        return element_id

    def ellipse(self, x: float, y: float, w: float, h: float, fill: str, stroke: str = INK) -> str:
        element_id = self._id("ellipse")
        item = self._base(element_id, "ellipse", x, y, w, h)
        item["backgroundColor"] = fill
        item["strokeColor"] = stroke
        item["roundness"] = None
        self.elements.append(item)
        return element_id

    def text(
        self,
        x: float,
        y: float,
        content: str,
        size: int = 18,
        color: str = INK,
        width: float | None = None,
        bold: bool = False,
        align: str = "left",
    ) -> str:
        element_id = self._id("text")
        lines = content.splitlines() or [""]
        estimated_width = width or max(80, min(1250, max(len(line) for line in lines) * size * 0.54))
        height = max(size * 1.35, len(lines) * size * 1.35)
        item = self._base(element_id, "text", x, y, estimated_width, height)
        item.update(
            {
                "text": content,
                "originalText": content,
                "fontSize": size,
                "fontFamily": 1,
                "textAlign": align,
                "verticalAlign": "top",
                "containerId": None,
                "originalText": content,
                "autoResize": True,
                "lineHeight": 1.25,
                "strokeColor": color,
                "backgroundColor": "transparent",
                "fontWeight": "700" if bold else "400",
            }
        )
        self.elements.append(item)
        return element_id

    def arrow(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: str = NAVY,
        dashed: bool = False,
        label: str | None = None,
    ) -> str:
        element_id = self._id("arrow")
        item = self._base(element_id, "arrow", x1, y1, x2 - x1, y2 - y1)
        item.update(
            {
                "points": [[0, 0], [x2 - x1, y2 - y1]],
                "lastCommittedPoint": None,
                "startBinding": None,
                "endBinding": None,
                "startArrowhead": None,
                "endArrowhead": "triangle",
                "strokeColor": color,
                "strokeStyle": "dashed" if dashed else "solid",
                "roundness": {"type": 2},
            }
        )
        self.elements.append(item)
        if label:
            self.text((x1 + x2) / 2 - len(label) * 3, (y1 + y2) / 2 - 18, label, 14, color, bold=True)
        return element_id

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str = MUTED, dashed: bool = False) -> str:
        element_id = self._id("line")
        item = self._base(element_id, "line", x1, y1, x2 - x1, y2 - y1)
        item.update(
            {
                "points": [[0, 0], [x2 - x1, y2 - y1]],
                "lastCommittedPoint": None,
                "strokeColor": color,
                "strokeStyle": "dashed" if dashed else "solid",
                "roundness": None,
            }
        )
        self.elements.append(item)
        return element_id


def build() -> dict[str, Any]:
    d = Diagram()

    # Canvas title and framing.
    d.rect(0, 0, 2400, 2600, "#fbfdff", "#d8e1ec", radius=False)
    d.text(90, 65, "CentRI / Central Routing Intelligence", 34, NAVY, bold=True)
    d.text(
        92,
        118,
        "A semantic API gateway for large agent catalogs — compile knowledge offline, route by retrieval, reason only over ambiguity",
        19,
        MUTED,
        width=1700,
    )
    d.text(1920, 73, "ARCHITECTURE + THEORY", 13, PURPLE, width=350, bold=True, align="right")
    d.text(1920, 98, "Research snapshot · Sep 2026", 13, MUTED, width=350, align="right")
    d.line(90, 163, 2310, 163, "#cbd5e1")

    # Thesis ribbon.
    d.rect(90, 190, 2220, 105, NAVY, NAVY)
    d.text(
        125,
        215,
        "CORE THESIS",
        14,
        "#93c5fd",
        width=190,
        bold=True,
    )
    d.text(
        315,
        208,
        "Move the growing agent catalog out of the request-time prompt.",
        25,
        WHITE,
        width=920,
        bold=True,
    )
    d.text(
        315,
        246,
        "Pay compilation cost when agents change; pay a bounded retrieval + disambiguation cost per request.",
        17,
        "#dbeafe",
        width=1450,
    )

    # Legend.
    d.rect(1830, 210, 430, 70, "#ffffff", "#cbd5e1")
    d.text(1850, 222, "Legend", 14, NAVY, bold=True)
    d.rect(1955, 223, 18, 18, BLUE_FILL, BLUE)
    d.text(1981, 220, "implemented PoC", 13, INK, width=120)
    d.rect(2110, 223, 18, 18, AMBER_FILL, AMBER)
    d.text(2136, 220, "configured / target", 13, INK, width=120)
    d.rect(1955, 251, 18, 18, RED_FILL, RED)
    d.text(1981, 248, "missing / risk", 13, INK, width=120)
    d.rect(2110, 251, 18, 18, PURPLE_FILL, PURPLE)
    d.text(2136, 248, "theory / evidence", 13, INK, width=120)

    # Section 1: offline compiler.
    d.text(90, 335, "01  OFFLINE COMPILATION  /  turn agent schemas into a routing memory", 22, NAVY, bold=True)
    d.rect(90, 380, 2220, 350, BLUE_FILL, BLUE)
    d.text(120, 402, "Runs when an agent is added, changed, or removed — not for every user request", 15, BLUE, bold=True)

    # Offline flow cards.
    cards = [
        (120, 450, 250, 205, "Agent catalog", "sample_agent_router_dataset.json\n10 synthetic agents\n38 declared tools\n20 golden cases", TEAL_FILL, TEAL),
        (405, 450, 250, 205, "Routing compiler", "routing cards\nexamples + exclusions\nadjacent-agent peers\nhard-negative prompt", PURPLE_FILL, PURPLE),
        (690, 450, 250, 205, "Synthetic expansion", "Nebius chat JSON\nup to 50 utterances / agent\noptional Tavily freshness\ncontext for timely domains", AMBER_FILL, AMBER),
        (975, 450, 250, 205, "Vectorization", "Nebius embeddings\nbatch size 32\nnormalize vectors\nsame model at runtime", BLUE_FILL, BLUE),
        (1260, 450, 250, 205, "Vector index", "current: FAISS\nIndexFlatIP exact search\ncosine-style similarity\nfuture: HNSW / IVF-PQ", GREEN_FILL, GREEN),
        (1545, 450, 345, 205, "Compiled routing memory", "faiss.index\nvectors.jsonl\nsynthetic_queries.json\nagent_id ↔ example mapping", TEAL_FILL, TEAL),
    ]
    for x, y, w, h, title, body, fill, stroke in cards:
        d.rect(x, y, w, h, fill, stroke)
        d.text(x + 18, y + 18, title, 17, stroke, width=w - 36, bold=True)
        d.text(x + 18, y + 55, body, 14, INK, width=w - 36)
    for x in [370, 655, 940, 1225, 1510]:
        d.arrow(x, 552, x + 32, 552, BLUE)
    d.text(1920, 455, "Compilation economics", 15, NAVY, bold=True)
    d.text(1920, 490, "One-time / amortized", 15, GREEN, width=300, bold=True)
    d.text(1920, 520, "• LLM query generation\n• embedding all examples\n• index build + validation", 14, INK, width=320)
    d.text(1920, 605, "Design principle", 15, NAVY, bold=True)
    d.text(1920, 640, "Agent descriptions become\naddressable memory, not\nrepeated prompt context.\nNemotron resolves only Top-K.", 14, PURPLE, width=320, bold=True)

    # Section 2: runtime.
    d.text(90, 780, "02  RUNTIME GATEWAY  /  one entry point for thousands of agents", 22, NAVY, bold=True)
    d.rect(90, 825, 2220, 420, TEAL_FILL, TEAL)
    d.text(120, 848, "Request path: split only when needed → retrieve broadly → rerank narrowly → hand off", 15, TEAL, bold=True)

    runtime_cards = [
        (120, 900, 220, 230, "Client", "one prompt\n+ optional history", BLUE_FILL, BLUE),
        (375, 900, 245, 230, "FastAPI /chat", "single front door\nschema validation\nshadow event", BLUE_FILL, BLUE),
        (655, 900, 245, 230, "Intent sharder", "Nebius micro-model\nor heuristic fallback\nbounded shards required", PURPLE_FILL, PURPLE),
        (935, 900, 245, 230, "Stage 1 retrieve", "embed each shard\nFAISS top-25 vectors\nagent score aggregation", GREEN_FILL, GREEN),
        (1215, 900, 260, 230, "Stage 2 disambiguate", "Top-3 routing cards\nmicro-LLM choice\nrationale + score", AMBER_FILL, AMBER),
        (1510, 900, 260, 230, "Agent handoff", "current: HTTP adapter\nmock fallback for sample\nworkflow metadata + guards", RED_FILL, RED),
        (1805, 900, 425, 230, "Response + telemetry", "one or many decisions\ncompound result set\nshadow log: prompt, score,\nagent, refusal signal", TEAL_FILL, TEAL),
    ]
    for x, y, w, h, title, body, fill, stroke in runtime_cards:
        d.rect(x, y, w, h, fill, stroke)
        d.text(x + 16, y + 16, title, 16, stroke, width=w - 32, bold=True)
        d.text(x + 16, y + 55, body, 14, INK, width=w - 32)
    for x, end in [(340, 375), (620, 655), (900, 935), (1180, 1215), (1475, 1510), (1770, 1805)]:
        d.arrow(x, 1015, end, 1015, TEAL)
    d.text(120, 1172, "Per-shard scoring in current PoC", 14, NAVY, bold=True)
    d.text(395, 1170, "agent_score = max(similarity) + 0.02 × hit_count", 17, PURPLE, width=650, bold=True)
    d.text(1120, 1172, "Top-K / Top-3 are tunable — evaluate recall@K before production", 14, MUTED, width=1020)

    # Feedback loop.
    d.rect(690, 1280, 1080, 150, AMBER_FILL, AMBER)
    d.text(720, 1300, "03  FEEDBACK LOOP  /  correct the routing surface, not the user-facing model", 18, AMBER, width=980, bold=True)
    d.text(720, 1340, "shadow logs → refusal / explicit correction → capable reviewer → corrected query embedding → versioned index", 15, INK, width=1000)
    d.text(720, 1377, "Current PoC warning: local mutable FAISS + unauthenticated correction endpoint + no locking, review, deduplication, or expiry.", 13, RED, width=1000)
    d.arrow(1800, 1035, 1800, 1350, AMBER, dashed=True, label="learn")
    d.arrow(690, 1350, 500, 1080, AMBER, dashed=True, label="correction")

    # Section 3: innovation and equations.
    d.text(90, 1490, "THEORETICAL INNOVATION  /  a routing control plane, not another agent", 22, NAVY, bold=True)
    d.rect(90, 1535, 1080, 425, PURPLE_FILL, PURPLE)
    d.text(125, 1560, "The scaling move", 19, PURPLE, bold=True)
    d.text(125, 1602, "Let A = agents, E = indexed examples / agent, V = A × E.", 17, INK, width=950)
    d.text(125, 1645, "Prompt-all LLM", 16, RED, bold=True)
    d.text(125, 1680, "request context ≈ A × schema_tokens\nattention + input cost grow with catalog size\noutput must still be generated / parsed", 15, INK, width=950)
    d.text(125, 1773, "CentRI current PoC", 16, BLUE, bold=True)
    d.text(125, 1808, "embed(q) + exact Flat search O(V × D) + LLM over K schemas\nK ≪ A, but current FAISS is linear — not O(log A)", 15, INK, width=950)
    d.text(125, 1898, "CentRI production target", 16, GREEN, bold=True)
    d.text(125, 1933, "ANN retrieval (HNSW / IVF-PQ) + calibrated rerank + abstain\nsublinear-like behavior is a target to benchmark, not a theorem", 15, INK, width=950)

    d.rect(1210, 1535, 1100, 425, AMBER_FILL, AMBER)
    d.text(1245, 1560, "Why two stages improve the accuracy / cost frontier", 19, AMBER, bold=True)
    d.text(1245, 1605, "Stage 1: high recall", 16, GREEN, bold=True)
    d.text(1245, 1640, "Cheap bi-encoder embeddings retrieve a small candidate pool.\nPrecomputed agent examples preserve open-world coverage.", 15, INK, width=980)
    d.text(1245, 1710, "Stage 2: high precision", 16, PURPLE, bold=True)
    d.text(1245, 1745, "A micro-LLM sees only Top-K schemas and the query.\nIt resolves payroll ↔ HR, support ↔ security, and other collisions.", 15, INK, width=980)
    d.text(1245, 1815, "Theoretical guardrail", 16, RED, bold=True)
    d.text(1245, 1850, "Retrieval recall@K bounds what reranking can recover.\nNo reranker can select an agent absent from the candidate set.", 15, INK, width=980)
    d.text(1245, 1910, "Therefore measure: recall@K · top-1 accuracy · abstention · ECE · p95 latency · cost/request", 14, NAVY, width=1000, bold=True)

    # Section 4: comparison.
    d.text(90, 2015, "DECISION ARCHITECTURE COMPARISON  /  choose the right primitive", 22, NAVY, bold=True)
    d.rect(90, 2060, 2220, 345, SLATE_FILL, "#94a3b8")
    # Column headers.
    cols = [
        (120, 350, "Approach", NAVY),
        (470, 740, "Strength", GREEN),
        (855, 1120, "Scaling constraint", RED),
        (1235, 1530, "Decision surface", PURPLE),
        (1645, 2220, "CentRI position", BLUE),
    ]
    for x, w, title, color in cols:
        d.text(x, 2085, title, 16, color, width=w - 20, bold=True)
    d.line(120, 2120, 2220, 2120, "#cbd5e1")
    rows = [
        (2140, "Prompt every LLM", "Open-ended reasoning\nfamiliar interface", "Input context and cost\nscale with A", "Text + implicit choice", "Use only for small catalogs or final synthesis"),
        (2200, "Flat choice surface", "Fast bounded decision", "Full option catalog must\nbe serialized and maintained", "Closed, enumerated options", "Inefficient discovery at 1k–1M agents; retrieve first"),
        (2260, "Single classifier", "One forward pass\ncheap after training", "Needs labeled taxonomy\nretraining for new agents", "Closed labels", "Fast baseline; weak under agent churn / open world"),
        (2320, "CentRI", "Offline memory +\nretrieve / rerank", "Current Flat index is O(V×D);\nANN + eval still required", "Open catalog → Top-K → route", "Single entry point, bounded reasoning, incremental compilation"),
    ]
    for y, approach, strength, constraint, surface, position in rows:
        d.text(120, y, approach, 14, NAVY, width=320, bold=True)
        d.text(470, y, strength, 14, INK, width=350)
        d.text(855, y, constraint, 14, RED if "scale" in constraint or "O(" in constraint or "retraining" in constraint else INK, width=350)
        d.text(1235, y, surface, 14, PURPLE, width=370)
        d.text(1645, y, position, 14, BLUE if approach == "CentRI" else INK, width=560, bold=approach == "CentRI")
        if y < 2320:
            d.line(120, y + 43, 2220, y + 43, "#e2e8f0")

    # Section 5: production boundary and evidence.
    d.text(90, 2470, "IMPLEMENTATION TRUTH  /  what the current repository proves vs. what it proposes", 21, NAVY, bold=True)
    d.rect(90, 2515, 1060, 360, GREEN_FILL, GREEN)
    d.text(125, 2540, "Implemented in this repository", 18, GREEN, bold=True)
    d.text(
        125,
        2585,
        "✓ catalog parsing + routing cards\n✓ Nebius OpenAI-compatible client\n✓ optional Tavily synthesis grounding\n✓ FAISS normalized vector store\n✓ intent split + vector vote + Top-3 rerank\n✓ FastAPI /chat, /agents, /health\n✓ shadow logs + correction script",
        15,
        INK,
        width=940,
    )
    d.rect(1190, 2515, 1120, 360, RED_FILL, RED)
    d.text(1225, 2540, "Must be benchmarked / productionized", 18, RED, bold=True)
    d.text(
        1225,
        2585,
        "• real agent execution, tools, workflows, guardrails\n• ANN index / sharding / concurrent writes\n• calibrated confidence + abstention policy\n• golden routing eval: recall@K, accuracy, ECE\n• parallel shard execution + result synthesis\n• auth, redaction, retention, rate limits, audit\n• latency and cost curves at 10 / 100 / 1,000 / 10,000 agents",
        15,
        INK,
        width=1000,
    )

    # Evidence footer.
    d.rect(90, 2920, 2220, 305, "#f8fafc", "#94a3b8")
    d.text(120, 2945, "RESEARCH NOTES / sources used for the claims in this board", 17, NAVY, bold=True)
    sources = (
        "1. FAISS indexes + guidelines (official): github.com/facebookresearch/faiss/wiki/Faiss-indexes\n"
        "   IndexFlatIP is exact; normalized vectors support cosine-style search; HNSW / IVF trade recall, memory, and speed.\n"
        "2. Two-stage retrieval evidence: arxiv.org/abs/2212.06121 and arxiv.org/abs/2205.10569\n"
        "   Dense retrieval supplies candidates; cross-encoder/reranker improves precision at added latency.\n"
        "3. Nebius Token Factory docs: docs.tokenfactory.nebius.com/api-reference/examples/create-embeddings\n"
        "   OpenAI-compatible embeddings/chat are the implementation basis in this repository."
    )
    d.text(120, 2985, sources, 13, INK, width=2100)
    d.text(
        120,
        3185,
        "Evidence discipline: CentRI is a design for predictable scaling, not a guaranteed accuracy win. The decisive next artifact is a reproducible benchmark harness.",
        16,
        RED,
        width=2100,
        bold=True,
    )

    return {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": d.elements,
        "appState": {
            "gridSize": None,
            "viewBackgroundColor": "#fbfdff",
            "scrollX": 0,
            "scrollY": 0,
            "zoom": {"value": 0.55},
            "currentItemStrokeColor": INK,
            "currentItemBackgroundColor": "transparent",
            "currentItemFillStyle": "solid",
            "currentItemStrokeWidth": 2,
            "currentItemStrokeStyle": "solid",
            "currentItemRoughness": 1,
            "currentItemOpacity": 100,
            "currentItemFontFamily": 1,
            "currentItemFontSize": 20,
            "currentItemTextAlign": "left",
            "currentItemStartArrowhead": None,
            "currentItemEndArrowhead": "triangle",
            "showGrid": False,
            "showStats": False,
            "zenModeEnabled": False,
            "viewModeEnabled": False,
            "name": "CentRI architecture and theoretical innovation",
        },
        "files": {},
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
