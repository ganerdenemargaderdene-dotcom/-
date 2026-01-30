from __future__ import annotations

from typing import Any, Dict, List, Optional, Text
import os
import yaml

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher


def _norm(raw: Optional[str]) -> Optional[str]:
    return raw.strip().upper() if raw else None


def _project_root() -> str:
    # Rasa-г ажиллуулж байгаа төслийн root хавтас гэж үзнэ
    return os.getcwd()


def _load_dun_yml() -> Dict[str, Any]:
    path = os.path.join(_project_root(), "dun.yml")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _builtin_grade_explanations() -> Dict[str, Dict[str, str]]:
    # Зураг дээр байсан (NA, F, I, E, NC, CR, R, W, NR, S, U) тайлбаруудыг богино, ойлгомжтой байдлаар MN+EN болгож оруулсан.
    # (G, WF, CA, RC гэх мэт нь зураг дээр байхгүй тул dun.yml -> codes хэсэгт нэмэхийг зөвлөе.)
    return {
        "NA": {
            "mn": "Одоогоор дүнг гаргаагүй.",
            "en": "No grade has been issued yet.",
        },
        "F": {
            "mn": "0–59 оноонд харгалзах үсгэн тэмдэглэгээ.",
            "en": "Letter grade corresponding to 0–59 points.",
        },
        "I": {
            "mn": "Хүндэтгэн үзэх шалтгаанаар явцын үнэлгээ дутуу бөгөөд улирлын шалгалтад орж чадаагүй үед хэрэглэнэ.",
            "en": "Used when coursework is incomplete and the student could not take the final exam due to an excused reason.",
        },
        "E": {
            "mn": "Хүндэтгэн үзэх шалтгаанаар улирлын шалгалтанд ороогүй тохиолдолд хэрэглэнэ.",
            "en": "Used when the student did not take the final exam due to an excused reason.",
        },
        "NC": {
            "mn": "Багц цаг тооцохгүй бөгөөд уг хичээлийг оноотой судалсан гэсэн тэмдэглэгээ.",
            "en": "Credits are not counted, but indicates the course was taken for a graded result.",
        },
        "CR": {
            "mn": "Өөр сургуулийн багц цагийг шилжүүлэн тооцох үед хэрэглэнэ.",
            "en": "Used when transferring credits from another institution.",
        },
        "R": {
            "mn": "Тухайн хичээлийг амжилттай судалсан ч тодорхой шаардлагаар дахин судлах хүсэлт гаргасан тохиолдолд тэмдэглэнэ.",
            "en": "Marked when the course was completed successfully, but the student requests to retake it due to specific requirements.",
        },
        "W": {
            "mn": "Хичээлийг цаашид судлах боломжгүй эсвэл хангалтгүй судалсан үед. (Ихэвчлэн шалгалтаас өмнө хугацаанд нь хүсэлт гаргана.)",
            "en": "Used when the student cannot continue the course or did not study/attend sufficiently (typically requested before the exam within the allowed period).",
        },
        "NR": {
            "mn": "Багш хугацаанд нь үнэлгээ тавьж системд оруулаагүй үед мэдээллийн системээс автоматаар тавигдана.",
            "en": "Automatically assigned by the system when the instructor does not enter the grade within the required time.",
        },
        "S": {
            "mn": "“Тоолцов” тэмдэглэгээ.",
            "en": "“Counted / Pass” mark.",
        },
        "U": {
            "mn": "“Үл тооцов” тэмдэглэгээ.",
            "en": "“Not counted / Fail” mark.",
        },
    }


def _get_code_explanation(code: str, data: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    1) Эхлээд dun.yml дотор codes: { CODE: {mn:..., en:...} } байвал түүнийг ашиглана
    2) Байхгүй бол зураг дээрх (builtin) тайлбаруудаас хайна
    """
    codes = (data.get("codes") or {})
    if isinstance(codes, dict) and code in codes and isinstance(codes[code], dict):
        mn = (codes[code].get("mn") or "").strip()
        en = (codes[code].get("en") or "").strip()
        if mn or en:
            return {"mn": mn, "en": en}

    builtins = _builtin_grade_explanations()
    if code in builtins:
        return builtins[code]

    return None


class ActionShowGradingPolicy(Action):
    def name(self) -> Text:
        return "action_show_grading_policy"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        data = _load_dun_yml()
        policy = (data.get("policy") or {})

        mn_list = policy.get("mn") or []
        en_list = policy.get("en") or []

        if not mn_list and not en_list:
            dispatcher.utter_message(
                text=(
                    "dun.yml олдсонгүй эсвэл policy хэсэг хоосон байна.\n"
                    "dun.yml was not found or the policy section is empty."
                )
            )
            return []

        parts: List[str] = []
        if mn_list:
            parts.append("📌 **Дүн бодох / бүртгэх дүрэм (MN)**")
            parts.extend([f"- {x}" for x in mn_list])

        if en_list:
            if parts:
                parts.append("")  # blank line
            parts.append("📌 **Grading policy / rules (EN)**")
            parts.extend([f"- {x}" for x in en_list])

        dispatcher.utter_message(text="\n".join(parts))
        return []


class ActionExplainGradeCode(Action):
    def name(self) -> Text:
        return "action_explain_grade_code"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        code = _norm(tracker.get_slot("grade_code"))

        if not code:
            dispatcher.utter_message(response="utter_ask_grade_code")
            return []

        data = _load_dun_yml()
        exp = _get_code_explanation(code, data)

        if not exp:
            dispatcher.utter_message(
                text=(
                    f"'{code}' тэмдэглэгээний тайлбар одоогоор байхгүй байна.\n"
                    f"No explanation found for '{code}' yet."
                )
            )
            return []

        mn = (exp.get("mn") or "").strip()
        en = (exp.get("en") or "").strip()

        # Хоёуланг нь харуулна (байгаа хэсгүүдийг л хэвлэнэ)
        lines: List[str] = [f"**{code}**"]
        if mn:
            lines.append(f"MN: {mn}")
        if en:
            lines.append(f"EN: {en}")

        dispatcher.utter_message(text="\n".join(lines))
        return []
