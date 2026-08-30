"""
Reporting Agent
Combines outputs from every other agent into:
1. A single 0-100 Trust Score
2. A bilingual (English + Urdu) plain-language summary
3. A downloadable PDF report with an "Insaaf Certified" badge line
"""

import os
from typing import Dict
from fpdf import FPDF
from datetime import datetime
import arabic_reshaper
from bidi.algorithm import get_display

from agents.translation_agent import TranslationAgent

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")
URDU_FONT_PATH = os.path.join(FONTS_DIR, "NotoNaskhArabic-Regular.ttf")

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
WATERMARK_SRC = os.path.join(ASSETS_DIR, "insaaf_watermark.png")
WATERMARK_FAINT = os.path.join(ASSETS_DIR, "insaaf_watermark_faint.png")
WATERMARK_OPACITY = 0.06  # 6% — visible but clearly behind all text

_watermark_path_cache: Dict[str, str] = {}


def _get_faint_watermark() -> str | None:
    """Return path to a pre-processed watermark PNG with opacity baked in.

    fpdf2 cannot set alpha on an arbitrary image, so we pre-multiply the
    alpha channel once with Pillow and cache the result on disk next to the
    source. Returns None if the source PNG is missing.
    """
    if not os.path.exists(WATERMARK_SRC):
        return None
    if _watermark_path_cache.get("path"):
        return _watermark_path_cache["path"]

    src_mtime = os.path.getmtime(WATERMARK_SRC)
    if (
        os.path.exists(WATERMARK_FAINT)
        and os.path.getmtime(WATERMARK_FAINT) >= src_mtime
    ):
        _watermark_path_cache["path"] = WATERMARK_FAINT
        return WATERMARK_FAINT

    from PIL import Image

    img = Image.open(WATERMARK_SRC).convert("RGBA")
    r, g, b, a = img.split()

    # The source PNG has a solid black background (RGB 0,0,0, alpha 255)
    # rather than true transparency. Treat pixels whose luminance is below
    # a threshold as "background" and zero their alpha so only the logo
    # mark itself remains as a watermark.
    import numpy as np

    rgb = np.array(img.convert("RGB"), dtype=np.int16)
    lum = rgb.max(axis=2)  # brightest channel ≈ perceived brightness
    # Smooth mask: 0 at black, ramps to 1 around the logo edge
    mask = np.clip((lum - 4) / 20.0, 0.0, 1.0)
    base_alpha = (mask * 255).astype(np.uint8)
    faded_alpha = (base_alpha * WATERMARK_OPACITY).astype(np.uint8)
    faded = Image.fromarray(np.dstack([np.array(r), np.array(g), np.array(b), faded_alpha]), "RGBA")
    faded.save(WATERMARK_FAINT)
    _watermark_path_cache["path"] = WATERMARK_FAINT
    return WATERMARK_FAINT


def shape_urdu_for_pdf(text: str) -> str:
    """
    Urdu/Arabic script needs two things a plain PDF library does not do
    automatically:
    1. Contextual letter joining (reshaping) - the same letter looks
       different at the start/middle/end of a word.
    2. Right-to-left visual reordering - Unicode stores logical order,
       but PDF rendering needs visual (display) order.

    arabic_reshaper handles (1), python-bidi handles (2). This same
    approach works for Arabic and Persian text too.
    """
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


