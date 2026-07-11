import os
from dotenv import load_dotenv

# Load variables from .env file if it exists
load_dotenv()

# ==========================================
# 1. Target Tracking Criteria
# ==========================================
# The keywords to match in job titles (case-insensitive, whole-word matching)
KEYWORDS = [
    "Flutter",
    "Android",
    "AI/ML",
    "Reactjs",
    "Backend",
    "Full Stack"
]

# Time limit in hours for jobs posted
JOB_LOOKBACK_HOURS = 24

# ==========================================
# 2. Portal Mappings
# ==========================================
# Dictionary of company names mapping to their ATS and board token/ID.
# Known public mappings are predefined. Others are pre-mapped to fallback handlers
# so you can easily customize their tokens or endpoints.
COMPANY_BOARDS = {
    # --- Pre-mapped Greenhouse Companies ---
    "Hubspot": {"ats": "greenhouse", "token": "hubspot"},
    "Reddit": {"ats": "greenhouse", "token": "reddit"},
    "GoDaddy": {"ats": "greenhouse", "token": "godaddy"},
    
    # --- Pre-mapped Lever Companies ---
    "Lever": {"ats": "lever", "token": "lever"},

    # --- Pre-mapped Ashby Companies ---
    "Zapier": {"ats": "ashby", "token": "zapier"},

    # --- Companies with Fallback or Custom Board configuration ---
    "1800 Flowers": {"ats": "fallback", "token": "1800flowers"},
    "24/7 In Touch Incorporated": {"ats": "fallback", "token": "247intouch"},
    "AAA": {"ats": "fallback", "token": "aaa"},
    "Allegis Transcription": {"ats": "fallback", "token": "allegistranscription"},
    "Alorica": {"ats": "fallback", "token": "alorica"},
    "Amazon": {"ats": "fallback", "token": "amazon"},
    "AMEX": {"ats": "fallback", "token": "amex"},
    "AM Trace": {"ats": "fallback", "token": "amtrace"},
    "Ansafone": {"ats": "fallback", "token": "ansafone"},
    "Anthem": {"ats": "fallback", "token": "anthem"},
    "Appen": {"ats": "fallback", "token": "appen"},
    "ACD Direct": {"ats": "fallback", "token": "acddirect"},
    "Activus Connect": {"ats": "fallback", "token": "activusconnect"},
    "Babble": {"ats": "fallback", "token": "babble"},
    "Babbletype": {"ats": "fallback", "token": "babbletype"},
    "Bold Business": {"ats": "fallback", "token": "boldbusiness"},
    "Boom Town": {"ats": "fallback", "token": "boomtown"},
    "Brand Institute": {"ats": "fallback", "token": "brandinstitute"},
    "Broadpath": {"ats": "fallback", "token": "broadpath"},
    "Call Experts": {"ats": "fallback", "token": "callexperts"},
    "Cambly": {"ats": "fallback", "token": "cambly"},
    "Capacity": {"ats": "fallback", "token": "capacity"},
    "CarMax": {"ats": "fallback", "token": "carmax"},
    "Carvana": {"ats": "fallback", "token": "carvana"},
    "Cass Information Systems": {"ats": "fallback", "token": "cassinfosystems"},
    "Clickworker": {"ats": "fallback", "token": "clickworker"},
    "Colony Brands": {"ats": "fallback", "token": "colonybrands"},
    "Concentrix": {"ats": "fallback", "token": "concentrix"},
    "Conduent": {"ats": "fallback", "token": "conduent"},
    "Conversica": {"ats": "fallback", "token": "conversica"},
    "CVS Health": {"ats": "fallback", "token": "cvshealth"},
    "Daily Transcription": {"ats": "fallback", "token": "dailytranscription"},
    "Direct Interactions": {"ats": "fallback", "token": "directinteractions"},
    "Dotdash": {"ats": "fallback", "token": "dotdash"},
    "Eagle Teleservices": {"ats": "fallback", "token": "eagleteleservices"},
    "eBay": {"ats": "fallback", "token": "ebay"},
    "Elevation Connect": {"ats": "fallback", "token": "elevationconnect"},
    "Eureka Facts": {"ats": "fallback", "token": "eurekafacts"},
    "Exam Works": {"ats": "fallback", "token": "examworks"},
    "Fancy Hands": {"ats": "fallback", "token": "fancyhands"},
    "G1 Survey Research": {"ats": "fallback", "token": "g1surveyresearch"},
    "Gengo": {"ats": "fallback", "token": "gengo"},
    "Humana": {"ats": "fallback", "token": "humana"},
    "Humanatic": {"ats": "fallback", "token": "humanatic"},
    "ICUC": {"ats": "fallback", "token": "icuc"},
    "InfoCision": {"ats": "fallback", "token": "infocision"},
    "Inktel Contact Center Solutions": {"ats": "fallback", "token": "inktel"},
    "Intermedia": {"ats": "fallback", "token": "intermedia"},
    "Keyword Studios": {"ats": "fallback", "token": "keywordstudios"},
    "L & E Research": {"ats": "fallback", "token": "leresearch"},
    "Literably": {"ats": "fallback", "token": "literably"},
    "Magic Ears": {"ats": "fallback", "token": "magicears"},
    "Mass Mutual": {"ats": "fallback", "token": "massmutual"},
    "Maximus": {"ats": "fallback", "token": "maximus"},
    "Mercor": {"ats": "fallback", "token": "mercor"},
    "MDS": {"ats": "fallback", "token": "mds"},
    "Micro1": {"ats": "fallback", "token": "micro1"},
    "My Employment Options": {"ats": "fallback", "token": "myemploymentoptions"},
    "Nelnet": {"ats": "fallback", "token": "nelnet"},
    "Nielsen": {"ats": "fallback", "token": "nielsen"},
    "Omni Interactions": {"ats": "fallback", "token": "omniinteractions"},
    "OnBrand 24": {"ats": "fallback", "token": "onbrand24"},
    "One Forma": {"ats": "fallback", "token": "oneforma"},
    "One Support": {"ats": "fallback", "token": "onesupport"},
    "Outplex": {"ats": "fallback", "token": "outplex"},
    "Pat Live": {"ats": "fallback", "token": "patlive"},
    "Pearl Interactive Network": {"ats": "fallback", "token": "pearlinteractivenetwork"},
    "Pearson": {"ats": "fallback", "token": "pearson"},
    "Pleio": {"ats": "fallback", "token": "pleio"},
    "Public Storage": {"ats": "fallback", "token": "publicstorage"},
    "Qurate Retail Group": {"ats": "fallback", "token": "qurateretailgroup"},
    "Reesby IT": {"ats": "fallback", "token": "reesbyit"},
    "Rev.com": {"ats": "fallback", "token": "rev"},
    "SC Data Centers": {"ats": "fallback", "token": "scdatacenters"},
    "S & P Data": {"ats": "fallback", "token": "spdata"},
    "Screen Rant": {"ats": "fallback", "token": "screenrant"},
    "Sedgwick": {"ats": "fallback", "token": "sedgwick"},
    "Sitel": {"ats": "fallback", "token": "sitel"},
    "Slingshot Technology": {"ats": "fallback", "token": "slingshottechnology"},
    "SMI": {"ats": "fallback", "token": "smi"},
    "Smith.ai": {"ats": "fallback", "token": "smithai"},
    "Startek": {"ats": "fallback", "token": "startek"},
    "Stella & Dot": {"ats": "fallback", "token": "stelladot"},
    "Skybridge Americas": {"ats": "fallback", "token": "skybridgeamericas"},
    "Support.com": {"ats": "fallback", "token": "supportdotcom"},
    "Sutherland Global": {"ats": "fallback", "token": "sutherlandglobal"},
    "Study.com": {"ats": "fallback", "token": "studydotcom"},
    "Teemwork.ai": {"ats": "fallback", "token": "teemworkai"},
    "Teleflora": {"ats": "fallback", "token": "teleflora"},
    "Telelanguage": {"ats": "fallback", "token": "telelanguage"},
    "Teleperformance": {"ats": "fallback", "token": "teleperformance"},
    "Telus International": {"ats": "fallback", "token": "telusinternational"},
    "The Social Element": {"ats": "fallback", "token": "thesocialelement"},
    "Transcom": {"ats": "fallback", "token": "transcom"},
    "Transperfect": {"ats": "fallback", "token": "transperfect"},
    "TSD Global": {"ats": "fallback", "token": "tsdglobal"},
    "TTEC": {"ats": "fallback", "token": "ttec"},
    "Tyme Global": {"ats": "fallback", "token": "tymeglobal"},
    "Ultius": {"ats": "fallback", "token": "ultius"},
    "United Health Group": {"ats": "fallback", "token": "unitedhealthgroup"},
    "Unum": {"ats": "fallback", "token": "unum"},
    "Valor Global": {"ats": "fallback", "token": "valorglobal"},
    "Verizon": {"ats": "fallback", "token": "verizon"},
    "VIP Desk Connect": {"ats": "fallback", "token": "vipdeskconnect"},
    "VIQ": {"ats": "fallback", "token": "viq"},
    "Wayfair": {"ats": "fallback", "token": "wayfair"},
    "Webstaurant Store": {"ats": "fallback", "token": "webstaurantstore"},
    "Webtoon": {"ats": "fallback", "token": "webtoon"},
    "Welocalize": {"ats": "fallback", "token": "welocalize"},
    "Windy City Call Center": {"ats": "fallback", "token": "windycitycallcenter"},
    "Working Solutions": {"ats": "fallback", "token": "workingsolutions"},
    "World Travel Holdings": {"ats": "fallback", "token": "worldtravelholdings"},
}

# ==========================================
# 3. Notification Settings (Environment Vars)
# ==========================================
# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Google Sheets configuration
# Can be a path to a credentials JSON file or raw JSON content of the service account
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Job Scraper Results")
GOOGLE_WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "Jobs")
