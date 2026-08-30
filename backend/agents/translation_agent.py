"""
Translation Agent
Converts the English findings summary into Urdu.

Production path (recommended in Qoder once you have internet + a free
Hugging Face inference token): call the free Hugging Face Inference API
for facebook/nllb-200-distilled-600M or Helsinki-NLP/opus-mt-en-ur.

Local/offline fallback: a phrase-substitution dictionary covering the
fixed vocabulary this app actually generates (trust score, bias detected,
feature names, etc.) so the demo works with zero network dependency and
zero cost even if the HF API is unreachable during judging.

Swap USE_HF_API to True and set HF_API_TOKEN as an environment variable
once you have a free Hugging Face token.
"""

import os
import requests
from typing import Dict

USE_HF_API = False
HF_API_URL = "https://api-inference.huggingface.co/models/Helsinki-NLP/opus-mt-en-ur"
HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")

# Fallback phrase dictionary - covers the fixed report vocabulary.
# Extend this as you add more report sentences.
FALLBACK_DICTIONARY = {
    "Trust Score": "اعتماد اسکور",
    "Bias detected": "تعصب کا پتہ چلا",
    "No significant bias detected": "کوئی نمایاں تعصب نہیں ملا",
    "Disparate Impact Ratio": "غیر مساوی اثر کا تناسب",
    "Equal Opportunity Difference": "مساوی مواقع کا فرق",
    "passes the 80 percent rule": "80 فیصد اصول پر پورا اترتا ہے",
    "fails the 80 percent rule": "80 فیصد اصول پر پورا نہیں اترتا",
    "when comparing": "جب موازنہ کیا جائے",
    "against": "کے خلاف",
    "This system shows signs of bias against the unprivileged group.": (
        "یہ نظام کمزور گروہ کے خلاف تعصب کے آثار ظاہر کرتا ہے۔"
    ),
    "This system appears fair based on the metrics tested.": (
        "جانچے گئے پیمانوں کی بنیاد پر یہ نظام منصفانہ معلوم ہوتا ہے۔"
    ),
    "The top contributing feature to the model's decisions is:": (
        "ماڈل کے فیصلوں میں سب سے زیادہ اثر انداز عنصر ہے:"
    ),
}


class TranslationAgent:
    def __init__(self):
        pass

    def _translate_via_api(self, text: str) -> str:
        response = requests.post(
            HF_API_URL,
            headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
            json={"inputs": text},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        return data[0]["translation_text"]

    def _translate_via_fallback(self, text: str) -> str:
        translated = text
        # Process longer phrases first so a short entry like "against"
        # doesn't corrupt a longer full-sentence entry that contains it.
        for en_phrase, ur_phrase in sorted(
            FALLBACK_DICTIONARY.items(), key=lambda kv: len(kv[0]), reverse=True
        ):
            if en_phrase in translated:
                translated = translated.replace(en_phrase, ur_phrase)
        return translated

    def translate(self, text: str) -> Dict:
        if USE_HF_API and HF_API_TOKEN:
            try:
                return {"status": "success", "source": "huggingface_api", "text": self._translate_via_api(text)}
            except Exception:
                pass  # fall through to offline fallback, never crash the pipeline

        return {
            "status": "success",
            "source": "offline_fallback_dictionary",
            "text": self._translate_via_fallback(text),
        }
