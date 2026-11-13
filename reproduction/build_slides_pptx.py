#!/usr/bin/env python3
"""Build the styled 16:9 presentation deck and speaker notes.

Requires python-pptx. Numbers are read from the validated analysis summary so
the deck cannot drift from the report. Run from the repository root:

    python reproduction/build_slides_pptx.py reproduction/analysis \
        --output reproduction/submission/presentation.pptx \
        --notes reproduction/submission/presentation-notes.md
"""

import argparse
import json
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_TICK_MARK
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

# ---------------------------------------------------------------- palette
INK = RGBColor(0x0B, 0x12, 0x20)
INK2 = RGBColor(0x1E, 0x29, 0x3B)
MUTED = RGBColor(0x64, 0x74, 0x8B)
BORDER = RGBColor(0xE2, 0xE8, 0xF0)
BG = RGBColor(0xF6, 0xF8, 0xFB)
CARD = RGBColor(0xFF, 0xFF, 0xFF)
SOFT = RGBColor(0xEE, 0xF2, 0xF7)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEAL = RGBColor(0x0D, 0x94, 0x88)
TEAL_LIGHT = RGBColor(0xCC, 0xFB, 0xF1)
TEAL_DARK = RGBColor(0x0F, 0x76, 0x6E)
AMBER = RGBColor(0xD9, 0x77, 0x06)
AMBER_LIGHT = RGBColor(0xFE, 0xF3, 0xC7)
ROSE = RGBColor(0xBE, 0x12, 0x3C)
SLATE = RGBColor(0x47, 0x55, 0x69)

FONT = "Arial"
MONO = "Courier New"

SLIDE_TITLES = [
    "SimpleMem: the retrieval-depth tradeoff",
    "What we reproduced",
    "The one modification",
    "Measurement design",
    "Live check: does the evidence chain hold?",
    "Measured impact",
    "Comparison with the paper",
    "Debugging and inherited limits",
    "Conclusions",
]

SLIDE_W = 13.333
SLIDE_H = 7.5
MARGIN = 0.7
REPO = "github.com/FreshbirdZhao/SimpleMem-Reproducibility"
DATE = "13 November 2026"


# ---------------------------------------------------------------- helpers
def rgb_text(value):
    text = str(value)
    if text.startswith("#"):
        text = text[1:]
    return RGBColor.from_string(text.upper())


def add_slide(prs, dark=False):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = INK if dark else BG
    return slide


def box(slide, x, y, w, h, text="", size=14, bold=False, color=INK,
        align=PP_ALIGN.LEFT, font=FONT, anchor=MSO_ANCHOR.TOP,
        spacing=1.0, space_after=0, italic=False, margins=(0, 0, 0, 0)):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left = Inches(margins[0])
    tf.margin_right = Inches(margins[1])
    tf.margin_top = Inches(margins[2])
    tf.margin_bottom = Inches(margins[3])
    tf.vertical_anchor = anchor
    lines = text.split("\n")
    for index, line in enumerate(lines):
        p = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        p.space_after = Pt(space_after)
        run = p.add_run()
        run.text = line
        run.font.name = font
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = color
    return shape


def rect(slide, x, y, w, h, fill=None, line=None, line_w=0.75, radius=None,
         transparency=None):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shape.adjustments[0] = radius
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
        if transparency:
            from pptx.oxml.ns import qn
            solid = shape.fill._xPr.find(qn("a:solidFill"))
            srgb = solid.find(qn("a:srgbClr"))
            node = srgb.makeelement(qn("a:alpha"), {"val": str(int(transparency * 100000))})
            srgb.append(node)
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(line_w)
    shape.shadow.inherit = False
    style = shape._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}style")
    if style is not None:
        shape._element.remove(style)
    if shape.has_text_frame:
        shape.text_frame.text = ""
    return shape


def circle(slide, x, y, d, fill, text="", size=13, color=WHITE):
    shape = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background()
    shape.shadow.inherit = False
    style = shape._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}style")
    if style is not None:
        shape._element.remove(style)
    tf = shape.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.color.rgb = color
    return shape


