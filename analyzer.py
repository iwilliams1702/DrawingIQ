# Copyright (c) 2026 Isaiah Williams / DrawingIQ
# All rights reserved. Unauthorized copying, modification,
# or distribution of this software is strictly prohibited.




"""
analyzer.py — Core AI analysis engine for DrawingIQ
Zero-hallucination prompting, strict grounding, quote estimation, and extended feature set.
"""

import json
import os
from openai import OpenAI

MODEL      = "gpt-4o"
MAX_TOKENS = 4000


# ── Detail level instructions ──────────────────────────────────────────────────
DETAIL_INSTRUCTIONS = {
    "Quick Scan": (
        "Extract ONLY what is explicitly and clearly visible: part name, material, "
        "drawing type, and up to 5 dimensions with their tolerances. "
        "Do NOT infer, estimate, or guess anything not directly readable in the drawing. "
        "Skip GD&T and machining sequence unless clearly labeled."
    ),
    "Standard": (
        "Extract all clearly visible dimensions, tolerances, flags, GD&T callouts, "
        "and manufacturing notes. Only report what is directly readable. "
        "If something is partially obscured or ambiguous, mark it with is_estimated=true "
        "and note the uncertainty."
    ),
    "Deep Review": (
        "Perform exhaustive extraction of every readable detail: all dimensions, "
        "every GD&T callout, surface finish specs, material spec numbers, "
        "title block fields, notes, and revision history if visible. "
        "Suggest machining sequence and tooling only if the part geometry clearly "
        "supports those conclusions. Mark ALL inferred fields with is_estimated=true."
    ),
}

# ── Discipline context ─────────────────────────────────────────────────────────
DISCIPLINE_CONTEXT = {
    "Auto-Detect": "",
    "Mechanical / Machining": (
        "This is a mechanical/machining drawing. Focus on tolerances, fits, "
        "surface finishes, GD&T, and machinability. "
        "Flag tight tolerances (±0.005\" or ±0.1mm or tighter) only if explicitly shown."
    ),
    "Structural / Civil": (
        "This is a structural/civil drawing. Focus on load-bearing members, "
        "connection details, material grades (ASTM specs), weld symbols, "
        "and code compliance notes (AISC, ACI). Only flag issues explicitly shown."
    ),
    "Electrical / Schematic": (
        "This is an electrical schematic or wiring diagram. Identify components, "
        "circuit topology, voltage/current ratings, wire gauges, and safety flags "
        "that are explicitly labeled."
    ),
    "Architectural": (
        "This is an architectural drawing. Extract room dimensions, scale, "
        "materials, building codes, and construction notes that are explicitly shown."
    ),
    "PCB / Electronics": (
        "This is a PCB or electronics drawing. Focus on component designators, "
        "trace widths, layer stackup, impedance requirements, and IPC standards "
        "only as explicitly labeled."
    ),
    "Welding / Fabrication": (
        "This is a welding or fabrication drawing. Extract weld symbols, joint types, "
        "filler metal specs (AWS), pre/post heat requirements, and inspection notes "
        "that are explicitly shown in the drawing."
    ),
}

