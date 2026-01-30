from __future__ import annotations

from typing import Any, Dict, Optional, Text
import os
import yaml

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher


def _norm(raw: Optional[str]) -> Optional[str]:
    return raw.strip().upper() if raw else None


def _project_root() -> str:
    return os.getcwd()


def _load_dun_yml() -> Dict[str, Any]:
    path = os.path.join(_project_root(), "dun.yml")
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class ActionShowGradingPolicy(Action):
    def name(self) -> Text:
        return "action_show_grading_policy"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        data = _load_dun_yml()
        policy = (data.get("policy") or {})
        mn_list = policy.get("mn") or []

        if not mn_list:
            dispatcher.utter_message(text="dun.yml олдсонгүй эсвэл хоосон байна.")
            return []

        mn_text = "\n".join([f"- {x}" for x in mn_list])

        dispatcher.utter_message(
            text=(
                "📌 **Дүн бодох / бүртгэх дүрэм**\n"
                f"{mn_text}\n\n"
                "🖼️ Доорх зурагт дүнгийн тэмдэглэгээний тайлбар бий. (Хэрвээ сайтад байршуулбал зураг URL-аа холбоно.)"
            )
            # image: URL байх ёстой. Сайт дээрээ байршуулсны дараа доорхыг нэмнэ:
            # , image="/assets/grade_legend.png"
        )
        return []


class ActionExplainGradeCode(Action):
    def name(self) -> Text:
        return "action_explain_grade_code"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        code = _norm(tracker.get_slot("grade_code"))

        if not code:
            dispatcher.utter_message(response="utter_ask_grade_code")
            return []

        # Зөвхөн таны өгсөн зураг дээрх тайлбараас.
        explanations: Dict[str, str] = {
            "NA": "Одоогоор дүнг гаргаагүй.",
            "F": "0–59 оноонд харгалзах үсгэн тэмдэглэгээ.",
            "I": "Хүндэтгэн үзэх шалтгаанаар явцын үнэлгээ дутуу бөгөөд улирлын шалгалтад орж чадаагүй үед хэрэглэнэ.",
            "E": "Хүндэтгэн үзэх шалтгаанаар улирлын шалгалтанд ороогүй тохиолдолд хэрэглэнэ.",
            "NC": "Багц цаг тооцохгүй бөгөөд уг хичээлийг оноотой судалсан гэсэн тэмдэглэгээ.",
            "CR": "Өөр сургуулийн багц цагийг шилжүүлэн тооцох үед хэрэглэнэ.",
            "R": "Тухайн хичээлийг амжилттай судалсан ч тодорхой шаардлагаар дахин судлах хүсэлт гаргасан тохиолдолд тэмдэглэнэ.",
            "W": "Хичээлийг цаашид судлах боломжгүй эсвэл хангалтгүй судалсан үед.",
            "NR": "Багш хугацаанд нь үнэлгээ тавьж системд оруулаагүй үед системээс автоматаар тавигдана.",
            "S": "“Тоолцов” тэмдэглэгээ.",
            "U": "“Үл тооцов” тэмдэглэгээ.",
        }

        text = explanations.get(code)
        if not text:
            dispatcher.utter_message(
                text=(
                    f"'{code}' тэмдэглэгээний тайлбар энэ удаад  "
                    "эсвэл тодорхойлолт байхгүй байна."
                )
            )
            return []

        dispatcher.utter_message(text=f"**{code}**: {text}\n\n(Эх сурвалж: N/A)")
        return []