def chip(slide, x, y, w, h, text, fill=SOFT, color=INK2, size=10.5, bold=True):
    rect(slide, x, y, w, h, fill=fill, radius=0.5)
    box(slide, x, y, w, h, text, size=size, bold=bold, color=color,
        align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def header(slide, number, label, title, dark=False, width=11.9):
    accent = TEAL if not dark else TEAL_LIGHT
    rect(slide, MARGIN, 0.62, 0.30, 0.06, fill=accent)
    box(slide, MARGIN, 0.80, width, 0.30, f"{number}  ·  {label}", size=11,
        bold=True, color=accent)
    box(slide, MARGIN, 1.12, width, 0.75, title, size=30, bold=True,
        color=WHITE if dark else INK, spacing=1.0)


def footer(slide, index, total, dark=False):
    color = MUTED if not dark else RGBColor(0x94, 0xA3, 0xB8)
    box(slide, MARGIN, 7.08, 9.0, 0.22, f"FTEC5660  ·  ZHAO GUODONG  ·  1155263139  ·  {REPO}",
        size=8.5, color=color)
    box(slide, SLIDE_W - MARGIN - 1.0, 7.08, 1.0, 0.22, f"{index:02d} / {total:02d}",
        size=8.5, color=color, align=PP_ALIGN.RIGHT)


def card(slide, x, y, w, h, accent=TEAL, fill=CARD):
    shape = rect(slide, x, y, w, h, fill=fill, line=BORDER, radius=0.06)
    rect(slide, x, y, w, 0.06, fill=accent)
    return shape


def stat(slide, x, y, w, h, value, label, note="", accent=TEAL):
    card(slide, x, y, w, h, accent=accent)
    box(slide, x + 0.28, y + 0.28, w - 0.56, 0.62, value, size=30, bold=True, color=INK)
    box(slide, x + 0.28, y + 0.95, w - 0.56, 0.30, label, size=10.5, bold=True, color=SLATE)
    if note:
        box(slide, x + 0.28, y + 1.26, w - 0.56, 0.45, note, size=9.5, color=MUTED, spacing=1.05)


def table(slide, rows, x, y, w, col_widths, row_h=0.46, header_row=True,
          align=None, font_size=11):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y),
                                   Inches(w), Inches(row_h * len(rows)))
    tbl = shape.table
    tbl.first_row = False
    tbl.horz_banding = False
    tbl.vert_banding = False
    align = align or [PP_ALIGN.LEFT] * len(rows[0])
    for index, width in enumerate(col_widths):
        tbl.columns[index].width = Inches(width)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(row_h)
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.margin_left = Inches(0.14)
            cell.margin_right = Inches(0.10)
            cell.margin_top = Inches(0.04)
            cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if r == 0 and header_row:
                cell.fill.fore_color.rgb = INK2
            else:
                cell.fill.fore_color.rgb = CARD if r % 2 else SOFT
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = align[c]
            run = p.add_run()
            run.text = str(value)
            run.font.name = FONT
            run.font.size = Pt(font_size)
            run.font.bold = bool(r == 0 and header_row)
            run.font.color.rgb = WHITE if (r == 0 and header_row) else INK2
    return tbl


def add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text.strip()


def money_delta(value):
    return f"{value:+.4f}"