# ── JSON schema ────────────────────────────────────────────────────────────────
JSON_SCHEMA = """{
  "drawing_type": "Mechanical|Structural|Electrical|Architectural|PCB|Welding|Assembly|Unknown",
  "part_name": "string or null — ONLY from title block",
  "part_number": "string or null — ONLY from title block",
  "revision": "string or null — ONLY from title block",
  "scale": "string or null — ONLY if explicitly shown",
  "sheet_info": "string or null — e.g. Sheet 1 of 3",
  "material": "string or null — ONLY if explicitly called out",
  "material_spec": "string or null — e.g. ASTM A36, 6061-T6",
  "surface_finish": "string or null — ONLY if explicitly shown",
  "heat_treatment": "string or null — ONLY if explicitly shown",
  "weight_estimate": "string or null — ONLY if shown on drawing",
  "units": "inches|mm|mixed|unknown",
  "confidence_score": 0-100,
  "drawing_clarity": "Clear|Partially Legible|Difficult to Read|Unclear",
  "title_block_found": true/false,
  "dimensions": [
    {
      "feature": "string — exact label from drawing",
      "value": "string — exact value as written",
      "tolerance": "string or null — exact as written, null if not shown",
      "unit": "mm|in|deg|etc",
      "is_critical": true/false,
      "is_estimated": false,
      "location_hint": "string or null — e.g. top view, section A-A"
    }
  ],
  "gdt_callouts": [
    {
      "symbol": "string — exact GD&T symbol",
      "feature": "string",
      "value": "string — exact as written",
      "datum": "string or null",
      "is_estimated": false
    }
  ],
  "flags": [
    {
      "severity": "critical|warning|info",
      "category": "string",
      "description": "string — describe ONLY what is visible, not assumptions",
      "recommendation": "string",
      "evidence": "string — quote the exact text or callout that triggered this flag"
    }
  ],
  "manufacturing_concerns": ["string — only concerns directly evidenced by the drawing"],
  "machinist_notes": "string — written as an experienced machinist briefing a junior. Only reference visible details.",
  "estimated_complexity": "Low|Medium|High|Very High",
  "complexity_reasoning": "string — brief explanation based on visible features",
  "recommended_processes": ["string — only processes clearly required by the drawing"],
  "standards_referenced": ["string — only standards explicitly named in the drawing"],
  "setup_count_estimate": "integer or null — estimated number of setups/operations",
  "raw_notes": ["string — verbatim copy of any general notes visible in the drawing"],
  "revision_history": ["string — verbatim revision entries if visible"],
  "related_parts": ["string — part numbers explicitly referenced"],
  "estimated_material_volume_cm3": "number or null — only if all outer dimensions visible",
  "tolerance_stack_risk": "Low|Medium|High|Unknown",
  "page_count": 1
}"""


# ── Zero-hallucination system prompt ──────────────────────────────────────────
SYSTEM_PROMPT = """You are a senior manufacturing engineer and drawing reviewer with 25+ years of experience.

CRITICAL ACCURACY RULES — FOLLOW THESE ABOVE ALL ELSE:
1. ONLY extract information that is EXPLICITLY, CLEARLY VISIBLE in the drawing.
2. If a field is not visible, not legible, or not present — set it to null. NEVER guess or infer.
3. NEVER fabricate part numbers, dimensions, tolerances, materials, or standards.
4. NEVER add flags, warnings, or concerns that are not directly evidenced by visible content.
5. If the drawing is blurry, low-res, or a photo at an angle — lower confidence_score accordingly and mark affected fields with is_estimated=true.
6. Dimensions: copy the EXACT value as written. Do not convert units unless the drawing does.
7. Tolerances: only report what is explicitly written. Do not apply general machining tolerances.
8. Flags: only raise a flag if you can quote the specific text, callout, or missing element that justifies it.
9. If you cannot read a value clearly, set it to null — do not guess.
10. machinist_notes must reference ONLY details visible in the drawing.

WHAT COUNTS AS A FLAG:
- critical: a conflict between dimensions, a missing required callout (e.g. no tolerance on a feature marked critical), or something that would directly cause a manufacturing failure
- warning: a callout that is ambiguous, partially illegible, or potentially problematic
- info: a note or callout that the machinist should be aware of but does not indicate a problem
- DO NOT flag things that are normal, standard, or assumed — only flag actual visible issues

Respond ONLY with a valid JSON object. No markdown, no code fences, no preamble."""


def build_prompt(discipline: str, detail_level: str) -> str:
    discipline_ctx = DISCIPLINE_CONTEXT.get(discipline, "")
    detail_ctx     = DETAIL_INSTRUCTIONS.get(detail_level, DETAIL_INSTRUCTIONS["Standard"])
    return (
        f"{f'DISCIPLINE: {discipline_ctx}' + chr(10) if discipline_ctx else ''}"
        f"DETAIL LEVEL: {detail_ctx}\n\n"
        f"JSON SCHEMA TO FOLLOW:\n{JSON_SCHEMA}"
    )


