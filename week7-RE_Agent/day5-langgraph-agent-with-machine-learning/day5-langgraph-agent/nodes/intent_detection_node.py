"""Task 2 & 4: Intent Detection & Comprehensive Funnel with Multi-Entity, Purpose, Investment, House/Flat Marla vs Budget rules, Cancellation & Rescheduling."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage

from logger import default_agent_logger
from state import AgentState, PropertyPreferences, UserProfile
from tools.crm_tools import lookup_appointment, words_to_number_string

logger = logging.getLogger("LangGraphAgent")

# Continual-learning hooks (Day 5.5). Wrapped defensively so a missing/broken
# learning module can NEVER break live call handling — it only means the
# agent keeps using the rule engine and stops logging training examples.
try:
    from learning.dataset import log_training_example
    from learning.intent_classifier import predict as ml_predict_intent
    _LEARNING_ENABLED = True
except Exception as _learning_import_error:  # pragma: no cover
    logger.warning(f"[IntentDetectionNode] learning module unavailable: {_learning_import_error}")
    _LEARNING_ENABLED = False

    def log_training_example(*args, **kwargs):  # type: ignore
        return None

    def ml_predict_intent(*args, **kwargs):  # type: ignore
        return None, 0.0

URDU_NUMBERS = {
    "ایک": 1, "دو": 2, "تین": 3, "چار": 4, "پانچ": 5, "پونچ": 5,
    "چھ": 6, "سات": 7, "آٹھ": 8, "نو": 9, "دس": 10, "ٹین": 10,
    "گیارہ": 11, "الیون": 11, "بارہ": 12, "تیرہ": 13, "چودہ": 14, "پندرہ": 15,
    "سولہ": 16, "سترہ": 17, "اٹھارہ": 18, "انیس": 19, "بیس": 20,
    "پچیس": 25, "تیس": 30, "تھرٹی": 30, "اکتیس": 31, "پچاس": 50, "سو": 100,
}

URDU_MONTHS_MAP = {
    "جنوری": "January", "فروری": "February", "مارچ": "March", "اپریل": "April",
    "مئی": "May", "جون": "June", "جولائی": "July", "اگست": "August",
    "ستمبر": "September", "اکتوبر": "October", "نومبر": "November", "دسمبر": "December",
}

UNSUPPORTED_CITIES_MAP = {
    "karachi": "Karachi", "کراچی": "Karachi",
    "multan": "Multan", "ملتان": "Multan",
    "faisalabad": "Faisalabad", "فیصل آباد": "Faisalabad", "فصل آباد": "Faisalabad",
    "peshawar": "Peshawar", "پشاور": "Peshawar",
    "quetta": "Quetta", "کوئٹہ": "Quetta",
    "sialkot": "Sialkot", "سیالکوٹ": "Sialkot", "سیال کوٹ": "Sialkot", "seakh court": "Sialkot", "ceakh court": "Sialkot",
    "gujranwala": "Gujranwala", "گوجرانوالہ": "Gujranwala",
    "hyderabad": "Hyderabad", "حیدرآباد": "Hyderabad",
    "gwadar": "Gwadar", "گوادر": "Gwadar",
    "abbottabad": "Abbottabad", "ایبٹ آباد": "Abbottabad",
    "bahawalpur": "Bahawalpur", "بہاولپور": "Bahawalpur",
    "sargodha": "Sargodha", "سرگودھا": "Sargodha",
}

OFF_TOPIC_CUES = (
    # Python & Programming
    "python", "پائیتھن", "پایتھن", "بایتھن", "بائیتھن", "پائتھن", "پیٹھن", "paython", "paithan",
    "code", "coding", "کوڈنگ", "کودنگ", "software", "سافٹ ویئر", "hardware", "computer", "کمپیوٹر",
    "java", "جاوا", "javascript", "c++", "c#", "html", "css", "react", "php", "sql", "database",
    "algorithm", "الگورتھم", "chatgpt", "openai", "artificial intelligence", "ai model",
    # Prompt injection & instruction bypassing
    "sab bhool jao", "sab bhul jao", "سب بھول جاؤ", "سب بھول جا", "sab bhool jao aur",
    "forget everything", "forget previous", "ignore previous", "ignore all", "system prompt", "jailbreak",
    # Weather
    "weather", "mausam", "موسم", "barish", "بارش", "rain", "temperature",
    # Sports
    "cricket", "کرکٹ", "match", "میچ", "football", "babar azam", "ipl", "psl", "world cup",
    # Food / Recipes
    "recipe", "recipi", "khana", "cook", "cooking", "بریانی", "biryani", "dish", "salan",
    # Politics / News
    "politics", "siyasat", "سیاست", "imran khan", "nawaz sharif", "election", "pti", "pmln", "government",
    # General Trivia / Science / Math
    "general knowledge", "gk", "history", "tareekh", "science", "math", "calculator", "solve",
    # Music / Poetry / Jokes
    "song", "gana", "گانا", "poetry", "shayari", "شاعری", "tell me a joke", "latifa", "joke", "لطیفہ", "kahani",
    # Identity & Personal
    "who made you", "tum kaun ho", "kaun ho", "کون ہو", "who are you", "kis ne banaya", "tum ai ho", "are you an ai",
    # Medical
    "medicine", "bimari", "dawa", "doctor", "ilaj", "pain",
)

REAL_ESTATE_KEYWORDS = (
    "ghar", "house", "flat", "apartment", "plot", "marla", "kanal", "sqft", "square feet",
    "dha", "bahria", "gulberg", "johar town", "model town", "faisal town", "college road",
    "islamabad", "lahore", "rawalpindi", "rent", "buy", "sale", "khareedna", "bechna", "kiraya",
    "price", "budget", "crore", "lakh", "property", "properties", "society", "societies",
    "amenit", "school", "hospital", "masjid", "park", "visit", "appointment", "meeting",
    "agent", "developer", "registry", "transfer", "noc", "dastawaiz", "installment", "qist",
    "down payment", "commiss", "tax", "legal", "portion", "baths", "bedroom",
    # Urdu script
    "گھر", "فلیٹ", "اپارٹمنٹ", "پلاٹ", "مرلہ", "کنال", "ڈی ایچ اے", "بحریہ", "لاہور", "اسلام آباد",
    "راولپنڈی", "رینٹ", "کرایہ", "خرید", "خریدنا", "بیچنا", "بجٹ", "کروڑ", "لاکھ", "پراپرٹی",
    "پراپرٹیز", "سوسائٹی", "وزٹ", "ملاقات", "اپوائنٹمنٹ", "رجسٹری", "انتقال", "قسط", "ٹیکس",
)


def _is_off_topic_query(text: str) -> bool:
    """Check if user query is off-topic, programming, prompt-injection, or unrelated definition."""
    t = text.lower().strip()
    if not t:
        return False

    for cue in OFF_TOPIC_CUES:
        if cue in t:
            if cue in ("code", "match"):
                if re.search(rf"\b{cue}\b", t):
                    return True
            else:
                return True

    def_cues = ("definition", "ڈیفینیشن", "define", "تعریف", "meaning", "matlab kya", "کا مطلب", "kya hota hai", "کیا ہوتا ہے")
    if any(dc in t for dc in def_cues):
        has_real_estate = any(rk in t for rk in REAL_ESTATE_KEYWORDS)
        if not has_real_estate:
            return True

    return False

INVALID_NAMES = {
    "sir", "sahib", "madam", "bhai", "ji", "janab", "valued client", "client", "customer",
    "user", "none", "null", "سر", "صاحب", "جناب", "بھائی", "جی", "مدام", "نامور", "نام",
    "سین", "سین صاحب", "seen", "سن", "سو", "سی", "کو", "یا", "پر", "یار", "ورکس", "works",
    "ستمبر", "اکتوبر", "نومبر", "دسمبر", "جنوری", "فروری", "مارچ", "اپریل", "مئی", "جون",
    "جولائی", "اگست", "september", "october", "november", "december", "january", "february",
    "march", "april", "may", "june", "july", "august", "tomorrow", "kal", "کل", "parso",
    "پرسوں", "today", "aaj", "آج", "shaam", "شام", "baje", "بجے", "am", "pm", "ٹھیک", "theek",
    "اوکے", "okay", "ok", "ek", "ایک", "دو", "تین", "چار", "پانچ", "کر دو", "کر دیں", "پہ",
    "پیش", "دی", "لے", "چن", "chin", "چین"
}

NO_BUDGET_CUES = (
    "budget ka masla nahi", "budget ka issue nahi", "koi specific budget nahi", "no budget",
    "just show", "list dikha", "properties dikhao", "options dikhao", "options dikha dein",
    "jo available hain dikha do", "list dikha dein", "aise hi dikhao", "dikhayein", "dikhao",
    "بس لسٹ دکھا دو", "آپشنز دکھاؤ", "آپشن دکھا دیں", "کوئی بجٹ نہیں", "بجٹ کا مسئلہ نہیں",
    "لسٹ دکھا دو", "لسٹ دکھائیں", "دکھا دیں", "دکھاؤ"
)

RESCHEDULE_CUES = (
    # Direct english & roman
    "reschedule", "re-schedule", "re schedule", "reshedule", "re shedule", "reskedule", "re skedule",
    "shift appointment", "shift meeting", "shift visit", "change time", "time change", "change date", "date change",
    "change appointment", "change booking", "appointment change", "badalna", "badal do", "badal dein",
    "kisi aur time", "kisi aur din", "kisi aur waqt", "postpone",
    # FIX: "badha do/dein" and "agay karo/karein" (postpone/push forward)
    # are common ways to ask for a reschedule that weren't covered before
    # (a phrase like "booking agay badha dein" was matching the unrelated
    # "book" substring in the booking rule instead, since reschedule cues
    # only covered "badal" (change) not "badha"/"agay" (postpone/push back)).
    "badha do", "badha dein", "agay badha", "aage badha", "agay kar do", "agay kar dein",
    "aage kar do", "aage kar dein", "aage badha do", "aage badha dein",
    # Urdu text
    "ری شیڈول", "ریشیڈول", "ری شیڈیول", "ریشیڈیول", "ری شیڈل", "ریشیڈل", "ری شیڈولنگ",
    "شیڈول تبدیل", "وقت تبدیل", "ٹائم تبدیل", "تاریخ تبدیل", "دوسرا ٹائم", "دوسرا وقت", "دوسرے دن", "دوسری تاریخ",
    "بدل دو", "بدل دیں", "بدلنا", "تبدیل", "آگے بڑھا دیں", "آگے بڑھا دو",
    # Deepgram phonetic transcriptions of 'reschedule'
    "ریس کے جول", "ریس کےجول", "ریس کے گول", "ریسکیجول", "ریس کیجول", "ری سکیجول", "ری اسکیجول",
    "ریلیز کے جھول", "ریلیز کیجول", "ریلیز کے جول", "ریلیز شیڈول", "ریلیز شیڈیول", "ریلیز کیجول ریلیز کیجول",
    "ریلیز کے جھول گردوں"
)


def _societies_in_city(city: str) -> str:
    c = city.lower().strip()
    if c == "lahore":
        return "DHA Defence, Bahria Town, Johar Town, Faisal Town, Model Town, aur College Road"
    elif c == "islamabad":
        return "E-11, F-10, F-11, F-6, G-11, G-13, DHA Islamabad, aur Bahria Town"
    elif c == "rawalpindi":
        return "Bahria Town Rawalpindi aur Airport Housing Society"
    return "DHA Defence aur Bahria Town"


def _extract_budget_pkr(text: str) -> Optional[float]:
    """Extract numeric budget in PKR handling English, Urdu, and numerical formats."""
    t = text.lower()
    
    # Check for Crore / Cr / Karor / کروڑ
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:crores?|cr|karor|کروڑ)", t)
    if m:
        return float(m.group(1)) * 10_000_000

    # Check for Lakh / Lac / لاکھ
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|لاکھ)", t)
    if m:
        return float(m.group(1)) * 100_000

    # Word-based Urdu numbers
    for word, val in URDU_NUMBERS.items():
        if f"{word} کروڑ" in t or f"{word} crore" in t or f"{word} cr" in t:
            return float(val) * 10_000_000
        if f"{word} لاکھ" in t or f"{word} lakh" in t or f"{word} lac" in t:
            return float(val) * 100_000

    # Explicit numbers e.g. Rs 25,000,000 or PKR 15000000
    m = re.search(r"(?:rs\.?|pkr|budget of|upto|around)\s*([\d,]+(?:\.\d+)?)", t)
    if m:
        try:
            val = float(m.group(1).replace(",", ""))
            if val > 1000:
                return val
        except ValueError:
            pass

    # Direct large raw numbers
    m = re.search(r"\b(\d{7,9})\b", t)
    if m:
        return float(m.group(1))

    return None


def _extract_date_str(text: str) -> Optional[str]:
    """Extract date string from Urdu, Roman Urdu, or English."""
    t = text.lower().strip()

    # Direct Urdu month patterns
    for u_m, eng_m in URDU_MONTHS_MAP.items():
        if u_m in text:
            m_num = re.search(r"(\d{1,2})\s*" + re.escape(u_m), text)
            if m_num:
                return f"{m_num.group(1)} {eng_m}"
            for word, val in URDU_NUMBERS.items():
                if f"{word} {u_m}" in text:
                    return f"{val} {eng_m}"
            return eng_m

    # English month patterns
    m_eng = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b", t)
    if m_eng:
        return f"{m_eng.group(1)} {m_eng.group(2).title()}"

    for word, val in {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12}.items():
        if f"{word} sep" in t or f"{word} oct" in t or f"{word} nov" in t or f"{word} dec" in t or f"{word} jan" in t or f"{word} feb" in t or f"{word} mar" in t:
            month_match = re.search(r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)", t)
            if month_match:
                return f"{val} {month_match.group(1).title()}"

    # ISO or standard numeric dates (YYYY-MM-DD, DD/MM/YYYY)
    m_iso = re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b", t)
    if m_iso:
        return m_iso.group(1)

    # Relative days
    if any(k in t for k in ("kal", "کل", "tomorrow")):
        return "Tomorrow"
    elif any(k in t for k in ("parso", "parson", "پرسوں", "day after")):
        return "Day after tomorrow"
    elif any(k in t for k in ("aaj", "آج", "today")):
        return "Today"
    elif "friday" in t or "jummah" in t or "جمعہ" in t:
        return "Friday"
    elif "saturday" in t or "hafte" in t or "ہفتہ" in t:
        return "Saturday"
    elif "sunday" in t or "itwar" in t or "اتوار" in t:
        return "Sunday"
    elif "monday" in t or "peer" in t or "پیر" in t:
        return "Monday"

    return None


def _extract_time_str(text: str) -> Optional[str]:
    """Extract time string with comprehensive Urdu speech & English support."""
    t = text.lower().strip()

    # 1. Exact speech patterns for 2:00 PM / Two PM / ٹو پی ایم / 2 بجے
    if any(k in t for k in (
        "2:00", "200", "2 pm", "2:00 pm", "2pm", "two pm", "two p.m.", "2 p.m.",
        "ٹو پی ایم", "ٹو پی ام", "ٹو پی ایم ورکس", "ٹو pm", "ٹو بجے", "2 بجے", "دو بجے",
        "دو baje", "2 baje", "ٹو ورکس", "ٹو پی ایم پر", "ٹو پی ایم پہ", "ٹو چلے گا"
    )):
        return "2:00 PM"

    # 2. Exact speech patterns for 11:30 AM / 11 thirty / الیون تھرٹی / 113 / 1130
    if any(k in t for k in (
        "11:30", "1130", "113", "11 تھرٹی", "الیون تھرٹی", "الیون 30", "الیون", "eleven thirty",
        "ساڑھے گیارہ", "گیارہ تیس", "11 30", "11.30", "1130am", "11:30am", "1130 am", "11:30 am",
        "113 pe", "1130 pe", "11 تھرٹی پہ", "11 تھرٹی پیش", "الیون تھرٹی پیش", "الیون تھرٹی اے ایم"
    )):
        return "11:30 AM"

    # 3. Exact speech patterns for 10:30 AM / 1030 / ساڑھے دس / ٹین تھرٹی
    if any(k in t for k in (
        "10:30", "1030", "ساڑھے دس", "ٹین تھرٹی", "ten thirty", "10 30", "10:30 am", "1030am", "ٹین تھرٹی اے ایم"
    )):
        return "10:30 AM"

    # 4. Exact speech patterns for 3:00 PM / three pm / 3 بجے / تھری پی ایم
    if any(k in t for k in (
        "3:00", "300", "3 بجے", "تین بجے", "تھری پی ایم", "تھری پی ام", "three pm", "3 pm", "3:00 pm", "3pm",
        "تین بج", "3بجے", "3 baje", "three baje", "3:00pm", "3 00", "تھری بجے"
    )):
        return "3:00 PM"

    # 5. Exact speech patterns for 3:30 PM / 330 / ساڑھے تین / تھری تھرٹی
    if any(k in t for k in (
        "3:30", "330", "ساڑھے تین", "تھری تھرٹی", "three thirty", "3 30", "3.30", "3:30 pm", "330pm"
    )):
        return "3:30 PM"

    # 5b. Exact speech patterns for 4:30 PM / 430 / ساڑھے چار / فور تھرٹی
    if any(k in t for k in (
        "4:30", "430", "ساڑھے چار", "فور تھرٹی", "four thirty", "4 30", "4.30", "4:30 pm", "430pm", "4:30 baje"
    )):
        return "4:30 PM"

    # 6. Exact speech patterns for 4:00 PM / 400 / چار بجے / فور پی ایم
    if any(k in t for k in (
        "4:00", "400", "چار بجے", "4 بجے", "فور پی ایم", "فور پی ام", "four pm", "4 pm", "4:00 pm", "4pm",
        "شام چار", "shaam 4", "shaam four", "4 baje", "چار baje", "شام 4 بجے", "4 pa m", "4 pam", "4پہ", "فور بجے"
    )):
        return "4:00 PM"

    # 6b. Exact speech patterns for 5:30 PM / 530 / ساڑھے پانچ / فائیو تھرٹی
    if any(k in t for k in (
        "5:30", "530", "ساڑھے پانچ", "فائیو تھرٹی", "five thirty", "5 30", "5.30", "5:30 pm", "530pm", "5:30 baje"
    )):
        return "5:30 PM"

    # 7. Exact speech patterns for 5:00 PM / 500 / پانچ بجے / فائیو پی ایم
    if any(k in t for k in (
        "5:00", "500", "پانچ بجے", "5 بجے", "فائیو پی ایم", "فائیو پی ام", "five pm", "5 pm", "5:00 pm", "5pm",
        "شام پانچ", "shaam 5", "shaam five", "5 baje", "پانچ baje", "5 pa m", "5 pam", "faym pam", "faym", "فائیو بجے"
    )):
        return "5:00 PM"

    # 8. Exact speech patterns for 6:00 PM / 600 / چھ بجے / سکس پی ایم
    if any(k in t for k in (
        "6:00", "600", "چھ بجے", "6 بجے", "سکس پی ایم", "سکس پی ام", "six pm", "6 pm", "6:00 pm", "6pm",
        "شام چھ", "shaam 6", "shaam six", "6 baje", "چھ baje", "شام 6 بجے", "6 pa m", "6 pam", "سکس بجے"
    )):
        return "6:00 PM"

    # 9. Exact speech patterns for 1:00 PM / ون پی ایم / 1 بجے
    if any(k in t for k in (
        "1:00", "100", "1 pm", "1:00 pm", "1pm", "one pm", "ون پی ایم", "ون پی ام", "ون بجے", "ایک بجے", "1 baje"
    )):
        return "1:00 PM"

    # 10. Exact speech patterns for 1:30 PM / ڈیڑھ بجے / 130
    if any(k in t for k in ("1:30", "130", "ڈیڑھ", "ڈیڑھ بجے", "one thirty", "1 30", "1.30", "ون تھرٹی")):
        return "1:30 PM"

    # 11. Exact speech patterns for 2:30 PM / ڈھائی بجے / 230
    if any(k in t for k in ("2:30", "230", "ڈھائی", "ڈھائی بجے", "two thirty", "2 30", "2.30", "ٹو تھرٹی")):
        return "2:30 PM"

    # 12. Exact speech patterns for 10:00 AM / 1000 / دس بجے / ٹین اے ایم
    if any(k in t for k in ("10:00", "1000", "دس بجے", "10 بجے", "ten am", "10 am", "10:00 am", "10am", "10 baje", "ٹین اے ایم", "ٹین am")):
        return "10:00 AM"

    # 13. Exact speech patterns for 11:00 AM / 1100 / گیارہ بجے / الیون اے ایم
    if any(k in t for k in ("11:00", "1100", "گیارہ بجے", "11 بجے", "eleven am", "11 am", "11:00 am", "11am", "11 baje", "الیون اے ایم", "الیون am")):
        return "11:00 AM"

    # 14. Exact speech patterns for 12:00 PM / بارہ بجے / ٹولف
    if any(k in t for k in ("12:00", "1200", "12 pm", "12:00 pm", "12pm", "twelve pm", "ٹولف", "ٹوئلو", "بارہ بجے", "12 baje")):
        return "12:00 PM"

    # 15. Standard regex pattern with AM/PM/Baje
    m_time = re.search(r"(\d{1,2}(?::\d{2})?\s*(?:am|pm|baje|bjy|بجے))", t)
    if m_time:
        raw_val = m_time.group(1).upper()
        return raw_val.replace("BAJE", "PM").replace("BJY", "PM").replace("بجے", "PM").strip()

    # 16. Urdu Word numbers with baje
    for word, val in URDU_NUMBERS.items():
        if f"{word} بجے" in text or f"{word} baje" in t or f"{word} bjy" in t:
            period = "AM" if val in (9, 10, 11) else "PM"
            return f"{val}:00 {period}"

    # 17. English Word numbers with am/pm
    for word, val in {"six": 6, "five": 5, "four": 4, "three": 3, "two": 2, "one": 1, "eleven": 11, "ten": 10, "nine": 9}.items():
        if f"{word} pm" in t or f"shaam {word}" in t:
            return f"{val}:00 PM"
        if f"{word} am" in t or f"subah {word}" in t:
            return f"{val}:00 AM"

    # 18. General day periods
    if "shaam" in t or "شام" in t or "evening" in t:
        return "5:00 PM"
    elif "subah" in t or "صبح" in t or "morning" in t:
        return "11:00 AM"
    elif "dopahar" in t or "دوپہر" in t or "afternoon" in t:
        return "2:00 PM"

    return None


def _extract_client_name(text: str) -> Optional[str]:
    """Extract valid client name from spoken responses with robust Urdu phonetics."""
    t = text.strip()

    # Handle common Pakistani spoken names and Deepgram STT transcriptions
    name_patterns = [
        (("سین زین", "زین", "zain", "zayn"), "Zain"),
        (("کا ذہن", "کا ذھن", "کاظم", "kazim", "qasim", "قاسم"), "Kazim"),
        (("حمزہ", "hamza"), "Hamza"),
        (("علی", "ali"), "Ali"),
        (("عثمان", "usman", "usmaan"), "Usman"),
        (("عمر", "عامر", "omar", "umar", "aamir", "amir"), "Umar"),
        (("احمد", "ahmed", "ahmad"), "Ahmed"),
        (("بلال", "bilal"), "Bilal"),
        (("حسن", "hassan", "hasan"), "Hassan"),
        (("طارق", "tariq"), "Tariq"),
        (("وقاص", "waqas"), "Waqas"),
        (("عبداللہ", "abdullah"), "Abdullah"),
        (("سعد", "saad"), "Saad"),
        (("فرحان", "farhan"), "Farhan"),
        (("شاہ زیب", "شاہزیب", "shahzaib"), "Shahzaib"),
        (("ارسلان", "arslan"), "Arslan"),
        (("فیصل", "faisal"), "Faisal"),
        (("کاشف", "kashif"), "Kashif"),
        (("عاصم", "asim"), "Asim"),
    ]

    for triggers, mapped_name in name_patterns:
        if any(trig in t.lower() for trig in triggers):
            return mapped_name

    clean = re.sub(
        r"(?:mera naam|meri naam|my name is|this is|naam hai|naam he|naam|hai|he|is|ji|sir|sahib|میرا نام|میری نام|میرے نام|میرا|میری|میرے|نام|ہے|ہوں|اور|کانٹیکٹ|نمبر|یہ|سر|صاحب|ہیں|کا نام|کہہ دیں|کہتے ہیں|سین|سین صاحب)",
        " ",
        text,
        flags=re.IGNORECASE,
    ).strip()
    words = [w for w in clean.split() if len(w) >= 2 and not w.isdigit()]
    for w in words:
        clean_w = w.strip().lower()
        if clean_w not in INVALID_NAMES and not clean_w.isdigit():
            return w.strip().title()
    return None


def _extract_appointment_id(text: str, state: AgentState) -> Optional[str]:
    """Extract appointment ID from spoken text.
    Focuses on numbers/digits since the 'APT-' prefix is constant.
    Handles 'APT-2094', 'apt 2094', spoken words 'two zero nine four',
    'two thousand ninety four', 'two thousand ninty four', '2 0 9 4',
    Urdu numbers 'do sifar nau char', 'do hazaar chauranway', etc.
    """
    t = text.lower().strip()
    if not t:
        return None

    # 1. Direct standard patterns: APT-2094, APT 2094, APT2094, APT: 2094
    m = re.search(r"\bapt[-:\s]?(\d{3,6})\b", t)
    if m:
        return f"APT-{m.group(1)}"

    # 2. Urdu phonetic transcriptions: اے پی ٹی 2094, ایپٹ 2094, ای پی ٹی 2094, اپوائنٹمنٹ آئی ڈی 2094
    m_ur = re.search(r"(?:اے\s*پی\s*ٹی|ایپٹ|ای\s*پی\s*ٹی|اےپیٹی|اپوائنٹمنٹ\s*آئی\s*ڈی|آئی\s*ڈی)[-:\s]?(\d{3,6})", t)
    if m_ur:
        return f"APT-{m_ur.group(1)}"

    # 3. Phrased patterns: "appointment id is 2094", "appointment number 2094", "id 2094"
    m_phrase = re.search(r"(?:appointment|booking|visit|id|آئی ڈی|نمبر)\s*(?:id|number|hai|he|hega|is)?\s*[:#-]?\s*(\d{3,6})\b", t)
    if m_phrase:
        return f"APT-{m_phrase.group(1)}"

    # 4. Spoken number extraction (words, digits, spaced numbers, compound numbers)
    # The prefix 'APT-' remains the same, so any extracted 4-digit number maps to APT-XXXX
    num_str = words_to_number_string(t)
    if num_str:
        last_clarif = state.get("last_clarification_type", "")
        appt = state.get("appointment_status", {})

        words_count = len(t.split())
        has_id_cues = any(w in t for w in (
            "apt", "id", "appointment", "booking", "visit", "cancel", "reschedule",
            "shift", "badal", "آئی ڈی", "کینسل", "منسوخ", "شیڈیول", "نمبر"
        ))
        is_clarif_waiting = (
            last_clarif == "appointment_id"
            or appt.get("id_asked_flag")
            or appt.get("pending_action") in ("cancellation", "rescheduling")
        )

        if is_clarif_waiting or has_id_cues or words_count <= 8:
            return f"APT-{num_str}"

    # 5. Direct standalone digits if prompted
    last_clarif = state.get("last_clarification_type", "")
    appt = state.get("appointment_status", {})
    if last_clarif == "appointment_id" or appt.get("id_asked_flag"):
        m_num = re.search(r"\b(\d{3,6})\b", t)
        if m_num:
            return f"APT-{m_num.group(1)}"

    return None


def _extract_entities(text: str, state: AgentState) -> Dict[str, Any]:
    """Extract all conversational real estate entities simultaneously."""
    t = text.lower()
    extracted: Dict[str, Any] = {}
    appt = state.get("appointment_status", {})

    # 1. Budget
    budget = _extract_budget_pkr(text)
    if budget is not None:
        extracted["budget"] = budget

    # 2. Property Type
    type_mapping = {
        "house": "House", "ghar": "House", "ghr": "House", "گھر": "House", "مکان": "House", "villa": "House",
        "kothi": "House", "flat": "Flat", "فلیٹ": "Flat", "apartment": "Flat", "اپارٹمنٹ": "Flat",
        "plot": "Plot", "پلاٹ": "Plot", "upper portion": "Upper Portion", "اوپر والا": "Upper Portion",
        "lower portion": "Lower Portion", "نیچے والا": "Lower Portion", "portion": "Portion", "پورشن": "Portion",
        "farm house": "Farm House", "فارم ہاؤس": "Farm House",
    }
    for pattern, label in type_mapping.items():
        if pattern in t:
            extracted["property_type"] = label
            break

    # 3. Purpose (Buy / Rent)
    rent_cues = ("rent", "rental", "kiraya", "kiraye", "rent par", "rent pe", "rent pr", "کرایہ", "کرائے", "رینٹ", "کرایے", "kiraye par", "kiraye pe")
    buy_cues = (
        "buy", "purchase", "sale", "for sale", "kharid", "khareed", "khared", "kharedna",
        "khareedna", "kharidna", "khareedne", "kharedne", "kharidne", "khareedni", "kharedni", "kharidni",
        "lena chahta", "lena hai", "lene hain", "khareedna chahta", "kharedna chahta", "kharidna chahta",
        "خرید", "خریدنا", "بیچنا", "خریدنے", "بائے", "سیل", "خریدوں"
    )
    if any(x in t for x in rent_cues):
        extracted["purpose"] = "For Rent"
    elif any(x in t for x in buy_cues):
        extracted["purpose"] = "For Sale"
    elif extracted.get("budget") and extracted["budget"] >= 5_000_000:
        extracted["purpose"] = "For Sale"

    # 4. Supported Cities
    city_mapping = {
        "lahore": "Lahore", "لاہور": "Lahore",
        "islamabad": "Islamabad", "اسلام آباد": "Islamabad", "isb": "Islamabad",
        "rawalpindi": "Rawalpindi", "rawalpindi": "Rawalpindi", "pindi": "Rawalpindi",
    }
    for c_pat, c_name in city_mapping.items():
        if c_pat in t:
            extracted["city"] = c_name
            break

    # 5. Unsupported Cities
    for u_pat, u_name in UNSUPPORTED_CITIES_MAP.items():
        if u_pat in t:
            extracted["unsupported_city"] = u_name
            break

    # 6. Investment Goal Check
    if any(k in t for k in ("investment", "invest", "sarmayakari", "سرمایہ کاری", "منافع", "roi", "rental yield", "investment ke liye", "invest karna", "investment purpose")):
        extracted["investment_goal"] = True

    # 7. Area Marla & Kanal
    for word, val in URDU_NUMBERS.items():
        if f"{word} مرلہ" in t or f"{word} مرلے" in t or f"{word} marla" in t or f"{word} marle" in t:
            extracted["area_marla"] = float(val)
            break
        if f"{word} کنال" in t or f"{word} kanal" in t:
            extracted["area_marla"] = float(val * 20)
            break

    if "area_marla" not in extracted:
        m_marla = re.search(r"(\d+(?:\.\d+)?)\s*(?:marla|marle|مرلہ|مرلے|مرلا)", t)
        if m_marla:
            extracted["area_marla"] = float(m_marla.group(1))
        elif re.search(r"(\d+(?:\.\d+)?)\s*(?:kanal|کنال)", t):
            m_k = re.search(r"(\d+(?:\.\d+)?)\s*(?:kanal|کنال)", t)
            if m_k:
                extracted["area_marla"] = float(m_k.group(1)) * 20.0

    # 8. Bedrooms
    m_bed = re.search(r"(\d+)\s*(?:bed|beds|bedroom|bedrooms|بیڈ|کمرے|kamray)", t)
    if m_bed:
        extracted["bedrooms"] = int(m_bed.group(1))

    # 9. Locality / Societies
    localities = (
        "bahria town rawalpindi", "bahria town islamabad", "bahria town", "bahria",
        "بحریہ ٹاؤن", "بحریہ",
        "dha phase 6", "dha phase 5", "dha phase 4", "dha phase 3", "dha phase 2", "dha phase 1",
        "dha defence", "ڈی ایچ اے", "پی ایچ اے", "ٹی ایچ ایم", "ڈیفنس", "defense", "defence", "dha",
        "faisal town", "فیصل ٹاؤن", "model town", "ماڈل ٹاؤن", "johar town", "جوہر ٹاؤن",
        "gulberg", "گلبرگ", "college road", "کالج روڈ", "askari", "عسکری", "lake city", "لیک سٹی",
        "e-11", "f-11", "f-10", "f-8", "f-7", "f-6", "g-15", "g-13", "g-11", "g-10"
    )
    for loc in localities:
        if loc in t:
            clean_loc = loc
            if clean_loc in ("ڈی ایچ اے", "پی ایچ اے", "ٹی ایچ ایم", "ڈیفنس", "defense", "defence", "dha"):
                clean_loc = "DHA"
            elif clean_loc in ("بحریہ ٹاؤن", "بحریہ"):
                clean_loc = "Bahria Town"
            elif clean_loc == "گلبرگ":
                clean_loc = "Gulberg"
            elif clean_loc == "جوہر ٹاؤن":
                clean_loc = "Johar Town"
            elif clean_loc == "ماڈل ٹاؤن":
                clean_loc = "Model Town"
            extracted["locality"] = clean_loc.title()
            break

    # 10. Phone number
    m_phone = re.search(r"(\b03\d{2}[- ]?\d{7}\b|\b\+?92\d{10}\b|\b03\d{9}\b)", text)
    if m_phone:
        extracted["phone"] = m_phone.group(1).replace("-", "").replace(" ", "")

    # 11. Client Name
    if any(k in t for k in ("mera naam", "meri naam", "my name is", "this is", "naam hai", "naam he", "میرا نام", "نام ہے", "کا ذہن", "کاظم", "عمر", "عامر")):
        name_extracted = _extract_client_name(text)
        if name_extracted and name_extracted.lower() not in INVALID_NAMES:
            extracted["name"] = name_extracted
    elif appt.get("name_asked_flag"):
        name_extracted = _extract_client_name(text)
        if name_extracted and name_extracted.lower() not in INVALID_NAMES:
            extracted["name"] = name_extracted

    # 12. Option Selection
    if re.fullmatch(r"\s*[1-5]\s*", t):
        extracted["selected_option_idx"] = int(t.strip()) - 1
    elif any(k in t for k in ("first", "1st", "pehla", "پہلا", "آپشن ون", "option 1", "option one", "آپشن دن", "آپشن من", "آپشن 1", "یہ آپشن من", "یا آپشن من")):
        extracted["selected_option_idx"] = 0
    elif any(k in t for k in ("second", "2nd", "doosra", "دوسرا", "آپشن ٹو", "option 2", "option two", "آپشن 2")):
        extracted["selected_option_idx"] = 1
    elif any(k in t for k in ("third", "3rd", "teesra", "تیسرا", "آپشن تھری", "option 3", "option three", "آپشن 3")):
        extracted["selected_option_idx"] = 2

    m_prop = re.search(r"\b(prop-\d{3,5})\b", text, re.IGNORECASE)
    if m_prop:
        extracted["property_id"] = m_prop.group(1).upper()

    # 13. Dates & Times
    date_val = _extract_date_str(text)
    if date_val:
        extracted["date_str"] = date_val

    time_val = _extract_time_str(text)
    if time_val:
        extracted["time_str"] = time_val

    # If slot was unavailable and user picks alternative
    if appt.get("status") == "slot_unavailable" and not extracted.get("time_str"):
        if any(k in t for k in ("pehla", "first", "11", "الیون", "صبح", "morning", "opt 1", "1")):
            extracted["time_str"] = "11:30 AM"
        elif any(k in t for k in ("doosra", "second", "3", "تین", "afternoon", "opt 2", "2")):
            extracted["time_str"] = "3:30 PM"

    # 14. Appointment ID (Cross-call cancellation & rescheduling)
    appt_id_val = _extract_appointment_id(text, state)
    if appt_id_val:
        extracted["appointment_id"] = appt_id_val

    return extracted


def _classify_intent(text: str, state: AgentState, extracted: Dict[str, Any]) -> str:
    """Accurately classify user intent."""
    t = text.lower().strip()
    appt = state.get("appointment_status", {})

    last_clarif = state.get("last_clarification_type", "")
    if last_clarif == "appointment_id" or appt.get("id_asked_flag"):
        if appt.get("pending_action") == "cancellation" or appt.get("status") == "pending_cancellation":
            return "cancellation"
        if appt.get("pending_action") == "rescheduling" or appt.get("status") == "pending_reschedule":
            return "rescheduling"
        if any(w in t for w in ("cancel", "cencel", "کینسل", "کینسیل", "منسوخ")):
            return "cancellation"
        if any(w in t for w in ("reschedule", "shift", "badal")):
            return "rescheduling"
        if appt.get("pending_action"):
            return appt.get("pending_action")

    # 1. Cancellation cues (TOP PRIORITY)
    cancellation_cues = (
        "cancel", "cencel", "کینسل", "کینسیل", "منسوخ", "drop", "khatam", "ختم",
        "nahi aana", "نہیں آنا", "cancel my appointment", "cancel appointment", "cancel visit",
        "کینسل کر", "کینسیل کر", "منسوخ کر", "کنسل"
    )
    if any(w in t for w in cancellation_cues):
        return "cancellation"

    # 2. Rescheduling cues (HIGH PRIORITY)
    if any(w in t for w in RESCHEDULE_CUES) or appt.get("status") == "pending_reschedule":
        return "rescheduling"

    # 3. Off-topic query check (TOP PRIORITY)
    if _is_off_topic_query(t):
        return "off_topic"

    # 4. Goodbye / Acknowledgment cues
    ack_cues = (
        "ok", "okay", "theek hai", "theek", "thik hai", "thik", "acha", "achha",
        "shukriya", "shukria", "thanks", "thank you", "done", "perfect", "great", "bohat shukriya",
        "اوکے", "ٹھیک ہے", "شکریہ", "بہت شکریہ"
    )
    if appt.get("status") in ("scheduled", "rescheduled") and (t in ack_cues or any(t == w for w in ack_cues) or any(t.startswith(f"{w} ") for w in ack_cues)):
        return "goodbye"

    goodbye_cues = [
        "bye", "goodbye", "allah hafiz", "khuda hafiz", "see you", "exit", "quit",
        "shukriya", "shukria", "thanks", "thank you", "اللہ حافظ", "خدا حافظ"
    ]
    if any(w in t for w in goodbye_cues):
        return "goodbye"

    # 5. Booking cues
    is_explicit_booking = any(w in t for w in [
        "meeting", "meet", "appointment", "schedule", "milna", "mulaqat", "visit",
        "وزٹ", "ملاقات", "ملنا", "اپوائنٹمنٹ", "شیڈیول", "شیڈول", "book", "پسند آیا", "پسند", "visit schedule",
        "آپشن دن", "آپشن من", "آپشن 1", "آپشن 2", "آپشن 3", "سلیکٹ", "select"
    ]) or "selected_option_idx" in extracted or appt.get("status") == "slot_unavailable"

    if (is_explicit_booking or (appt.get("visit_started") and appt.get("status") not in ("scheduled", "rescheduled", "cancelled", "pending_reschedule"))) and appt.get("status") not in ("scheduled", "rescheduled", "pending_reschedule"):
        return "booking"

    # 6. Email request cues
    # FIX (was too narrow — matched almost nothing real callers say):
    # only "email me"/"send email"/"mail details" matched before, so a
    # normal request like "email bhej dein" or "mujhe email kar dein" fell
    # through to the RAG/recommendation fallback instead. Also removed the
    # old bare "میل" cue — that's ambiguous with "mile" (the distance unit)
    # in Urdu and was a false-positive risk (e.g. "kitni door hai" style
    # questions), replaced with the actual common Urdu spelling "ایمیل".
    email_cues = (
        "email", "e-mail", "gmail",
        "email me", "send email", "mail details", "email bhej", "bhej email",
        "email kar", "kar email", "email par", "email pe", "email pr",
        "mujhe email", "email address", "email chahiye", "email send",
        "ای میل", "ایمیل", "ای میل بھیج", "ای میل کر",
    )
    if any(w in t for w in email_cues):
        return "email"

    # 7. RAG / Amenities / Schools / Hospitals / FAQ inquiry cues
    rag_cues = (
        "document", "dastawaiz", "registry", "transfer", "procedure", "process",
        "tax", "taxes", "commission", "fee", "fees", "legal", "noc", "approval",
        "payment plan", "installment", "qist", "qistain", "down payment",
        "amenit", "school", "schools", "hospital", "hospitals", "clinic", "college",
        "park", "mosque", "masjid", "market", "commercial", "developer", "builder",
        "sahooliyat", "sahulat", "authority", "faq", "kya documents", "kon se documents",
        # FIX: "loan"/"mortgage" and "stamp duty" weren't covered at all —
        # a plain "mortgage kaise milta hai" or "stamp duty kitni hai" fell
        # through to the recommendation default instead of RAG.
        "loan", "mortgage", "stamp duty", "karza", "قرض",
        "سہولیات", "سہولت", "سکول", "ہسپتال", "کالج", "پارک"
    )
    if any(w in t for w in rag_cues):
        return "rag"

    # 8. Pure standalone greeting
    # FIX: bare "hi" used to match as a raw substring, which silently fired
    # on "chahiye" (want/need — one of the most common words in real
    # requests, e.g. "property dekhne ke liye time chahiye" was being
    # misclassified as a greeting). Every other cue here is a full word/
    # phrase long enough that substring matching is safe; "hi" specifically
    # now requires a word boundary so it only matches the standalone word.
    greeting_cues = [
        "hello", "hey", "assalam", "salam", "aoa", "adaab", "start",
        "assalamualaykum", "assalam o alaikum", "assalamu alaikum", "وعلیکم", "وعلیکم السلام",
        "walikum as salam", "walaikum salam", "walekum assalam"
    ]
    has_greeting_cue = any(w in t for w in greeting_cues) or bool(re.search(r"\bhi\b", t))
    criteria_cues = ["ghar", "house", "flat", "plot", "marla", "budget", "crore", "lakh", "rent", "buy", "lahore", "islamabad", "rawalpindi", "invest", "investment"]
    if has_greeting_cue and not any(c in t for c in criteria_cues) and not extracted:
        return "greeting"

    # 9. Learned fallback (Day 5.5): every rule above is a high-precision,
    # hand-tuned cue for its intent, so we never let the ML model override
    # them. It only gets a say once every rule has passed without a match —
    # i.e. exactly the fuzzy cases that used to just silently default to
    # "recommendation". As more real calls are logged and the classifier is
    # periodically retrained (see learning/train_intent_classifier.py), this
    # fallback gets more accurate without any code changes here.
    ml_intent, ml_confidence = ml_predict_intent(text)
    if ml_intent and ml_intent != "recommendation":
        logger.info(f"[IntentDetectionNode] ML fallback classified '{text[:60]}' as '{ml_intent}' (confidence={ml_confidence:.2f})")
        return ml_intent

    return "recommendation"


def intent_detection_node(state: AgentState) -> Dict[str, Any]:
    """Detect user intent and orchestrate multi-entity qualification, purpose, cancellation & rescheduling."""
    step = default_agent_logger.log_node_entry("IntentDetectionNode", state.get("last_node", "START"), state)

    raw_input = state.get("raw_user_input", "")
    if not raw_input and state.get("conversation_history"):
        last_msg = state["conversation_history"][-1]
        raw_input = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    t_raw = raw_input.lower().strip()

    # 1. Extract all entities at once
    entities = _extract_entities(raw_input, state)

    # 2. Update Preferences
    prefs: PropertyPreferences = dict(state.get("property_preferences", {}))
    for k in ("city", "locality", "property_type", "purpose", "area_marla", "bedrooms"):
        if k in entities:
            prefs[k] = entities[k]
    if "investment_goal" in entities:
        prefs["investment_goal"] = True

    # 3. Update User Profile
    profile: UserProfile = dict(state.get("user_profile", {}))
    if "name" in entities and (not profile.get("name") or str(profile.get("name", "")).lower() in INVALID_NAMES):
        profile["name"] = entities["name"]
    if "phone" in entities:
        profile["phone"] = entities["phone"]

    # 4. Update Budget
    budget = entities.get("budget", state.get("budget"))

    # 5. Update Appointment Status
    appt = dict(state.get("appointment_status", {}))
    if "property_id" in entities:
        appt["property_id"] = entities["property_id"]

    # If user selected an option index from recommended listings
    if "selected_option_idx" in entities and state.get("recommended_properties"):
        idx = entities["selected_option_idx"]
        recs = state["recommended_properties"]
        if idx < len(recs):
            selected = recs[idx]
            appt["property_id"] = selected.get("property_id")
            clean_loc = str(selected.get("locality", "")).replace(", Punjab, Lahore", "").replace(", Punjab, Rawalpindi", "").replace(", Islamabad Capital Territory, Islamabad", "")
            appt["property_title"] = f"{int(selected.get('area_marla', 5))} Marla {selected.get('property_type', 'House')} in {clean_loc}"
            appt["agent_name"] = selected.get("agent", "Ahmed Raza")
            appt["visit_started"] = True

    # 6. Intent Classification
    intent = _classify_intent(raw_input, state, entities)

    # 7. Step-by-Step Funnel & Safeguards
    clarification_needed = False
    clarification_prompt = ""
    prev_clarification = state.get("last_clarification_type", "")
    current_clarification = ""
    unclear_count = state.get("consecutive_unclear_count", 0)

    # Check if the user's input was unclear or failed to answer the pending clarification
    is_unclear = False
    if intent == "recommendation" and raw_input.strip():
        if prev_clarification:
            answered = False
            if prev_clarification == "property_type" and ("property_type" in entities or any(k in t_raw for k in ("ghar", "house", "flat", "apartment", "plot", "portion", "گھر", "فلیٹ", "پلاٹ"))):
                answered = True
            elif prev_clarification == "purpose" and ("purpose" in entities or any(k in t_raw for k in ("buy", "rent", "sale", "khareed", "kiraya", "خرید", "رینٹ", "کرایہ"))):
                answered = True
            elif prev_clarification == "city" and ("city" in entities or "unsupported_city" in entities or any(k in t_raw for k in ("lahore", "islamabad", "rawalpindi", "لاہور", "اسلام آباد", "راولپنڈی"))):
                answered = True
            elif prev_clarification == "locality" and ("locality" in entities or any(k in t_raw for k in NO_BUDGET_CUES)):
                answered = True
            elif prev_clarification == "size_budget" and ("area_marla" in entities or "budget" in entities or any(k in t_raw for k in NO_BUDGET_CUES)):
                answered = True
            elif prev_clarification == "booking_datetime" and ("date_str" in entities or "time_str" in entities):
                answered = True
            elif prev_clarification == "booking_name" and bool(profile.get("name") and str(profile.get("name", "")).lower() not in INVALID_NAMES):
                answered = True
            elif prev_clarification == "appointment_id" and ("appointment_id" in entities or bool(_extract_appointment_id(raw_input, state))):
                answered = True

            if not answered and not entities:
                is_unclear = True
        elif not entities and not any(k in t_raw for k in REAL_ESTATE_KEYWORDS):
            is_unclear = True

    if is_unclear:
        clarification_needed = True
        clarification_prompt = "Maaf kijiye, aap ne jo kaha main samajh nahi saka. Kya aap dobara clarify kar sakte hain?"
        current_clarification = prev_clarification or "general"
        unclear_count += 1

    # Off-topic Question Guard
    elif intent == "off_topic":
        clarification_needed = True
        clarification_prompt = (
            "Maaf kijiye, main real estate agent hoon, main sirf real estate related queries ka jawab de sakta hoon. "
            "Bataiye, property ke hawalay se main aap ki kya madad kar sakta hoon?"
        )
        current_clarification = prev_clarification

    # Unsupported City Guard
    elif "unsupported_city" in entities:
        unsupported = entities["unsupported_city"]
        clarification_needed = True
        clarification_prompt = (
            f"Maaf kijiye ga, filwaqt hum sirf Lahore, Islamabad aur Rawalpindi mein deal karte hain. "
            f"{unsupported} mein hamari services filhal available nahi hain. Kya aap in 3 cities mein options dekhna chahenge?"
        )
        current_clarification = "city"

    elif intent == "cancellation":
        target_aid = entities.get("appointment_id") or appt.get("appointment_id")
        record = lookup_appointment(target_aid) if target_aid else None

        if not record:
            if target_aid:
                clarification_needed = True
                clarification_prompt = (
                    f"Maaf kijiye ga, ID {target_aid} ke sath koi booking nahi mili. "
                    "Baraye meherbani apna durust Appointment ID (jaise ke APT-1042) check kar ke dobara bataiye."
                )
                current_clarification = "appointment_id"
                appt["id_asked_flag"] = True
                appt["pending_action"] = "cancellation"
            else:
                clarification_needed = True
                clarification_prompt = (
                    "Baraye meherbani apna Appointment ID bataiye (jaise ke APT-1042) jo aap ko booking ke waqt email mein bheja gaya tha, "
                    "taake main aap ki visit cancel kar sakoon."
                )
                current_clarification = "appointment_id"
                appt["id_asked_flag"] = True
                appt["pending_action"] = "cancellation"
        else:
            appt.update({
                "appointment_id": record.get("appointment_id"),
                "lead_id": record.get("lead_id", ""),
                "property_id": record.get("property_id", "PROP-General"),
                "property_title": record.get("property_title", "Property Visit"),
                "agent_name": record.get("agent_name", "Ahmed Raza"),
                "date_str": record.get("date_str", ""),
                "time_str": record.get("time_str", ""),
                "calendar_event_id": record.get("calendar_event_id", ""),
                "calendar_link": record.get("calendar_link", ""),
                "status": "pending_cancellation",
            })
            if record.get("client_name") and not profile.get("name"):
                profile["name"] = record.get("client_name")
            if record.get("client_phone") and not profile.get("phone"):
                profile["phone"] = record.get("client_phone")

            clarification_needed = False
            current_clarification = ""
            appt["id_asked_flag"] = False
            appt["pending_action"] = ""

    elif intent == "rescheduling":
        target_aid = entities.get("appointment_id") or appt.get("appointment_id")
        record = lookup_appointment(target_aid) if target_aid else None

        if not record and not appt.get("property_title"):
            if target_aid:
                clarification_needed = True
                clarification_prompt = (
                    f"Maaf kijiye ga, ID {target_aid} ke sath koi booking nahi mili. "
                    "Baraye meherbani apna durust Appointment ID (jaise ke APT-1042) check kar ke dobara bataiye."
                )
                current_clarification = "appointment_id"
                appt["id_asked_flag"] = True
                appt["pending_action"] = "rescheduling"
            else:
                clarification_needed = True
                clarification_prompt = (
                    "Baraye meherbani apna Appointment ID bataiye (jaise ke APT-1042) jo aap ko booking ke waqt email mein bheja gaya tha, "
                    "taake main aap ki appointment reschedule kar sakoon."
                )
                current_clarification = "appointment_id"
                appt["id_asked_flag"] = True
                appt["pending_action"] = "rescheduling"
        else:
            if record:
                appt.update({
                    "appointment_id": record.get("appointment_id"),
                    "lead_id": record.get("lead_id", ""),
                    "property_id": record.get("property_id", "PROP-General"),
                    "property_title": record.get("property_title", "Property Visit"),
                    "agent_name": record.get("agent_name", "Ahmed Raza"),
                    "calendar_event_id": record.get("calendar_event_id", ""),
                    "calendar_link": record.get("calendar_link", ""),
                })
                if record.get("client_name") and not profile.get("name"):
                    profile["name"] = record.get("client_name")
                if record.get("client_phone") and not profile.get("phone"):
                    profile["phone"] = record.get("client_phone")

            appt["id_asked_flag"] = False
            appt["pending_action"] = ""

            curr_date = entities.get("date_str") or (appt.get("date_str") if appt.get("status") == "pending_reschedule" else "")
            curr_time = entities.get("time_str") or (appt.get("time_str") if appt.get("status") == "pending_reschedule" else "")

            aid_label = f"Appointment {appt.get('appointment_id')} ke liye " if appt.get("appointment_id") else ""
            if not curr_date and not curr_time:
                appt["date_str"] = ""
                appt["time_str"] = ""
                appt["status"] = "pending_reschedule"
                appt["date_asked_flag"] = True
                appt["time_asked_flag"] = True
                clarification_needed = True
                clarification_prompt = f"Ji bilkul, {aid_label}aap kis naye din aur time par visit shift karna chahte hain?"
                current_clarification = "rescheduling_datetime"
            elif curr_date and not curr_time:
                appt["date_str"] = curr_date
                appt["time_str"] = ""
                appt["status"] = "pending_reschedule"
                appt["time_asked_flag"] = True
                clarification_needed = True
                clarification_prompt = f"Ji bilkul, {curr_date} ko aap kis time par visit shift karna chahte hain?"
                current_clarification = "rescheduling_datetime"
            elif not curr_date and curr_time:
                appt["time_str"] = curr_time
                appt["date_str"] = ""
                appt["status"] = "pending_reschedule"
                appt["date_asked_flag"] = True
                clarification_needed = True
                clarification_prompt = f"Ji bilkul, {curr_time} ke liye aap kis din visit shift karna chahte hain?"
                current_clarification = "rescheduling_datetime"
            else:
                appt["date_str"] = curr_date
                appt["time_str"] = curr_time
                appt["status"] = "rescheduled"
                clarification_needed = False
                current_clarification = ""

    elif intent == "booking":
        appt["visit_started"] = True

        if "date_str" in entities:
            appt["date_str"] = entities["date_str"]
        if "time_str" in entities:
            appt["time_str"] = entities["time_str"]

        if not appt.get("property_title"):
            rec_props = state.get("recommended_properties", [])
            if rec_props:
                top = rec_props[0]
                clean_loc = str(top.get("locality", "")).replace(", Punjab, Lahore", "").replace(", Punjab, Rawalpindi", "").replace(", Islamabad Capital Territory, Islamabad", "")
                appt["property_id"] = top.get("property_id")
                appt["property_title"] = f"{int(top.get('area_marla', 5))} Marla {top.get('property_type', 'House')} in {clean_loc}"
                appt["agent_name"] = top.get("agent", "Ahmed Raza")
            else:
                appt["property_title"] = "RealEstate Hub Property Visit"

        # Step A: Ask for Date & Time
        if not appt.get("date_str") and not appt.get("time_str"):
            appt["date_asked_flag"] = True
            appt["time_asked_flag"] = True
            clarification_needed = True
            clarification_prompt = "Ji bilkul, visit ke liye aap kis din aur kis time par aana pasand karenge?"
            current_clarification = "booking_datetime"
        elif appt.get("date_str") and not appt.get("time_str"):
            appt["time_asked_flag"] = True
            clarification_needed = True
            clarification_prompt = "Ji bilkul, aap kis time par aana pasand karenge?"
            current_clarification = "booking_datetime"
        elif not appt.get("date_str") and appt.get("time_str"):
            appt["date_asked_flag"] = True
            clarification_needed = True
            clarification_prompt = "Ji bilkul, aap kis din visit ke liye aana pasand karenge?"
            current_clarification = "booking_datetime"

        # Step B: Ask for Name (Valid check, not generic words like Sir/Sahib)
        elif not profile.get("name") or str(profile.get("name", "")).lower() in INVALID_NAMES:
            appt["name_asked_flag"] = True
            clarification_needed = True
            clarification_prompt = "Baraye meherbani apna shubh naam bataiye taake hum appointment aap ke naam par confirm kar sakein."
            current_clarification = "booking_name"
        else:
            clarification_needed = False
            current_clarification = ""

    elif intent == "recommendation":
        # Check if user says 'just show properties' or 'no specific budget'
        user_wants_direct_list = any(cue in t_raw for cue in NO_BUDGET_CUES)

        # Step 1: Property Type
        if not prefs.get("property_type"):
            clarification_needed = True
            clarification_prompt = "Aap ghar dekh rahe hain ya flat?"
            current_clarification = "property_type"

        # Step 2: Purpose (Buy / Rent)
        elif not prefs.get("purpose"):
            clarification_needed = True
            clarification_prompt = "Aap khareedna chahte hain ya rent par lena chahte hain?"
            current_clarification = "purpose"

        # Step 3: City
        elif not prefs.get("city"):
            clarification_needed = True
            clarification_prompt = "Aap kis city mein dekhna chahenge? Hamare paas Lahore, Islamabad aur Rawalpindi mein options available hain."
            current_clarification = "city"

        # Step 4: Societies / Area in that City (Only if user hasn't specified locality, marla, or budget yet)
        elif prefs.get("city") and not prefs.get("locality") and prefs.get("area_marla") is None and budget is None and not state.get("property_preferences", {}).get("societies_shared"):
            prefs["societies_shared"] = True
            city = prefs["city"]
            socs = _societies_in_city(city)
            clarification_needed = True
            clarification_prompt = f"{city} mein hamare paas {socs} jaisi societies available hain. Aap kis area mein prefer karenge?"
            current_clarification = "locality"

        # Step 5: House vs Flat Specific Qualification
        elif not user_wants_direct_list and not state.get("property_preferences", {}).get("size_budget_asked"):
            pt = prefs.get("property_type", "House").lower()
            loc = prefs.get("locality", "")
            prefix = f"{loc} mein " if loc else ""
            invest_str = "investment ke liye " if prefs.get("investment_goal") else ""
            purpose_str = "rent ke liye " if prefs.get("purpose") == "For Rent" else ""

            # FLAT RULE: Only ask for budget (DO NOT ask marla for flats!)
            if pt in ("flat", "apartment"):
                if budget is None:
                    prefs["size_budget_asked"] = True
                    clarification_needed = True
                    clarification_prompt = f"{prefix}Aap {invest_str}{purpose_str}ka approximate budget kitna hai?"
                    current_clarification = "size_budget"
            # HOUSE RULE: Ask for Marla AND Budget!
            else:
                if prefs.get("area_marla") is None and budget is None:
                    prefs["size_budget_asked"] = True
                    clarification_needed = True
                    clarification_prompt = f"{prefix}Aap {invest_str}{purpose_str}kitne marla ka {pt} dekh rahe hain aur aapka approximate budget kitna hai?"
                    current_clarification = "size_budget"
                elif prefs.get("area_marla") is not None and budget is None:
                    marla_str = f"{int(prefs['area_marla'])} marla "
                    prefs["size_budget_asked"] = True
                    clarification_needed = True
                    clarification_prompt = f"{prefix}{marla_str}{pt} ke liye aapka approximate budget kitna hai?"
                    current_clarification = "size_budget"
                elif prefs.get("area_marla") is None and budget is not None:
                    prefs["size_budget_asked"] = True
                    clarification_needed = True
                    clarification_prompt = f"{prefix}Aap kitne marla ka {pt} dekh rahe hain?"
                    current_clarification = "size_budget"
        else:
            clarification_needed = False
            current_clarification = ""

    output = {
        "intent": intent,
        "property_preferences": prefs,
        "user_profile": profile,
        "budget": budget,
        "appointment_status": appt,
        "clarification_needed": clarification_needed,
        "clarification_prompt": clarification_prompt,
        "last_clarification_type": current_clarification,
        "consecutive_unclear_count": unclear_count if is_unclear else 0,
        "last_node": "IntentDetectionNode",
    }

    default_agent_logger.log_node_exit(
        step,
        output,
        reasoning=f"Intent: '{intent}'. Purpose: '{prefs.get('purpose')}'. Time: '{appt.get('time_str')}'. Name: '{profile.get('name')}'. Clarification: {clarification_needed}.",
    )

    # Continual learning (Day 5.5): every real turn becomes a future training
    # example for the periodically-retrained intent classifier. Skipped for
    # off_topic turns (not a real intent to learn) and never blocks the call.
    if intent != "off_topic" and raw_input.strip():
        log_training_example(
            raw_input,
            intent,
            session_id=state.get("session_id", "default_session"),
            clarification_needed=clarification_needed,
            source="rule_engine",
        )

    return output