# ---------------------------------------------------------------- build
def build(summary, output, notes_path):
    baseline = summary["baseline"]
    modified = summary["modified"]
    diff = summary["paired_modified_minus_baseline"]
    seeds = summary["seeds"]
    trials = summary["trials"]

    f1_base = baseline["f1"]["mean"]
    f1_mod = modified["f1"]["mean"]
    f1_delta = diff["f1"]["mean"]
    ret_base = baseline["retrieved"]["mean"]
    ret_mod = modified["retrieved"]["mean"]
    ret_delta = diff["retrieved"]["mean"]
    tot_base = baseline["total_seconds"]["mean"]
    tot_mod = modified["total_seconds"]["mean"]
    tot_delta = diff["total_seconds"]["mean"]
    f1_values = diff["f1"]["values"]
    improved = sum(value > 0 for value in f1_values)

    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    total = 9

    # ------------------------------------------------------------ 1 title
    slide = add_slide(prs, dark=True)
    rect(slide, 0, 0, 0.18, SLIDE_H, fill=TEAL)
    rect(slide, 9.2, -1.4, 5.6, 5.6, fill=TEAL, radius=0.5, transparency=0.88)
    rect(slide, 10.6, 3.6, 4.2, 4.2, fill=AMBER, radius=0.5, transparency=0.92)
    box(slide, 0.9, 0.75, 10.0, 0.3, "FTEC5660  ·  INDIVIDUAL PROJECT  ·  REPRODUCIBILITY WORK",
        size=11, bold=True, color=TEAL_LIGHT)
    box(slide, 0.9, 1.7, 11.2, 1.9,
        "SimpleMem:\nthe retrieval-depth tradeoff", size=52, bold=True, color=WHITE,
        spacing=1.02)
    box(slide, 0.9, 3.85, 9.6, 0.9,
        "Can semantic retrieval drop from top-25 to top-10 without losing answer quality?",
        size=19, color=RGBColor(0xCB, 0xD5, 0xE1), spacing=1.15)
    rect(slide, 0.9, 4.95, 1.4, 0.05, fill=AMBER)
    box(slide, 0.9, 5.2, 7.5, 0.35, "ZHAO GUODONG  ·  1155263139", size=15, bold=True, color=WHITE)
    box(slide, 0.9, 5.6, 9.0, 0.3, f"{REPO}  ·  {DATE}", size=10, color=RGBColor(0x94, 0xA3, 0xB8))
    for x, value, label in [
        (0.9, "120", "validated predictions"),
        (3.35, "3", "paired trials"),
        (5.35, "419", "dialogue turns"),
    ]:
        box(slide, x, 6.25, 2.2, 0.42, value, size=24, bold=True, color=TEAL_LIGHT)
        box(slide, x + 0.02, 6.68, 2.3, 0.25, label, size=9, color=RGBColor(0x94, 0xA3, 0xB8))
    add_notes(slide, """
Open with the question and the scope. This is a partial reproduction of SimpleMem's text memory pipeline on LoCoMo, not a full paper replication. State the one modification up front: semantic top-k 25 to 10. Point at the three numbers: 120 validated predictions, 3 paired trials, one 419-turn conversation. Mention the repository.
""")

    # ------------------------------------------------------------ 2 target
    slide = add_slide(prs)
    header(slide, "01", "WHAT WE REPRODUCED",
           "A full long conversation, compressed into memory")
    steps = [
        ("1", "Memory construction", "Window 40, overlap 2\nSemantic compression"),
        ("2", "Retrieval planning", "LLM infers search intent\nand depth"),
        ("3", "Hybrid retrieval", "Semantic + keyword\n+ structured"),
        ("4", "Reflection & answer", "Up to 2 reflection\nrounds"),
    ]
    x = MARGIN
    for index, (num, title, detail) in enumerate(steps):
        card(slide, x, 2.05, 2.72, 1.62, accent=TEAL if index < 2 else AMBER)
        circle(slide, x + 0.24, 2.26, 0.42, TEAL if index < 2 else AMBER, num, size=12)
        box(slide, x + 0.78, 2.28, 1.8, 0.3, title, size=12, bold=True, color=INK)
        box(slide, x + 0.24, 2.85, 2.28, 0.7, detail, size=9.5, color=MUTED, spacing=1.1)
        if index < 3:
            box(slide, x + 2.78, 2.68, 0.28, 0.3, "→", size=16, bold=True, color=TEAL)
        x += 3.06

    facts = [
        ("419", "dialogue turns", "one complete LoCoMo conversation"),
        ("20", "fixed questions", "6 multi-hop · 5 temporal\n6 single-hop · 3 adversarial"),
        ("DeepSeek", "hosted model", "deepseek-chat via OpenAI-\ncompatible endpoint"),
        ("Qwen3", "embeddings", "0.6B, 1024 dimensions,\nrun locally"),
    ]
    x = MARGIN
    for value, label, note in facts:
        card(slide, x, 4.15, 2.86, 1.95)
        box(slide, x + 0.24, 4.38, 2.4, 0.45, value, size=22, bold=True, color=INK)
        box(slide, x + 0.24, 4.93, 2.4, 0.28, label, size=9.5, bold=True, color=TEAL_DARK)
        box(slide, x + 0.24, 5.25, 2.4, 0.7, note, size=9, color=MUTED, spacing=1.1)
        x += 3.0
    box(slide, MARGIN, 6.35, 11.9, 0.55,
        "Target: the released pipeline answers questions from compressed memory, scored with the "
        "upstream token-set F1. The paper's exact 43.24 is context, not a replication target.",
        size=11, color=SLATE, spacing=1.15)
    footer(slide, 2, total)
    add_notes(slide, """
Walk the four stages left to right: compression into memory units, plan, hybrid retrieval, reflection before answering. Then the four facts. Say explicitly that the target is the behavior plus the upstream F1, and that the paper number is context. Mention the question mix and why one full conversation is a feasible case study.
""")

    # ------------------------------------------------------------ 3 change
    slide = add_slide(prs)
    header(slide, "02", "THE ONE MODIFICATION",
           "One variable: semantic top-k, 25 → 10")
    card(slide, MARGIN, 2.05, 5.05, 2.35, accent=SLATE)
    box(slide, MARGIN + 0.3, 2.3, 4.4, 0.3, "BASELINE  ·  REPOSITORY DEFAULT", size=10, bold=True, color=SLATE)
    box(slide, MARGIN + 0.3, 2.7, 4.4, 0.9, "k = 25", size=40, bold=True, color=INK)
    box(slide, MARGIN + 0.3, 3.55, 4.3, 0.6, "semantic candidates per semantic search",
        size=10.5, color=MUTED, spacing=1.1)

    box(slide, 6.05, 3.0, 0.85, 0.5, "→", size=32, bold=True, color=TEAL)

    card(slide, 7.05, 2.05, 5.55, 2.35, accent=TEAL)
    box(slide, 7.35, 2.3, 4.9, 0.3, "MODIFIED  ·  SINGLE CHANGE", size=10, bold=True, color=TEAL_DARK)
    box(slide, 7.35, 2.7, 4.9, 0.9, "k = 10", size=40, bold=True, color=INK)
    box(slide, 7.35, 3.55, 4.9, 0.6, "same memory, same prompts, same evaluator",
        size=10.5, color=MUTED, spacing=1.1)

    box(slide, MARGIN, 4.72, 4.0, 0.3, "HELD CONSTANT", size=10, bold=True, color=SLATE)
    constants = ["copied memory (same checksum)", "prompts & evaluator", "keyword k = 5",
                 "structured k = 5", "planning & reflection on", "temperature call sites"]
    x, y = MARGIN, 5.05
    for index, label in enumerate(constants):
        if index == 3:
            x, y = MARGIN, 5.51
        chip(slide, x, y, 3.8, 0.34, label, fill=SOFT, size=9.5)
        x += 4.0

    rect(slide, MARGIN, 6.15, 11.9, 0.62, fill=AMBER_LIGHT, radius=0.12)
    box(slide, MARGIN + 0.25, 6.15, 11.4, 0.62,
        "Semantic k caps each semantic search, not the merged context. Keyword, structured and "
        "reflection results can still add entries.", size=10.5, color=INK2, anchor=MSO_ANCHOR.MIDDLE)
    footer(slide, 3, total)
    add_notes(slide, """
This is the whole experimental change. Baseline is the repository default 25; modified is 10. Everything else is identical: prompts, evaluator, keyword and structured k, planning and reflection. Within a seed the modified run copies the baseline memory database and verifies its checksum, so memory generation cannot confound the comparison. The amber note is important: top-k is per semantic search, not a cap on the final context, which is why the retrieved count falls but does not fall to 10.
""")

    # ------------------------------------------------------------ 4 design
    slide = add_slide(prs)
    header(slide, "03", "MEASUREMENT DESIGN",
           "Three paired trials, four measurements")
    metrics = [
        ("Answer F1", "token-set harmonic mean\nof precision and recall"),
        ("Retrieved", "unique merged memory\nentries per question"),
        ("Retrieval", "planning + hybrid search\nseconds per question"),
        ("Answer", "generation seconds\nper question"),
    ]
    x = MARGIN
    for label, detail in metrics:
        card(slide, x, 2.05, 2.86, 1.55)
        box(slide, x + 0.24, 2.25, 2.4, 0.32, label, size=13, bold=True, color=TEAL_DARK)
        box(slide, x + 0.24, 2.65, 2.4, 0.75, detail, size=9.5, color=MUTED, spacing=1.1)
        x += 3.0

    rect(slide, MARGIN, 3.85, 5.75, 2.55, fill=CARD, line=BORDER, radius=0.05)
    box(slide, MARGIN + 0.3, 4.05, 5.1, 0.3, "HOW TRIALS ARE AGGREGATED", size=10, bold=True, color=SLATE)
    rows = [("Seeds", "5660 · 5661 · 5662"),
            ("Runs", "3 seeds × 2 conditions = 6"),
            ("Predictions", "20 questions × 6 runs = 120"),
            ("Variance", "sample variance across 3 seeds (n−1)")]
    y = 4.42
    for label, value in rows:
        box(slide, MARGIN + 0.3, y, 1.35, 0.3, label, size=9.5, bold=True, color=MUTED)
        box(slide, MARGIN + 1.75, y, 3.8, 0.3, value, size=10.5, color=INK2)
        y += 0.46

    rect(slide, 6.85, 3.85, 5.75, 2.55, fill=INK, radius=0.05)
    box(slide, 7.15, 4.05, 5.1, 0.3, "WHAT IS DELIBERATELY NOT DONE", size=10, bold=True, color=TEAL_LIGHT)
    for index, line in enumerate([
        "no provider seed or token counts",
        "no fixed order counterbalancing",
        "no significance claim from 3 trials",
        "no pooling of questions as trials",
    ]):
        box(slide, 7.15, 4.5 + index * 0.44, 5.2, 0.3, "—  " + line, size=10.5,
            color=RGBColor(0xCB, 0xD5, 0xE1))
    box(slide, MARGIN, 6.62, 11.9, 0.3,
        "Each seed builds memory once; the modified run reuses the byte-identical baseline database.",
        size=9.5, color=MUTED)
    footer(slide, 4, total)
    add_notes(slide, """
Four numbers: F1, retrieved entries, retrieval seconds, answer seconds. Six runs and 120 predictions. Explain the aggregation: one aggregate per seed, then mean and sample variance across the three seeds; the three paired differences, not 20 questions, measure variability. The dark panel lists what is deliberately missing: no provider seed, no token cost, no counterbalanced order, no significance claim.
""")

    # ------------------------------------------------------------ 5 demo
    slide = add_slide(prs)
    header(slide, "04", "LIVE CHECK",
           "Does the evidence chain hold?")
    rect(slide, MARGIN, 2.05, 7.55, 3.95, fill=INK, radius=0.04)
    for i, color in enumerate([RGBColor(0xF8, 0x71, 0x71), RGBColor(0xFB, 0xBF, 0x24), RGBColor(0x34, 0xD3, 0x99)]):
        circle(slide, MARGIN + 0.28 + i * 0.24, 2.25, 0.13, color)
    box(slide, MARGIN + 0.28, 2.55, 7.0, 0.3, "TERMINAL  ·  repository root", size=9,
        color=RGBColor(0x94, 0xA3, 0xB8), font=MONO)
    box(slide, MARGIN + 0.28, 2.95, 7.0, 0.35, "$ .venv/bin/python reproduction/validate_evidence.py \\",
        size=10.5, color=WHITE, font=MONO)
    box(slide, MARGIN + 0.55, 3.3, 7.0, 0.35, "reproduction/runs/recovered-20261113-060600-75832",
        size=10.5, color=WHITE, font=MONO)
    terminal_lines = [
        (3.72, '{\n  "verified_predictions": 120,\n  "verified_pairs": 3,\n  "complete": true,', TEAL_LIGHT),
        (4.9, '  "checks": [dataset hash, question order, settings, logs,\n'
              '             paired memory, memory digest, independent F1, timings] }',
         RGBColor(0x94, 0xA3, 0xB8)),
    ]
    for y, text, color in terminal_lines:
        box(slide, MARGIN + 0.28, y, 7.0, 0.9, text, size=10, color=color, font=MONO, spacing=1.15)
    box(slide, MARGIN + 0.28, 5.66, 7.0, 0.25, "0.3 s  ·  local files only  ·  no API calls", size=9,
        color=TEAL_LIGHT, font=MONO)

    checks = [
        ("120", "predictions"),
        ("3", "pairs"),
        ("8", "checks"),
    ]
    y = 2.05
    for value, label in checks:
        card(slide, 8.45, y, 4.15, 0.95, accent=TEAL)
        box(slide, 8.7, y + 0.16, 0.9, 0.55, value, size=24, bold=True, color=TEAL_DARK)
        box(slide, 9.65, y + 0.3, 2.7, 0.3, label, size=10, bold=True, color=SLATE)
        y += 1.1
    box(slide, 8.45, 5.4, 4.15, 0.6, "Independent F1 recomputation\nis part of the check.", size=9.5,
        color=MUTED, spacing=1.15)
    footer(slide, 5, total)
    add_notes(slide, """
Before I show the results, let me verify the evidence chain behind them. Every number in this talk comes from six completed runs, three paired trials, and one hundred twenty question predictions.

（操作：提前把终端开在项目根目录，字号调到 20pt 以上，先试跑一次再用 Cmd+K 清屏。讲完这句后按 Cmd+Tab 切到终端，回车运行下面这条命令，约 0.3 秒，不调用 API。）

.venv/bin/python reproduction/validate_evidence.py reproduction/runs/recovered-20261113-060600-75832

（操作：输出显示 verified_predictions 120、verified_pairs 3、complete true 和八项检查。用鼠标指一下前三行，再指一下 checks 列表；不要打开 results.json 滚动。）

The script independently recomputes token-level F1, re-sums the retrieval and answer timings, and verifies the dataset hash, the question order, the settings, the logs, the paired memory, and the stored memory digest. One hundred twenty predictions, three pairs, every check passes.

So the numbers on the next slide are not hand-entered; they are computed from these validated files. Now, the measured impact.

（操作：讲完立即 Cmd+Tab 回到 PowerPoint，进入下一页。整段演示控制在 45 秒内；如果终端出错，直接切回这一页说一句 “I will show the screenshot instead”，不要现场 debug。）
""")

    # ------------------------------------------------------------ 6 results
    slide = add_slide(prs)
    header(slide, "05", "MEASURED IMPACT",
           "Less context, slightly higher F1, no speedup")
    stat(slide, MARGIN, 2.0, 3.75, 1.85, f"{f1_mod:.4f}",
         "MEAN F1 (ALL 20)",
         f"from {f1_base:.4f}   ·   {f1_delta * 100:+.2f} pp")
    stat(slide, 4.75, 2.0, 3.75, 1.85, f"{ret_mod:.2f}",
         "RETRIEVED ENTRIES / Q",
         f"from {ret_base:.2f}   ·   {ret_delta:+.2f}", accent=SLATE)
    stat(slide, 8.75, 2.0, 3.85, 1.85, f"{tot_mod:.2f}s",
         "RETRIEVAL + ANSWER",
         f"from {tot_base:.3f}s   ·   {tot_delta:+.2f}s", accent=AMBER)

    chart_data = CategoryChartData()
    chart_data.categories = [f"seed {seed}" for seed in seeds]
    chart_data.add_series("k = 25", tuple(baseline["f1"]["values"]))
    chart_data.add_series("k = 10", tuple(modified["f1"]["values"]))
    frame = slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(MARGIN), Inches(4.02),
                                   Inches(7.55), Inches(2.85), chart_data)
    chart = frame.chart
    chart.has_title = False
    chart.font.name = FONT
    chart.font.size = Pt(10)
    chart.font.color.rgb = SLATE
    chart.has_legend = True
    chart.legend.position = XL_LEGEND_POSITION.TOP
    chart.legend.include_in_layout = False
    chart.legend.font.size = Pt(9.5)
    plot = chart.plots[0]
    plot.gap_width = 55
    plot.overlap = -8
    for series, color in zip(plot.series, (SLATE, TEAL)):
        series.format.fill.solid()
        series.format.fill.fore_color.rgb = color
    value_axis = chart.value_axis
    value_axis.minimum_scale = 0.55
    value_axis.maximum_scale = 0.72
    value_axis.major_unit = 0.05
    value_axis.tick_labels.font.size = Pt(9)
    value_axis.tick_labels.font.color.rgb = MUTED
    value_axis.major_tick_mark = XL_TICK_MARK.NONE
    value_axis.has_major_gridlines = True
    value_axis.major_gridlines.format.line.color.rgb = BORDER
    value_axis.format.line.fill.background()
    chart.category_axis.tick_labels.font.size = Pt(9.5)
    chart.category_axis.major_tick_mark = XL_TICK_MARK.NONE
    chart.category_axis.format.line.color.rgb = BORDER

    rect(slide, 8.55, 4.02, 4.05, 1.5, fill=CARD, line=BORDER, radius=0.06)
    box(slide, 8.8, 4.2, 3.6, 0.3, "PER-SEED F1 DIFFERENCE", size=9, bold=True, color=SLATE)
    y = 4.52
    for index, seed in enumerate(seeds):
        value = f1_values[index]
        color = TEAL_DARK if value > 0 else ROSE
        box(slide, 8.8, y, 1.0, 0.25, f"seed {seed}", size=9, color=MUTED)
        box(slide, 10.6, y, 1.7, 0.25, f"{value:+.4f}", size=11, bold=True, color=color,
            align=PP_ALIGN.RIGHT)
        y += 0.3

    rect(slide, 8.55, 5.68, 4.05, 1.2, fill=AMBER_LIGHT, radius=0.08)
    box(slide, 8.8, 5.8, 3.6, 1.0,
        f"F1 improves in {improved} of 3 trials.\nThe direction is not consistent;\ntreat the mean as descriptive.",
        size=9.5, color=INK2, spacing=1.2)
    footer(slide, 6, total)
    add_notes(slide, """
Read the three cards: mean F1 0.6243 to 0.6494, plus 2.51 percentage points; retrieved entries 45.03 to 23.45, minus 21.58; combined latency 8.62 to 9.08 seconds, so no speedup. Then the chart: two of three seeds improve, seed 5662 falls by 0.0166. Say the mean is descriptive and the direction is not consistent. Do not claim statistical significance. A smaller context is not automatically a cost or latency win because planning and reflection also call the hosted model.
""")

    # ------------------------------------------------------------ 7 paper
    slide = add_slide(prs)
    header(slide, "06", "COMPARISON WITH THE PAPER",
           "Why 0.62 is not comparable to 43.24")
    rows = [
        ["Dimension", "Paper (Table 1 / 7)", "This study"],
        ["Model", "GPT-4.1-mini, temperature 0.0", "deepseek-chat, call-site temperatures"],
        ["Data", "Full LoCoMo benchmark", "1 conversation, 20 fixed questions"],
        ["Retrieval k", "range 3–20 (adaptive)", "fixed 25 vs fixed 10"],
        ["Windowing", "window 20, stride 5", "window 40, overlap 2"],
        ["Average F1", "43.24", "62.43 (k=25) / 64.94 (k=10)"],
    ]
    table(slide, rows, MARGIN, 2.05, 11.9, [2.1, 4.6, 5.2], row_h=0.52, font_size=10.5)
    box(slide, MARGIN, 5.35, 5.7, 0.3, "WHAT THE PAPER DOES SHOW", size=9.5, bold=True, color=TEAL_DARK)
    box(slide, MARGIN, 5.68, 5.7, 1.1,
        "Table 6: F1 saturates at low k (35.20 at k=1, 42.85 at k=3,\n"
        "43.45 at k=10). That motivates testing lower depth.",
        size=10.5, color=INK2, spacing=1.2)

    rect(slide, 6.75, 5.3, 5.8, 1.45, fill=INK, radius=0.05)
    box(slide, 7.0, 5.45, 5.3, 0.3, "NOT ESTABLISHED HERE", size=9.5, bold=True, color=TEAL_LIGHT)
    box(slide, 7.0, 5.75, 5.3, 0.9,
        "Exact published F1 · 30× token savings · full-benchmark\ngeneralisation · a causal latency gain.",
        size=10, color=RGBColor(0xCB, 0xD5, 0xE1), spacing=1.2)
    footer(slide, 7, total)
    add_notes(slide, """
Be explicit: our F1 is higher than the paper's, and that proves nothing because model, data, retrieval range, windowing, category mix and aggregation all differ. The paper's Table 6 is the motivation: performance saturates as k grows, 42.85 at k=3 and 43.45 at k=10, so testing a lower depth is a reasonable local experiment. The dark panel lists what we did not establish, including the 30x token claim, because token accounting is disabled upstream.
""")

    # ------------------------------------------------------------ 8 debug
    slide = add_slide(prs)
    header(slide, "07", "DEBUGGING & INHERITED LIMITS",
           "What broke, what we fixed, what remains")
    fixes = [
        ("LanceDB FTS", "0.41.0 removed Tantivy.\nPinned 0.25.3 + pylance; a smoke\nsearch verifies keyword hits.",
         "FIXED", TEAL),
        ("Legacy config import", "Category-5 path imported a root\nconfig module. Both conditions\nnow use unified settings.",
         "FIXED", TEAL),
        ("Inherited: stale index", "Tantivy index covers only the first\ninsertion batch. Kept in both\nconditions, disclosed.",
         "DISCLOSED", AMBER),
    ]
    x = MARGIN
    for title, detail, tag, accent in fixes:
        card(slide, x, 2.05, 3.85, 1.78, accent=accent)
        box(slide, x + 0.25, 2.24, 2.55, 0.3, title, size=12.5, bold=True, color=INK)
        chip(slide, x + 2.78, 2.24, 0.85, 0.26, tag,
             fill=TEAL_LIGHT if accent == TEAL else AMBER_LIGHT,
             color=TEAL_DARK if accent == TEAL else AMBER, size=7.5)
        box(slide, x + 0.25, 2.68, 3.35, 1.0, detail, size=9.5, color=MUTED, spacing=1.15)
        x += 4.02

    box(slide, MARGIN, 4.12, 5.6, 0.3, "RECOVERY ON 13 NOVEMBER", size=9.5, bold=True, color=SLATE)
    box(slide, MARGIN, 4.45, 5.75, 1.5,
        "Seed 5662 failed on 8 Nov (API errors, fallback answers,\nmissing results). Both runs were excluded and the whole\n"
        "pair was rerun with fresh memory; seeds 5660–5661 keep\ntheir original outputs. The later date is disclosed.",
        size=10, color=INK2, spacing=1.2)

    rect(slide, 6.9, 4.28, 5.65, 1.6, fill=CARD, line=BORDER, radius=0.05)
    box(slide, 7.15, 4.44, 5.1, 0.3, "THREATS TO VALIDITY", size=9.5, bold=True, color=ROSE)
    box(slide, 7.15, 4.72, 5.2, 1.15,
        "1 conversation · 20 questions · 3 trials · category 3 missing\n"
        "mutable model alias · fixed baseline-first order\n"
        "hosted-model non-determinism · paper/dependency drift\npilot overlap · no token or cost accounting",
        size=9.5, color=SLATE, spacing=1.25)
    footer(slide, 8, total)
    add_notes(slide, """
Three blockers. LanceDB 0.41 removed the Tantivy full-text interface, so keyword retrieval silently disappeared; pinning 0.25.3 with pylance fixed it and a smoke test confirmed a matching document is returned. The evaluator still imported a legacy config module in category-5 paths, which could fall back to the correct abstention answer; both conditions now use unified settings. The inherited limitation: the keyword index is not rebuilt after the first insertion batch, so keywords are incomplete; it is identical in both conditions and disclosed rather than hidden. Then the recovery and the validity threats.
""")

    # ------------------------------------------------------------ 9 end
    slide = add_slide(prs, dark=True)
    rect(slide, 0, 0, 0.18, SLIDE_H, fill=TEAL)
    header(slide, "08", "CONCLUSIONS", "Reproducible behavior, not a leaderboard win", dark=True)
    takeaways = [
        ("01", "The pipeline runs.", "Memory construction, planned hybrid retrieval,\nreflection and scoring execute end to end."),
        ("02", "The change is measurable.", "k=25→10 cuts context by 21.6 entries/question,\nF1 moves +2.51 pp but inconsistently."),
        ("03", "Broader claims need more.", "More conversations, category coverage,\ncounterbalanced order, usage logging."),
    ]
    y = 2.15
    for num, title, detail in takeaways:
        box(slide, MARGIN, y, 0.75, 0.55, num, size=26, bold=True, color=TEAL)
        box(slide, MARGIN + 0.85, y + 0.02, 9.8, 0.35, title, size=15, bold=True, color=WHITE)
        box(slide, MARGIN + 0.85, y + 0.4, 9.8, 0.7, detail, size=10, color=RGBColor(0xCB, 0xD5, 0xE1),
            spacing=1.2)
        y += 1.4
    rect(slide, MARGIN, 6.35, 11.9, 0.04, fill=RGBColor(0x33, 0x41, 0x55))
    box(slide, MARGIN, 6.55, 8.0, 0.3, f"{REPO}", size=10, color=TEAL_LIGHT, font=MONO)
    box(slide, SLIDE_W - MARGIN - 2.4, 6.55, 2.4, 0.3, "Questions welcome", size=10, color=MUTED,
        align=PP_ALIGN.RIGHT)
    footer(slide, 9, total, dark=True)
    add_notes(slide, """
Close on three points. The pipeline is reproducible end to end. The modification is measurable: less context, a small and inconsistent F1 move, no speedup. Anything broader needs more data, more categories, counterbalanced order and provider usage logging. Point to the repository for code, report, analysis tables and raw evidence instructions. Invite questions.
""")

    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output))

    # ------------------------------------------------------------ notes md
    notes_lines = [
        "# Zoom presentation script (target 12 minutes)",
        "",
        "Nine-slide deck: `presentation.pptx`. Numbers match `analysis/summary.json` and the 8-page report.",
        f"Repository: https://{REPO}",
        "",
    ]
    for index, slide in enumerate(prs.slides, start=1):
        notes_lines.extend([f"## Slide {index}: {SLIDE_TITLES[index - 1]}", "",
                            slide.notes_slide.notes_text_frame.text.strip(), ""])
    notes_path.write_text("\n".join(notes_lines))
    print(f"Wrote {output} and {notes_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis", type=Path, help="directory containing summary.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--notes", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads((args.analysis / "summary.json").read_text())
    if not summary.get("complete"):
        raise SystemExit("Refusing to build slides from an incomplete analysis")
    build(summary, args.output, args.notes)


if __name__ == "__main__":
    main()