# ── Single image analysis ──────────────────────────────────────────────────────
def analyze_image(
    b64_image: str,
    mime: str,
    discipline: str,
    detail_level: str,
    api_key: str,
) -> dict:
    client = OpenAI(api_key=api_key)
    prompt = build_prompt(discipline, detail_level)

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=0,          # Zero temperature = maximum determinism, no creativity
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url":    f"data:{mime};base64,{b64_image}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
    )

    raw = response.choices[0].message.content.strip()
    return _parse_response(raw)


# ── PDF multi-page analysis ────────────────────────────────────────────────────
def analyze_pdf_pages(
    pages: list[dict],
    discipline: str,
    detail_level: str,
    api_key: str,
) -> dict:
    if not pages:
        raise ValueError("No pages provided.")

    primary = analyze_image(
        pages[0]["b64"], pages[0]["mime"], discipline, detail_level, api_key
    )

    for page in pages[1:]:
        try:
            secondary = analyze_image(
                page["b64"], page["mime"], discipline, detail_level, api_key
            )
            primary = _merge_results(primary, secondary, page["page"])
        except Exception:
            continue

    primary["page_count"] = len(pages)
    return primary


# ── Quote estimation engine ────────────────────────────────────────────────────
def estimate_quote(result: dict, shop_rates: dict) -> dict:
    """
    Generate a cost estimate based on analysis result and shop-provided rates.

    shop_rates dict expected keys:
        machine_rate_per_hr   : float  ($/hr for CNC machine time)
        labor_rate_per_hr     : float  ($/hr for machinist labor)
        material_cost_per_kg  : float  ($/kg raw material)
        material_density_kg_m3: float  (density for material, e.g. 2700 for Al)
        overhead_pct          : float  (overhead as %, e.g. 15.0)
        profit_margin_pct     : float  (profit margin %, e.g. 20.0)
        setup_cost            : float  (fixed setup cost per job)
        quantity              : int    (number of parts)
    """
    complexity_hrs = {
        "Low":       {"machine": 0.5,  "labor": 0.75},
        "Medium":    {"machine": 1.5,  "labor": 2.0},
        "High":      {"machine": 4.0,  "labor": 5.0},
        "Very High": {"machine": 10.0, "labor": 12.0},
        "Unknown":   {"machine": 2.0,  "labor": 2.5},
    }

    complexity   = result.get("estimated_complexity", "Unknown")
    hrs          = complexity_hrs.get(complexity, complexity_hrs["Unknown"])
    setup_count  = result.get("setup_count_estimate") or 1
    qty          = max(1, int(shop_rates.get("quantity", 1)))

    # Adjust hours for setups
    machine_hrs = hrs["machine"] * setup_count
    labor_hrs   = hrs["labor"]   * setup_count

    # Per-part costs
    machine_cost = machine_hrs * float(shop_rates.get("machine_rate_per_hr", 0))
    labor_cost   = labor_hrs   * float(shop_rates.get("labor_rate_per_hr",   0))

    # Material cost
    vol_cm3    = result.get("estimated_material_volume_cm3")
    mat_cost   = 0.0
    mat_note   = "Volume not calculable from drawing"
    if vol_cm3:
        density  = float(shop_rates.get("material_density_kg_m3", 2700)) / 1_000_000  # kg/cm3
        weight   = vol_cm3 * density
        mat_cost = weight * float(shop_rates.get("material_cost_per_kg", 0))
        mat_note = f"{vol_cm3:.1f} cm³ × {density*1e6:.0f} kg/m³ = {weight:.3f} kg"

    setup_cost   = float(shop_rates.get("setup_cost", 0))
    subtotal_per = machine_cost + labor_cost + mat_cost
    subtotal_job = subtotal_per * qty + setup_cost

    overhead_pct = float(shop_rates.get("overhead_pct",     0)) / 100
    profit_pct   = float(shop_rates.get("profit_margin_pct", 0)) / 100

    overhead_amt = subtotal_job * overhead_pct
    profit_amt   = (subtotal_job + overhead_amt) * profit_pct
    total        = subtotal_job + overhead_amt + profit_amt
    per_part     = total / qty if qty else total

    return {
        "quantity":              qty,
        "complexity":            complexity,
        "setup_count":           setup_count,
        "machine_hours_per_part": round(machine_hrs, 2),
        "labor_hours_per_part":   round(labor_hrs,   2),
        "machine_cost":          round(machine_cost, 2),
        "labor_cost":            round(labor_cost,   2),
        "material_cost":         round(mat_cost,     2),
        "material_note":         mat_note,
        "setup_cost":            round(setup_cost,   2),
        "subtotal_per_part":     round(subtotal_per, 2),
        "overhead_amount":       round(overhead_amt, 2),
        "profit_amount":         round(profit_amt,   2),
        "total_job_cost":        round(total,        2),
        "price_per_part":        round(per_part,     2),
        "rates_used":            shop_rates,
        "disclaimer": (
            "This estimate is based on complexity heuristics and shop-provided rates. "
            "Actual costs may vary based on specific tooling, fixturing, material availability, "
            "and machinist experience. Always review with your team before quoting to a customer."
        ),
    }


