"""
analyzer.py — Core AI analysis engine for DrawingIQ
Handles prompt construction, OpenAI calls, result parsing, and error recovery.
"""

import json
import os
from openai import OpenAI


MODEL = "gpt-4o"
MAX_TOKENS = 3000


DETAIL_INSTRUCTIONS = {
    "Quick Scan": (
        "Focus only on critical flags, part name, material, and the top 5 dimensions. "
        "Be concise. Skip GD&T and machining sequence."
    ),
    "Standard": (
        "Provide a complete analysis including all visible dimensions, tolerances, "
        "flags, GD&T callouts, and manufacturing notes."
    ),
    "Deep Review": (
        "Provide an exhaustive analysis. Include all dimensions, every GD&T callout, "
        "surface finish specifications, material traceability/spec numbers, "
        "suggested machining sequence, tooling considerations, potential cost drivers, "
        "and alternative material recommendations if applicable."
    ),
}

DISCIPLINE_CONTEXT = {
    "Auto-Detect": "",
    "Mechanical / Machining": (
        "This is a mechanical/machining drawing. Focus on tolerances, fits, "
        "surface finishes, GD&T, and machinability. Flag any tight tolerances "
        "(±0.005\" or ±0.1mm or tighter)."
    ),
    "Structural / Civil": (
        "This is a structural/civil drawing. Focus on load-bearing members, "
        "connection details, material grades (ASTM specs), weld symbols, "
        "and code compliance notes (AISC, ACI)."
    ),
    "Electrical / Schematic": (
        "This is an electrical schematic or wiring diagram. Identify components, "
        "circuit topology, voltage/current ratings, wire gauges, and safety flags."
    ),
    "Architectural": (
        "This is an architectural drawing. Extract room dimensions, scale, "
        "materials, building codes referenced, and construction notes."
    ),
    "PCB / Electronics": (
        "This is a PCB or electronics drawing. Focus on component designators, "
        "trace widths, layer stackup if visible, impedance requirements, and IPC standards."
    ),
    "Welding / Fabrication": (
        "This is a welding or fabrication drawing. Extract weld symbols, joint types, "
        "filler metal specs (AWS), pre/post heat requirements, and inspection notes."
    ),
}

JSON_SCHEMA = """{
  "drawing_type": "Mechanical | Structural | Electrical | Architectural | PCB | Welding | Assembly | Unknown",
  "part_name": "string",
  "part_number": "string or null",
  "revision": "string or null",
  "scale": "string or null",
  "sheet_info": "e.g. Sheet 1 of 3, or null",
  "material": "string",
  "material_spec": "e.g. ASTM A36, 6061-T6, or null",
  "surface_finish": "string or null",
  "heat_treatment": "string or null",
  "weight_estimate": "string or null",
  "confidence_score": 0-100,
  "dimensions": [
    {"feature": "string", "value": "string", "tolerance": "string or null", "unit": "mm/in/deg/etc", "is_critical": true/false}
  ],
  "tolerances": [
    {"type": "string", "value": "string", "is_tight": true/false, "note": "string"}
  ],
  "gdt_callouts": [
    {"symbol": "⊙/⊕/◎/⊡ etc", "feature": "string", "value": "string", "datum": "string or null"}
  ],
  "flags": [
    {"severity": "critical|warning|info", "category": "string", "description": "string", "recommendation": "string"}
  ],
  "manufacturing_concerns": ["string"],
  "machinist_notes": "2-4 sentence paragraph written as an experienced machinist would explain this part to a junior machinist",
  "estimated_complexity": "Low | Medium | High | Very High",
  "recommended_processes": ["string"],
  "standards_referenced": ["string"],
  "related_parts": ["string"]
}"""


def build_prompt(discipline: str, detail_level: str) -> str:
    discipline_ctx = DISCIPLINE_CONTEXT.get(discipline, "")
    detail_ctx = DETAIL_INSTRUCTIONS.get(detail_level, DETAIL_INSTRUCTIONS["Standard"])

    return f"""You are a senior manufacturing engineer and drawing reviewer with 25+ years of experience across mechanical, structural, electrical, and fabrication disciplines.

Analyze the engineering drawing in the image and respond ONLY with a valid JSON object matching the schema below. No markdown, no code fences, no preamble — raw JSON only.

{f'DISCIPLINE CONTEXT: {discipline_ctx}' if discipline_ctx else ''}
DETAIL LEVEL: {detail_ctx}

RULES:
- Extract every visible dimension, tolerance, and annotation
- Flag tight tolerances, missing callouts, ambiguous notes, and manufacturability concerns
- confidence_score reflects how clearly readable the drawing is (100 = perfect clarity)
- If a field is not visible or applicable, use null (not empty string)
- flags severity: "critical" = will cause manufacturing failure, "warning" = needs attention, "info" = FYI

JSON SCHEMA:
{JSON_SCHEMA}"""


