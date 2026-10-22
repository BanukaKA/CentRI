"""Generate the five-minute CentRI technical presentation.

Usage:
    .venv\\Scripts\\python scripts/generate_presentation.py

The output is written to the repository root so it can be opened directly in
PowerPoint or imported into another presentation tool.
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_CONNECTOR
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "CentRI_5_minute_presentation.pptx"

W = Inches(13.333)
H = Inches(7.5)

# Palette: dark infrastructure navy with restrained semantic accents.
NAVY = RGBColor(18, 31, 52)
NAVY_2 = RGBColor(28, 47, 76)
INK = RGBColor(32, 48, 71)
MUTED = RGBColor(96, 116, 140)
LINE = RGBColor(204, 216, 229)
PAPER = RGBColor(248, 251, 253)
WHITE = RGBColor(255, 255, 255)
BLUE = RGBColor(48, 119, 221)
BLUE_LIGHT = RGBColor(224, 238, 255)
TEAL = RGBColor(15, 118, 110)
TEAL_LIGHT = RGBColor(220, 247, 243)
PURPLE = RGBColor(113, 74, 185)
PURPLE_LIGHT = RGBColor(239, 233, 253)
AMBER = RGBColor(190, 115, 12)
AMBER_LIGHT = RGBColor(255, 244, 211)
RED = RGBColor(190, 52, 52)
RED_LIGHT = RGBColor(255, 230, 230)
GREEN = RGBColor(27, 133, 74)
GREEN_LIGHT = RGBColor(224, 247, 232)


def rgb(hex_value: str) -> RGBColor:
    return RGBColor.from_string(hex_value.replace("#", ""))


def set_bg(slide, color: RGBColor = PAPER) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def shape(slide, kind, x, y, w, h, fill=WHITE, line=LINE, radius=False):
    item = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    item.fill.solid()
    item.fill.fore_color.rgb = fill
    item.line.color.rgb = line
    item.line.width = Pt(1)
    if radius and kind == MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE:
        item.adjustments[0] = 0.12
    return item


def textbox(
    slide,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    size: float = 16,
    color: RGBColor = INK,
    bold: bool = False,
    font: str = "Aptos",
    align=PP_ALIGN.LEFT,
    valign=MSO_ANCHOR.TOP,
    margin: float = 0.03,
):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    tf.vertical_anchor = valign
    tf.alignment = align
    for index, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        p.text = line
        p.font.name = font
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = color
        p.alignment = align
        p.space_after = Pt(2)
    return box


def rich_textbox(
    slide,
    runs: list[tuple[str, RGBColor, bool]],
    x: float,
    y: float,
    w: float,
    h: float,
    size: float = 16,
):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(0.03)
    tf.margin_right = Inches(0.03)
    p = tf.paragraphs[0]
    for text, color, bold in runs:
        run = p.add_run()
        run.text = text
        run.font.name = "Aptos"
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
    return box


def title(slide, kicker: str, heading: str, subtitle: str | None = None, dark: bool = False):
    color = WHITE if dark else NAVY
    muted = RGBColor(190, 208, 229) if dark else MUTED
    textbox(slide, kicker.upper(), 0.62, 0.34, 4.5, 0.25, 9, BLUE_LIGHT if dark else BLUE, True)
    textbox(slide, heading, 0.62, 0.65, 11.9, 0.55, 26, color, True)
    if subtitle:
        textbox(slide, subtitle, 0.65, 1.25, 11.9, 0.36, 12, muted)


def footer(slide, number: int, source: str | None = None, dark: bool = False):
    color = RGBColor(184, 202, 224) if dark else MUTED
    line = RGBColor(75, 101, 133) if dark else LINE
    slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, Inches(0.62), Inches(7.08), Inches(12.7), Inches(7.08)
    ).line.color.rgb = line
    textbox(slide, "CENTRI  /  CENTRAL ROUTING INTELLIGENCE", 0.65, 7.14, 5.2, 0.18, 7.5, color, True)
    if source:
        textbox(slide, source, 5.55, 7.14, 6.7, 0.18, 7.2, color, False, align=PP_ALIGN.RIGHT)
    textbox(slide, f"{number:02d}", 12.42, 7.11, 0.3, 0.2, 8, color, True, align=PP_ALIGN.RIGHT)


def bullet_list(slide, items, x, y, w, h, size=15, color=INK, bullet_color=BLUE, gap=0.39):
    for index, item in enumerate(items):
        yy = y + index * gap
        shape(slide, MSO_AUTO_SHAPE_TYPE.OVAL, x, yy + 0.08, 0.09, 0.09, bullet_color, bullet_color)
        textbox(slide, item, x + 0.18, yy, w - 0.18, 0.28, size, color)


def arrow(slide, x1, y1, x2, y2, color=BLUE, width=2.2):
    connector = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2)
    )
    connector.line.color.rgb = color
    connector.line.width = Pt(width)
    connector.line.end_arrowhead = True
    return connector


def card(slide, x, y, w, h, heading, body, fill, accent, body_size=12.5):
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, x, y, w, h, fill, accent, True)
    shape(slide, MSO_AUTO_SHAPE_TYPE.RECTANGLE, x, y, 0.07, h, accent, accent)
    textbox(slide, heading, x + 0.2, y + 0.14, w - 0.35, 0.35, 14, accent, True)
    textbox(slide, body, x + 0.2, y + 0.55, w - 0.35, h - 0.68, body_size, INK)


def add_notes(slide, text: str):
    # python-pptx does not expose notes editing consistently across versions.
    # Put the talk track in speaker-visible hidden metadata-like footer text only
    # when needed; the deck itself remains presentation-first.
    slide.notes_slide.notes_text_frame.text = text


def build_deck() -> Presentation:
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    blank = prs.slide_layouts[6]

    # Slide 1 — opening thesis.
    slide = prs.slides.add_slide(blank)
    set_bg(slide, NAVY)
    shape(slide, MSO_AUTO_SHAPE_TYPE.RECTANGLE, 9.7, 0, 3.63, 7.5, NAVY_2, NAVY_2)
    shape(slide, MSO_AUTO_SHAPE_TYPE.RECTANGLE, 9.7, 0, 0.08, 7.5, BLUE, BLUE)
    textbox(slide, "CENTRI / CENTRAL ROUTING INTELLIGENCE", 0.72, 0.68, 7.4, 0.25, 11, BLUE_LIGHT, True)
    textbox(slide, "One front door.\nThousands of agents.\nBounded intelligence.", 0.7, 1.42, 8.45, 2.15, 31, WHITE, True)
    textbox(
        slide,
        "A semantic API gateway that compiles agent capabilities offline, retrieves the right candidates at runtime, and reasons only where ambiguity remains.",
        0.74,
        4.08,
        7.85,
        0.85,
        17,
        RGBColor(204, 222, 244),
    )
    # Minimal visual: query → routing memory → agent.
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 10.28, 1.22, 2.35, 0.68, BLUE, BLUE, True)
    textbox(slide, "USER REQUEST", 10.28, 1.44, 2.35, 0.2, 12, WHITE, True, align=PP_ALIGN.CENTER)
    arrow(slide, 11.45, 1.95, 11.45, 2.55, RGBColor(168, 195, 228), 1.8)
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 10.28, 2.58, 2.35, 1.05, TEAL, TEAL, True)
    textbox(slide, "CENTRI\nROUTING PLANE", 10.28, 2.79, 2.35, 0.52, 13, WHITE, True, align=PP_ALIGN.CENTER)
    arrow(slide, 11.45, 3.67, 11.45, 4.28, RGBColor(168, 195, 228), 1.8)
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 10.28, 4.31, 2.35, 0.68, PURPLE, PURPLE, True)
    textbox(slide, "SPECIALIST AGENT", 10.28, 4.53, 2.35, 0.2, 12, WHITE, True, align=PP_ALIGN.CENTER)
    textbox(slide, "5-minute technical overview", 0.75, 6.25, 4.5, 0.25, 11, RGBColor(157, 183, 212))
    textbox(slide, "The problem is not more agents.\nThe problem is finding the right one.", 10.15, 5.55, 2.7, 0.75, 15, WHITE, True, align=PP_ALIGN.CENTER)
    footer(slide, 1, "Architecture proposal · current repository PoC", dark=True)
    add_notes(slide, "Opening: CentRI is a routing control plane, not another general-purpose agent. It gives a large agent catalog a single semantic entry point.")

    # Slide 2 — problem.
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    title(slide, "The problem", "Agent choice becomes the bottleneck", "As agent catalogs grow, naive routing grows in the wrong dimension.")
    card(slide, 0.72, 1.85, 3.75, 3.55, "PROMPT-ALL LLM ROUTING", "Every request includes:\n• many agent descriptions\n• tools, exclusions, policies\n• growing prompt tokens\n\nThe model spends reasoning budget scanning irrelevant candidates.", RED_LIGHT, RED, 14)
    card(slide, 4.78, 1.85, 3.75, 3.55, "FLAT CLASSIFIER", "Fast after training, but:\n• labels are closed-world\n• new agents require retraining\n• compound requests are awkward\n• long-tail coverage is fragile", AMBER_LIGHT, AMBER, 14)
    card(slide, 8.84, 1.85, 3.75, 3.55, "SINGLE-PASS CHOICE", "Typed decision engines are excellent for a bounded choice set.\n\nBut a large or changing catalog still needs candidate discovery before choice.", PURPLE_LIGHT, PURPLE, 14)
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 1.0, 5.85, 11.25, 0.7, NAVY, NAVY, True)
    rich_textbox(slide, [("The scaling question: ", WHITE, True), ("how do we keep routing cost and ambiguity bounded while the agent catalog expands?", BLUE_LIGHT, False)], 1.25, 6.04, 10.75, 0.28, 15)
    footer(slide, 2, "Design hypothesis; benchmark against real catalog sizes")
    add_notes(slide, "Explain that prompt-all routing can work for small catalogs, but the prompt and decision surface grow with the catalog. A classifier is fast but closed-world. Typed one-pass choices are bounded by their interface and still need discovery for very large catalogs.")

    # Slide 3 — core idea.
    slide = prs.slides.add_slide(blank)
    set_bg(slide, WHITE)
    title(slide, "The core innovation", "Compile the catalog once; route against memory", "CentRI separates slow knowledge preparation from fast request-time selection.")
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 0.72, 1.78, 5.72, 4.55, BLUE_LIGHT, BLUE, True)
    textbox(slide, "OFFLINE / CHANGE-TIME", 1.0, 2.05, 3.1, 0.25, 11, BLUE, True)
    textbox(slide, "Agent schema\n→ synthetic utterances\n→ embeddings\n→ vector index", 1.0, 2.55, 4.7, 1.55, 25, NAVY, True)
    bullet_list(slide, ["Nebius + Nemotron expand coverage", "Tavily grounds time-sensitive phrasing", "Contrastive peers create hard negatives", "Artifacts persist as routing memory"], 1.0, 4.45, 4.9, 1.4, 13, INK, BLUE, 0.39)
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 6.88, 1.78, 5.72, 4.55, TEAL_LIGHT, TEAL, True)
    textbox(slide, "RUNTIME / REQUEST-TIME", 7.16, 2.05, 3.1, 0.25, 11, TEAL, True)
    textbox(slide, "User query\n→ retrieve candidates\n→ resolve ambiguity\n→ return agent ID", 7.16, 2.55, 4.75, 1.55, 25, NAVY, True)
    bullet_list(slide, ["One embedding per intent shard", "FAISS returns high-recall candidates", "Micro-LLM sees only Top-K schemas", "Execution remains a separate concern"], 7.16, 4.45, 4.95, 1.4, 13, INK, TEAL, 0.39)
    arrow(slide, 6.45, 4.05, 6.84, 4.05, PURPLE, 2.5)
    textbox(slide, "amortize", 6.24, 3.62, 0.82, 0.22, 10, PURPLE, True, align=PP_ALIGN.CENTER)
    footer(slide, 3, "Repository: scripts/compile.py · centri/synthesis · centri/index")
    add_notes(slide, "This is the central design move. The catalog is transformed into reusable semantic memory when it changes. Runtime does not re-read every agent.")

    # Slide 4 — architecture.
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    title(slide, "How the system works", "Three planes: compile, route, learn", "The gateway is the control plane; specialized agents remain downstream execution units.")
    # Swimlanes.
    lanes = [
        (1.78, "COMPILE PLANE", BLUE_LIGHT, BLUE),
        (3.32, "ROUTING PLANE", TEAL_LIGHT, TEAL),
        (4.86, "LEARNING PLANE", AMBER_LIGHT, AMBER),
    ]
    for y, label, fill, accent in lanes:
        shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 0.72, y, 11.88, 1.18, fill, accent, True)
        textbox(slide, label, 0.93, y + 0.16, 1.35, 0.22, 9, accent, True)
    # Compile flow.
    compile_steps = [("Catalog", 2.42, TEAL), ("Synthesis", 3.76, PURPLE), ("Embed", 5.10, BLUE), ("FAISS", 6.44, GREEN), ("Artifacts", 7.78, TEAL)]
    for label, x, accent in compile_steps:
        shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, x, 2.06, 1.05, 0.58, WHITE, accent, True)
        textbox(slide, label, x, 2.25, 1.05, 0.18, 11, accent, True, align=PP_ALIGN.CENTER)
    for x in [3.47, 4.81, 6.15, 7.49]:
        arrow(slide, x, 2.35, x + 0.27, 2.35, BLUE, 1.5)
    # Runtime flow.
    runtime_steps = [("POST /route", 2.42, BLUE), ("Split", 3.76, PURPLE), ("Top-K", 5.10, GREEN), ("Top-3", 6.44, AMBER), ("Agent ID", 7.78, TEAL)]
    for label, x, accent in runtime_steps:
        shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, x, 3.60, 1.05, 0.58, WHITE, accent, True)
        textbox(slide, label, x, 3.79, 1.05, 0.18, 11, accent, True, align=PP_ALIGN.CENTER)
    for x in [3.47, 4.81, 6.15, 7.49]:
        arrow(slide, x, 3.89, x + 0.27, 3.89, TEAL, 1.5)
    # Learning flow.
    learn_steps = [("Shadow log", 2.42, AMBER), ("Review", 3.76, RED), ("Correct", 5.10, AMBER), ("Re-embed", 6.44, BLUE), ("Version", 7.78, GREEN)]
    for label, x, accent in learn_steps:
        shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, x, 5.14, 1.05, 0.58, WHITE, accent, True)
        textbox(slide, label, x, 5.33, 1.05, 0.18, 11, accent, True, align=PP_ALIGN.CENTER)
    for x in [3.47, 4.81, 6.15, 7.49]:
        arrow(slide, x, 5.43, x + 0.27, 5.43, AMBER, 1.5)
    textbox(slide, "Catalog source: sample_agent_router_dataset.json", 9.18, 2.12, 2.95, 0.33, 11, INK, True)
    textbox(slide, "Current handoff: StubAgentExecutor", 9.18, 3.67, 2.95, 0.33, 11, RED, True)
    textbox(slide, "Current risk: local mutable index", 9.18, 5.21, 2.95, 0.33, 11, RED, True)
    footer(slide, 4, "FastAPI · Nebius · NVIDIA Nemotron · Tavily · FAISS · Pydantic · NumPy")
    add_notes(slide, "Walk left-to-right. Compilation creates memory. Routing selects a destination. Learning uses production feedback to improve the routing surface.")

    # Slide 5 — request walkthrough.
    slide = prs.slides.add_slide(blank)
    set_bg(slide, WHITE)
    title(slide, "Inside one request", "Retrieve broadly, reason narrowly", "A compound request can produce multiple independent routes.")
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 0.72, 1.75, 12.0, 0.85, NAVY, NAVY, True)
    textbox(slide, "“Analyze our Q3 cloud infrastructure spend and prepare an incident summary.”", 1.0, 2.02, 11.4, 0.28, 17, WHITE, True, align=PP_ALIGN.CENTER)
    steps = [
        ("1", "Intent split", "cloud spend\nincident summary", PURPLE_LIGHT, PURPLE),
        ("2", "Embed", "one vector\nper shard", BLUE_LIGHT, BLUE),
        ("3", "Retrieve", "FAISS Top-25\nvector hits", GREEN_LIGHT, GREEN),
        ("4", "Aggregate", "agent score\nmax(sim) + vote", TEAL_LIGHT, TEAL),
        ("5", "Rerank", "LLM sees\nTop-3 cards", AMBER_LIGHT, AMBER),
        ("6", "Return", "agent IDs\nfor handoff", NAVY_2, WHITE),
    ]
    xs = [0.72, 2.73, 4.74, 6.75, 8.76, 10.77]
    for index, (number, heading, body, fill, accent) in enumerate(steps):
        shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, xs[index], 3.28, 1.63, 1.55, fill, accent if fill != NAVY_2 else NAVY_2, True)
        shape(slide, MSO_AUTO_SHAPE_TYPE.OVAL, xs[index] + 0.1, 3.43, 0.28, 0.28, accent if fill != NAVY_2 else BLUE, accent if fill != NAVY_2 else BLUE)
        textbox(slide, number, xs[index] + 0.1, 3.48, 0.28, 0.15, 9, WHITE, True, align=PP_ALIGN.CENTER)
        textbox(slide, heading, xs[index] + 0.12, 3.83, 1.4, 0.25, 12, accent if fill != NAVY_2 else WHITE, True, align=PP_ALIGN.CENTER)
        textbox(slide, body, xs[index] + 0.12, 4.19, 1.4, 0.42, 11, INK if fill != NAVY_2 else WHITE, False, align=PP_ALIGN.CENTER)
        if index < len(steps) - 1:
            arrow(slide, xs[index] + 1.66, 4.05, xs[index] + 1.94, 4.05, MUTED, 1.3)
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 1.17, 5.42, 10.95, 0.72, SLATE if False else PAPER, LINE, True)
    rich_textbox(slide, [("Bounded reasoning: ", NAVY, True), ("the reranker never compares against the full catalog — only the retrieved candidates.", TEAL, False)], 1.45, 5.63, 10.4, 0.25, 15)
    textbox(slide, "Current PoC: shards are processed sequentially; production target: parallel shard routing and execution.", 1.1, 6.42, 11.2, 0.25, 11, RED, True, align=PP_ALIGN.CENTER)
    footer(slide, 5, "Runtime: centri/routing · centri/gateway/app.py")
    add_notes(slide, "Use this example to make the pipeline concrete. The same gateway can return one or several agent destinations. The current implementation executes configured HTTP runtimes concurrently and uses an explicit simulation fallback when no endpoint is configured.")

    # Slide 6 — scale comparison.
    slide = prs.slides.add_slide(blank)
    set_bg(slide)
    title(slide, "Why this architecture scales", "Keep the request-time decision surface small", "CentRI is designed around a bounded cascade; exact performance still requires benchmarking.")
    # Left equations.
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 0.72, 1.78, 5.55, 4.75, NAVY, NAVY, True)
    textbox(slide, "REQUEST-TIME COST MODEL", 1.0, 2.06, 3.2, 0.22, 10, BLUE_LIGHT, True)
    textbox(slide, "Prompt-all LLM", 1.0, 2.58, 2.0, 0.28, 16, RED_LIGHT, True)
    textbox(slide, "context ≈ A × schema_tokens\nLLM scans the growing catalog\ncost and latency rise with A", 1.0, 2.96, 4.6, 0.85, 16, WHITE)
    textbox(slide, "CentRI current PoC", 1.0, 4.05, 2.5, 0.28, 16, BLUE_LIGHT, True)
    textbox(slide, "embed(q) + O(V × D) exact search\n+ LLM over K schemas\nK ≪ A, but Flat search is linear", 1.0, 4.43, 4.75, 0.92, 16, WHITE)
    textbox(slide, "CentRI production target", 1.0, 5.54, 2.7, 0.28, 16, TEAL_LIGHT, True)
    textbox(slide, "ANN retrieval: HNSW / IVF-PQ\nrecall–latency–memory tuning\nsublinear-like behavior must be measured", 1.0, 5.92, 4.75, 0.5, 14, WHITE)
    # Right bars.
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 6.65, 1.78, 5.98, 4.75, WHITE, LINE, True)
    textbox(slide, "DECISION SURFACE AS THE CATALOG GROWS", 6.95, 2.05, 4.9, 0.22, 10, NAVY, True)
    labels = [("Prompt-all LLM", 2.95, RED), ("Flat classifier", 1.75, AMBER), ("Jev-style choice", 1.35, PURPLE), ("CentRI cascade", 1.05, TEAL)]
    for index, (label, bar, color) in enumerate(labels):
        y = 2.63 + index * 0.75
        textbox(slide, label, 6.98, y, 1.35, 0.2, 11.5, INK, True)
        shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 8.55, y + 0.01, bar, 0.28, color, color, True)
        textbox(slide, "grows with A" if index == 0 else "bounded / fixed stage", 8.7 + bar, y + 0.05, 2.15, 0.18, 9.5, MUTED)
    textbox(slide, "A = total agents   K = rerank candidates   V = indexed examples   D = vector dimension", 6.98, 5.95, 5.0, 0.25, 10, MUTED)
    textbox(slide, "Claim discipline: CentRI is a scalability hypothesis until latency, recall, cost, and accuracy curves are measured.", 6.98, 6.25, 5.15, 0.25, 10.5, RED, True)
    footer(slide, 6, "FAISS official docs: IndexFlatIP exact; HNSW / IVF trade speed, memory, and recall")
    add_notes(slide, "Do not claim magical O(log N) behavior. The current index is exact Flat search and is linear. The architectural advantage is that the LLM only reasons over K candidates; production must move retrieval to ANN and benchmark it.")

    # Slide 7 — comparison and Jev.
    slide = prs.slides.add_slide(blank)
    set_bg(slide, WHITE)
    title(slide, "Where CentRI fits", "Not an LLM replacement — a routing control plane", "Each primitive is useful; CentRI composes them for an open, changing agent catalog.")
    headers = [("Approach", 0.75, 1.5), ("Best at", 2.55, 2.2), ("Breaks down when", 5.0, 2.7), ("CentRI response", 8.0, 4.45)]
    for heading, x, w in headers:
        textbox(slide, heading, x, 1.85, w, 0.25, 12, NAVY, True)
    slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(0.75), Inches(2.18), Inches(12.55), Inches(2.18)).line.color.rgb = LINE
    rows = [
        ("Prompt-all LLM", "Open-ended reasoning", "Catalog prompt grows; ambiguity and token cost grow", "Remove the catalog from the prompt; retrieve candidates first", RED_LIGHT, RED),
        ("Flat classifier", "Fast fixed labels", "New agents require labels, data, retraining", "Compile new agents incrementally from schemas + examples", AMBER_LIGHT, AMBER),
        ("Jev-style choice", "Typed, parallel bounded decisions", "Choice surface is enumerated; public interface documents ≤255 options", "Use candidate discovery before typed choice when A is large", PURPLE_LIGHT, PURPLE),
        ("CentRI", "Open-catalog semantic routing", "Current PoC still needs ANN, evaluation, security, real handoff", "One entry point → Top-K retrieval → focused disambiguation", TEAL_LIGHT, TEAL),
    ]
    for index, (approach, best, breaks, response, fill, accent) in enumerate(rows):
        y = 2.38 + index * 0.87
        shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 0.75, y, 11.8, 0.67, fill, accent, True)
        textbox(slide, approach, 0.98, y + 0.18, 1.35, 0.2, 11.5, accent, True)
        textbox(slide, best, 2.55, y + 0.12, 2.15, 0.35, 11, INK)
        textbox(slide, breaks, 5.0, y + 0.12, 2.7, 0.38, 11, INK)
        textbox(slide, response, 8.0, y + 0.12, 4.2, 0.38, 11, INK, approach == "CentRI")
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 0.75, 6.15, 11.8, 0.55, NAVY, NAVY, True)
    textbox(slide, "Key idea: candidate discovery and candidate choice are different problems.", 1.0, 6.32, 11.3, 0.2, 15, WHITE, True, align=PP_ALIGN.CENTER)
    footer(slide, 7, "Jev architecture reference: jevtypesafeai.com/jev/architecture")
    add_notes(slide, "Position CentRI as composition, not replacement. Jev-like typed decisions can be an excellent stage-two selector, but a very large catalog still needs candidate discovery.")

    # Slide 8 — current state and roadmap.
    slide = prs.slides.add_slide(blank)
    set_bg(slide, NAVY)
    title(slide, "From PoC to platform", "What exists today — and what proves the thesis", "The architecture is in place; the next milestone is evidence plus real handoff.", dark=True)
    card(slide, 0.72, 1.8, 5.75, 4.55, "BUILT IN THE REPOSITORY", "✓ 10-agent JSON catalog\n✓ Nebius embeddings + NVIDIA Nemotron\n✓ Optional Tavily synthesis grounding\n✓ Contrastive query-generation design\n✓ FAISS HNSW/Flat index and metadata\n✓ Intent splitting + Top-K retrieval\n✓ Top-3 micro-LLM reranking\n✓ /route, /chat, /catalog, /agents\n✓ Shadow logging + correction path", TEAL_LIGHT, TEAL, 13.5)
    card(slide, 6.86, 1.8, 5.75, 4.55, "NEXT PROOF POINTS", "1  Connect and test real agent endpoints\n2  Expand golden routing data\n3  Calibrate thresholds and abstention\n4  Add distributed ANN/sharding\n5  Add durable workflow state\n6  Add production tracing and metrics\n7  Harden multi-tenant authorization\n8  Measure 10 / 100 / 1k / 10k agents", RED_LIGHT, RED, 13.5)
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 1.22, 6.62, 10.82, 0.42, BLUE, BLUE, True)
    textbox(slide, "Success metric: routing accuracy and recall at a predictable p95 cost — not merely a clever diagram.", 1.4, 6.72, 10.45, 0.18, 12.5, WHITE, True, align=PP_ALIGN.CENTER)
    footer(slide, 8, "Repository status: initial platform; HTTP execution adapter + explicit mock fallback", dark=True)
    add_notes(slide, "Close with honesty and a clear next step. The system has the central routing skeleton. The decisive work is benchmark evidence, one real agent handoff, and production reliability.")

    # Slide 9 — sources / glossary.
    slide = prs.slides.add_slide(blank)
    set_bg(slide, PAPER)
    title(slide, "Technical glossary + sources", "Terms used in the architecture", "Keep this slide available after the five-minute narrative.")
    left = [
        ("Embedding", "Vector representation of text; semantic proximity becomes searchable."),
        ("ANN", "Approximate nearest neighbor search; trades a small amount of recall for speed."),
        ("FAISS", "Vector similarity-search library; current PoC uses exact IndexFlatIP."),
        ("Reranker", "Second-stage model that scores a small candidate set with richer context."),
        ("Abstention", "Router declines or asks for clarification when confidence is insufficient."),
        ("Recall@K", "Fraction of correct agents present in the first K retrieved candidates."),
    ]
    y = 1.78
    for term, definition in left:
        textbox(slide, term, 0.78, y, 1.45, 0.23, 11.5, BLUE, True)
        textbox(slide, definition, 2.35, y, 4.2, 0.38, 11, INK)
        y += 0.58
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 7.0, 1.78, 5.58, 4.2, WHITE, LINE, True)
    textbox(slide, "Research anchors", 7.3, 2.03, 2.5, 0.25, 14, NAVY, True)
    sources = [
        "FAISS official indexes + guidelines\nhttps://github.com/facebookresearch/faiss/wiki/Faiss-indexes",
        "Two-stage retrieval / reranking\nhttps://arxiv.org/abs/2212.06121\nhttps://arxiv.org/abs/2205.10569",
        "Jev public architecture\nhttps://www.jevtypesafeai.com/jev/architecture",
        "Nebius embeddings API\nhttps://docs.tokenfactory.nebius.com/api-reference/examples/create-embeddings",
        "Repository source\nsample_agent_router_dataset.json\ncentri/routing · centri/index · centri/gateway",
    ]
    y = 2.52
    for source in sources:
        shape(slide, MSO_AUTO_SHAPE_TYPE.OVAL, 7.3, y + 0.05, 0.08, 0.08, TEAL, TEAL)
        textbox(slide, source, 7.52, y, 4.65, 0.55, 10.5, INK)
        y += 0.65
    shape(slide, MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, 0.78, 5.98, 11.8, 0.6, AMBER_LIGHT, AMBER, True)
    textbox(slide, "Evidence discipline: CentRI is a strong architecture hypothesis; superiority must be established with a reproducible benchmark.", 1.05, 6.17, 11.25, 0.22, 13, AMBER, True, align=PP_ALIGN.CENTER)
    footer(slide, 9, "Sources are included for follow-up; claims are intentionally qualified")
    add_notes(slide, "Leave this slide visible for questions. Define the terms that are most likely unfamiliar and point to the repository and primary references.")

    return prs


def main() -> None:
    prs = build_deck()
    prs.save(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