# ── Result merge (multi-page PDFs) ────────────────────────────────────────────
def _merge_results(primary: dict, secondary: dict, page_num: int) -> dict:
    existing_features = {
        d.get("feature", "").lower()
        for d in primary.get("dimensions", [])
    }
    for dim in secondary.get("dimensions", []):
        if dim.get("feature", "").lower() not in existing_features:
            primary.setdefault("dimensions", []).append(dim)
            existing_features.add(dim.get("feature", "").lower())

    existing_flags = {
        f.get("description", "").lower()[:50]
        for f in primary.get("flags", [])
    }
    for flag in secondary.get("flags", []):
        key = flag.get("description", "").lower()[:50]
        if key not in existing_flags:
            flag["source_page"] = page_num
            primary.setdefault("flags", []).append(flag)
            existing_flags.add(key)

    existing_gdt = {g.get("value", "") for g in primary.get("gdt_callouts", [])}
    for gdt in secondary.get("gdt_callouts", []):
        if gdt.get("value", "") not in existing_gdt:
            primary.setdefault("gdt_callouts", []).append(gdt)

    existing_procs = set(primary.get("recommended_processes", []))
    for proc in secondary.get("recommended_processes", []):
        if proc not in existing_procs:
            primary.setdefault("recommended_processes", []).append(proc)

    existing_concerns = set(primary.get("manufacturing_concerns", []))
    for c in secondary.get("manufacturing_concerns", []):
        if c not in existing_concerns:
            primary.setdefault("manufacturing_concerns", []).append(c)
            existing_concerns.add(c)

    # Merge raw notes
    existing_notes = set(primary.get("raw_notes", []))
    for n in secondary.get("raw_notes", []):
        if n not in existing_notes:
            primary.setdefault("raw_notes", []).append(n)
            existing_notes.add(n)

    sec_conf = secondary.get("confidence_score", 0)
    if sec_conf and sec_conf > primary.get("confidence_score", 0):
        primary["confidence_score"] = sec_conf

    return primary


# ── Response parser ────────────────────────────────────────────────────────────
def _parse_response(raw: str) -> dict:
    text = raw.strip()

    if text.startswith("```"):
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        text  = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

    return {
        "drawing_type":       "Unknown",
        "part_name":          None,
        "material":           None,
        "confidence_score":   0,
        "drawing_clarity":    "Unclear",
        "title_block_found":  False,
        "flags": [{
            "severity":       "critical",
            "category":       "Parse Error",
            "description":    "AI returned an unstructured response. No data extracted.",
            "recommendation": "Re-upload a cleaner scan or try a different detail level.",
            "evidence":       raw[:300],
        }],
        "dimensions":              [],
        "gdt_callouts":            [],
        "manufacturing_concerns":  [],
        "machinist_notes":         "Analysis could not be parsed. Please retry.",
        "estimated_complexity":    "Unknown",
        "recommended_processes":   [],
        "standards_referenced":    [],
        "raw_notes":               [],
        "tolerance_stack_risk":    "Unknown",
        "_raw_response":           raw[:2000],
    }