def analyze_image(
    b64_image: str,
    mime: str,
    discipline: str,
    detail_level: str,
    api_key: str,
) -> dict:
    """
    Analyze a single drawing image. Returns parsed result dict.
    Raises on API error. Handles JSON parse failures gracefully.
    """
    client = OpenAI(api_key=api_key)
    prompt = build_prompt(discipline, detail_level)

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=0.05,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime};base64,{b64_image}",
                        "detail": "high",
                    }
                }
            ]
        }]
    )

    raw = response.choices[0].message.content.strip()
    return _parse_response(raw)


def analyze_pdf_pages(
    pages: list[dict],
    discipline: str,
    detail_level: str,
    api_key: str,
) -> dict:
    """
    Analyze a multi-page PDF. Each page gets analyzed, then results are merged.
    The first page (usually the main view) gets full analysis.
    Subsequent pages (detail views, sections) get merged in.
    """
    if not pages:
        raise ValueError("No pages provided.")

    # Analyze first page fully
    primary = analyze_image(pages[0]["b64"], pages[0]["mime"], discipline, detail_level, api_key)

    # Analyze remaining pages and merge
    for page in pages[1:]:
        try:
            secondary = analyze_image(page["b64"], page["mime"], discipline, detail_level, api_key)
            primary = _merge_results(primary, secondary, page["page"])
        except Exception:
            continue  # Don't fail whole job if one page fails

    primary["page_count"] = len(pages)
    return primary


def _merge_results(primary: dict, secondary: dict, page_num: int) -> dict:
    """Merge secondary page analysis into primary, appending new findings."""
    # Merge dimensions (deduplicate by feature name)
    existing_features = {d.get("feature", "").lower() for d in primary.get("dimensions", [])}
    for dim in secondary.get("dimensions", []):
        if dim.get("feature", "").lower() not in existing_features:
            primary.setdefault("dimensions", []).append(dim)
            existing_features.add(dim.get("feature", "").lower())

    # Merge flags (deduplicate by description)
    existing_flags = {f.get("description", "").lower()[:50] for f in primary.get("flags", [])}
    for flag in secondary.get("flags", []):
        key = flag.get("description", "").lower()[:50]
        if key not in existing_flags:
            flag["source_page"] = page_num
            primary.setdefault("flags", []).append(flag)
            existing_flags.add(key)

    # Merge GD&T callouts
    existing_gdt = {g.get("value", "") for g in primary.get("gdt_callouts", [])}
    for gdt in secondary.get("gdt_callouts", []):
        if gdt.get("value", "") not in existing_gdt:
            primary.setdefault("gdt_callouts", []).append(gdt)

    # Merge processes
    existing_procs = set(primary.get("recommended_processes", []))
    for proc in secondary.get("recommended_processes", []):
        if proc not in existing_procs:
            primary.setdefault("recommended_processes", []).append(proc)

    # Merge manufacturing concerns
    existing_concerns = set(primary.get("manufacturing_concerns", []))
    for c in secondary.get("manufacturing_concerns", []):
        if c not in existing_concerns:
            primary.setdefault("manufacturing_concerns", []).append(c)
            existing_concerns.add(c)

    # Keep highest confidence score
    sec_conf = secondary.get("confidence_score", 0)
    if sec_conf and sec_conf > primary.get("confidence_score", 0):
        primary["confidence_score"] = sec_conf

    return primary


def _parse_response(raw: str) -> dict:
    """Parse raw LLM output to dict. Handles markdown fences."""
    text = raw.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object within the text
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        # Last resort: return error result
        return {
            "drawing_type": "Unknown",
            "part_name": "Parse Error",
            "material": "Unknown",
            "confidence_score": 0,
            "flags": [{
                "severity": "critical",
                "category": "Parse Error",
                "description": "Could not parse structured response from AI.",
                "recommendation": "Try again or switch to a different detail level."
            }],
            "dimensions": [],
            "gdt_callouts": [],
            "manufacturing_concerns": [],
            "machinist_notes": "Analysis failed to parse. Raw output stored for review.",
            "estimated_complexity": "Unknown",
            "recommended_processes": [],
            "_raw_response": raw[:2000],
        }