class ReportingAgent:
    def __init__(self, intake_result: Dict, bias_result: Dict, explainability_result: Dict):
        self.intake_result = intake_result
        self.bias_result = bias_result
        self.explainability_result = explainability_result
        self.translator = TranslationAgent()

    def compute_trust_score(self) -> int:
        """
        Simple, transparent scoring formula (documented so judges can see
        the logic, not a black box):

        Start at 100.
        - Subtract 25 if Disparate Impact Ratio fails the 80% rule.
        - Subtract up to 25 based on how far Equal Opportunity Difference
          is from 0 (capped).
        - Subtract 15 if the protected attribute itself is a top predictive feature.
        """
        score = 100

        dir_data = self.bias_result.get("disparate_impact", {})
        if not dir_data.get("passes_80_percent_rule", True):
            score -= 25

        eod_data = self.bias_result.get("equal_opportunity")
        if eod_data:
            penalty = min(25, abs(eod_data.get("score", 0)) * 100)
            score -= penalty

        if self.explainability_result.get("protected_attribute_in_top_features"):
            score -= 15

        return max(0, round(score))

    def build_summary_english(self, trust_score: int, include_comparison: bool = True) -> str:
        bias_detected = self.bias_result.get("bias_detected", False)
        verdict = (
            "This system shows signs of bias against the unprivileged group."
            if bias_detected
            else "This system appears fair based on the metrics tested."
        )
        dir_data = self.bias_result["disparate_impact"]
        rule_status = "passes the 80 percent rule" if dir_data["passes_80_percent_rule"] else "fails the 80 percent rule"

        top_feature = None
        if self.explainability_result.get("top_features"):
            top_feature = self.explainability_result["top_features"][0]["feature"]

        summary = (
            f"Trust Score: {trust_score}/100.\n"
            f"{verdict}\n"
            f"Disparate Impact Ratio {rule_status} "
            f"(score: {dir_data['score']}).\n"
        )

        if include_comparison:
            group_def = self.bias_result.get("group_definition")
            if group_def:
                priv_str = ", ".join(group_def["privileged_values"])
                unpriv_str = ", ".join(group_def["unprivileged_values"])
                summary += f"When comparing {priv_str} against {unpriv_str}.\n"

        if top_feature:
            summary += f"The top contributing feature to the model's decisions is: {top_feature}.\n"

        return summary

    def _build_group_comparison(self) -> dict | None:
        """Return {en, ur} comparison clauses if group_definition is present."""
        group_def = self.bias_result.get("group_definition")
        if not group_def:
            return None

        priv_str = ", ".join(group_def["privileged_values"])
        unpriv_str = ", ".join(group_def["unprivileged_values"])

        en = f"Comparing: {priv_str} vs. {unpriv_str}"

        # Build Urdu clause by translating only the fixed keywords;
        # city/group names stay in their original script.
        when_en = "when comparing"
        against_en = "against"
        when_ur = "جب موازنہ کیا جائے"
        against_ur = "کے خلاف"
        ur = f"{when_ur} {priv_str} {against_ur} {unpriv_str}"

        return {"en": en, "ur": ur}

    def build_summaries(self, trust_score: int) -> Dict:
        summary_en = self.build_summary_english(trust_score, include_comparison=True)

        base_en = self.build_summary_english(trust_score, include_comparison=False)
        base_ur = self.translator.translate(base_en)["text"]

        group_comparison = self._build_group_comparison()
        if group_comparison:
            summary_ur = f"{base_ur}\n{group_comparison['ur']}.\n"
        else:
            summary_ur = base_ur

        return {
            "summary_english": summary_en,
            "summary_urdu": summary_ur,
            "group_comparison": group_comparison,
        }

    def assemble_report(self, trust_score: int, summaries: Dict) -> Dict:
        result = {
            "trust_score": trust_score,
            "certified": trust_score >= 70,
            "summary_english": summaries["summary_english"],
            "summary_urdu": summaries["summary_urdu"],
            "generated_at": datetime.utcnow().isoformat(),
        }
        if summaries.get("group_comparison"):
            result["group_comparison"] = summaries["group_comparison"]
        return result

    def run(self) -> Dict:
        trust_score = self.compute_trust_score()
        return self.assemble_report(trust_score, self.build_summaries(trust_score))

    def _draw_pdf_seal(self, pdf: FPDF, cx: float, cy: float, radius: float, certified: bool) -> None:
        """Draw a certificate seal: outer solid ring, inner dashed ring, centre mark."""
        GREEN, RUST = (46, 107, 79), (156, 62, 46)
        r, g, b = GREEN if certified else RUST

        pdf.set_draw_color(r, g, b)
        pdf.set_line_width(0.6)
        pdf.ellipse(cx - radius, cy - radius, radius * 2, radius * 2, style="D")

        inner_r = radius * 0.78
        pdf.set_line_width(0.3)
        try:
            pdf.set_dash_pattern(dash=1.5, gap=2)
        except Exception:
            pass
        pdf.ellipse(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2, style="D")
        try:
            pdf.set_dash_pattern()
        except Exception:
            pass

        # Centre mark — checkmark (certified) or exclamation mark (not certified)
        pdf.set_line_width(1.2)
        if certified:
            x1, y1 = cx - radius * 0.35, cy + radius * 0.05
            x2, y2 = cx - radius * 0.08, cy + radius * 0.32
            x3, y3 = cx + radius * 0.42, cy - radius * 0.32
            pdf.line(x1, y1, x2, y2)
            pdf.line(x2, y2, x3, y3)
        else:
            pdf.set_font("Helvetica", "B", int(radius * 1.4))
            pdf.set_text_color(r, g, b)
            pdf.set_xy(cx - radius, cy - radius * 0.65)
            pdf.cell(radius * 2, radius * 1.3, "!", align="C")

        # Restore text colour to black for subsequent text
        pdf.set_text_color(0, 0, 0)
        pdf.set_draw_color(0, 0, 0)

    def _stamp_watermark(self, pdf: FPDF) -> None:
        """Place a large, faint, centered watermark behind page content."""
        wm = _get_faint_watermark()
        if not wm:
            return
        # Cover ~60% of page width, centered, preserving aspect ratio.
        wm_w = pdf.w * 0.6
        wm_x = (pdf.w - wm_w) / 2
        wm_y = (pdf.h - wm_w) / 2  # square bounding box keeps it centered vertically
        pdf.image(wm, x=wm_x, y=wm_y, w=wm_w)

    def generate_pdf(self, report_data: Dict, output_path: str) -> str:
        pdf = FPDF()
        pdf.add_page()
        self._stamp_watermark(pdf)
        pdf.set_font("Helvetica", "B", 18)
        pdf.cell(0, 12, "Insaaf AI - Trust Report", ln=True)

        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, f"Generated: {report_data['generated_at']}", ln=True)
        pdf.ln(4)

        # Trust Score
        certified = report_data["trust_score"] >= 70
        pdf.set_font("Helvetica", "B", 40)
        pdf.set_text_color(46, 107, 79) if certified else pdf.set_text_color(156, 62, 46)
        pdf.cell(0, 20, f"Trust Score: {report_data['trust_score']}/100", ln=True)
        pdf.set_text_color(0, 0, 0)

        # Group comparison — clearly visible near the Trust Score
        group_comparison = report_data.get("group_comparison")
        if group_comparison:
            pdf.set_font("Helvetica", "I", 11)
            pdf.set_text_color(60, 60, 60)
            pdf.cell(0, 7, group_comparison["en"], ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        pdf.ln(4)

        # Circular seal graphic — centred, placed prominently near the score
        seal_radius = 14
        cx = pdf.w / 2
        cy = pdf.get_y() + seal_radius + 2
        self._draw_pdf_seal(pdf, cx, cy, seal_radius, certified)

        # Status label below the seal
        pdf.set_y(cy + seal_radius + 4)
        pdf.set_font("Helvetica", "B", 12)
        status_color = (46, 107, 79) if certified else (156, 62, 46)
        pdf.set_text_color(*status_color)
        pdf.cell(0, 8, "INSAAF CERTIFIED" if certified else "REVIEW REQUIRED", align="C", ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(6)

        # English summary
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 7, report_data["summary_english"])
        pdf.ln(4)

        # Urdu summary
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Urdu Summary:", ln=True)

        # Urdu script needs a Unicode-capable font - Helvetica/Arial cannot
        # render it. We bundle Noto Nastaliq Urdu (free, OFL-licensed, from
        # Google Fonts) in backend/fonts/ for exactly this reason.
        if os.path.exists(URDU_FONT_PATH):
            pdf.add_font("NotoNastaliqUrdu", "", URDU_FONT_PATH)
            pdf.set_font("NotoNastaliqUrdu", "", 14)
        else:
            pdf.set_font("Helvetica", "", 11)

        display_text = shape_urdu_for_pdf(report_data["summary_urdu"]) if os.path.exists(URDU_FONT_PATH) else report_data["summary_urdu"]
        pdf.multi_cell(0, 10, display_text, align="R")

        pdf.output(output_path)
        return output_path
