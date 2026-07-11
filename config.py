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
    "1800 Flowers": {"ats": "greenhouse", "token": "1800flowers"},
    "24/7 In Touch Incorporated": {"ats": "greenhouse", "token": "247intouch"},
    "AAA": {"ats": "greenhouse", "token": "aaa"},
    "ACD Direct": {"ats": "greenhouse", "token": "acddirect"},
    "Activus Connect": {"ats": "greenhouse", "token": "activusconnect"},
    "Allegis Transcription": {"ats": "greenhouse", "token": "allegistranscription"},
    "AM Trace": {"ats": "greenhouse", "token": "amtrace"},
    "Amazon": {"ats": "greenhouse", "token": "amazon"},
    "AMEX": {"ats": "greenhouse", "token": "amex"},
    "Ansafone": {"ats": "greenhouse", "token": "ansafone"},
    "Anthem": {"ats": "greenhouse", "token": "anthem"},
    "Babble": {"ats": "greenhouse", "token": "babble"},
    "Babbletype": {"ats": "greenhouse", "token": "babbletype"},
    "Bold Business": {"ats": "greenhouse", "token": "boldbusiness"},
    "Boom Town": {"ats": "greenhouse", "token": "boomtown"},
    "Brand Institute": {"ats": "greenhouse", "token": "brandinstitute"},
    "Broadpath": {"ats": "greenhouse", "token": "broadpath"},
    "Call Experts": {"ats": "greenhouse", "token": "callexperts"},
    "Capacity": {"ats": "greenhouse", "token": "capacity"},
    "CarMax": {"ats": "greenhouse", "token": "carmax"},
    "Carvana": {"ats": "greenhouse", "token": "carvana"},
    "Cass Information Systems": {"ats": "greenhouse", "token": "cassinfosystems"},
    "Clickworker": {"ats": "greenhouse", "token": "clickworker"},
    "Colony Brands": {"ats": "greenhouse", "token": "colonybrands"},
    "Daily Transcription": {"ats": "greenhouse", "token": "dailytranscription"},
    "Direct Interactions": {"ats": "greenhouse", "token": "directinteractions"},
    "Dotdash": {"ats": "greenhouse", "token": "dotdash"},
    "Eagle Teleservices": {"ats": "greenhouse", "token": "eagleteleservices"},
    "Elevation Connect": {"ats": "greenhouse", "token": "elevationconnect"},
    "Eureka Facts": {"ats": "greenhouse", "token": "eurekafacts"},
    "Exam Works": {"ats": "greenhouse", "token": "examworks"},
    "Fancy Hands": {"ats": "greenhouse", "token": "fancyhands"},
    "G1 Survey Research": {"ats": "greenhouse", "token": "g1surveyresearch"},
    "Gengo": {"ats": "greenhouse", "token": "gengo"},
    "GoDaddy": {"ats": "greenhouse", "token": "godaddy"},
    "Hubspot": {"ats": "greenhouse", "token": "hubspot"},
    "Humana": {"ats": "greenhouse", "token": "humana"},
    "Humanatic": {"ats": "greenhouse", "token": "humanatic"},
    "ICUC": {"ats": "greenhouse", "token": "icuc"},
    "InfoCision": {"ats": "greenhouse", "token": "infocision"},
    "Inktel Contact Center Solutions": {"ats": "greenhouse", "token": "inktel"},
    "Intermedia": {"ats": "greenhouse", "token": "intermedia"},
    "Keyword Studios": {"ats": "greenhouse", "token": "keywordstudios"},
    "L & E Research": {"ats": "greenhouse", "token": "leresearch"},
    "Literably": {"ats": "greenhouse", "token": "literably"},
    "Magic Ears": {"ats": "greenhouse", "token": "magicears"},
    "Mass Mutual": {"ats": "greenhouse", "token": "massmutual"},
    "Maximus": {"ats": "greenhouse", "token": "maximus"},
    "MDS": {"ats": "greenhouse", "token": "mds"},
    "Micro1": {"ats": "greenhouse", "token": "micro1"},
    "My Employment Options": {"ats": "greenhouse", "token": "myemploymentoptions"},
    "Nelnet": {"ats": "greenhouse", "token": "nelnet"},
    "Omni Interactions": {"ats": "greenhouse", "token": "omniinteractions"},
    "OnBrand 24": {"ats": "greenhouse", "token": "onbrand24"},
    "One Forma": {"ats": "greenhouse", "token": "oneforma"},
    "One Support": {"ats": "greenhouse", "token": "onesupport"},
    "Outplex": {"ats": "greenhouse", "token": "outplex"},
    "Pat Live": {"ats": "greenhouse", "token": "patlive"},
    "Pearl Interactive Network": {"ats": "greenhouse", "token": "pearlinteractivenetwork"},
    "Pearson": {"ats": "greenhouse", "token": "pearson"},
    "Pleio": {"ats": "greenhouse", "token": "pleio"},
    "Public Storage": {"ats": "greenhouse", "token": "publicstorage"},
    "Qurate Retail Group": {"ats": "greenhouse", "token": "qurateretailgroup"},
    "Reddit": {"ats": "greenhouse", "token": "reddit"},
    "Reesby IT": {"ats": "greenhouse", "token": "reesbyit"},
    "S & P Data": {"ats": "greenhouse", "token": "spdata"},
    "SC Data Centers": {"ats": "greenhouse", "token": "scdatacenters"},
    "Screen Rant": {"ats": "greenhouse", "token": "screenrant"},
    "Sedgwick": {"ats": "greenhouse", "token": "sedgwick"},
    "Sitel": {"ats": "greenhouse", "token": "sitel"},
    "Skybridge Americas": {"ats": "greenhouse", "token": "skybridgeamericas"},
    "Slingshot Technology": {"ats": "greenhouse", "token": "slingshottechnology"},
    "SMI": {"ats": "greenhouse", "token": "smi"},
    "Smith.ai": {"ats": "greenhouse", "token": "smithai"},
    "Startek": {"ats": "greenhouse", "token": "startek"},
    "Stella & Dot": {"ats": "greenhouse", "token": "stelladot"},
    "Study.com": {"ats": "greenhouse", "token": "studycom"},
    "Support.com": {"ats": "greenhouse", "token": "supportdotcom"},
    "Sutherland Global": {"ats": "greenhouse", "token": "sutherlandglobal"},
    "Teemwork.ai": {"ats": "greenhouse", "token": "teemworkai"},
    "Teleflora": {"ats": "greenhouse", "token": "teleflora"},
    "Telelanguage": {"ats": "greenhouse", "token": "telelanguage"},
    "Teleperformance": {"ats": "greenhouse", "token": "teleperformance"},
    "Telus International": {"ats": "greenhouse", "token": "telusinternational"},
    "The Social Element": {"ats": "greenhouse", "token": "thesocialelement"},
    "Transcom": {"ats": "greenhouse", "token": "transcom"},
    "Transperfect": {"ats": "greenhouse", "token": "transperfect"},
    "TSD Global": {"ats": "greenhouse", "token": "tsdglobal"},
    "TTEC": {"ats": "greenhouse", "token": "ttec"},
    "Tyme Global": {"ats": "greenhouse", "token": "tymeglobal"},
    "Ultius": {"ats": "greenhouse", "token": "ultius"},
    "United Health Group": {"ats": "greenhouse", "token": "unitedhealthgroup"},
    "Unum": {"ats": "greenhouse", "token": "unum"},
    "Valor Global": {"ats": "greenhouse", "token": "valorglobal"},
    "Verizon": {"ats": "greenhouse", "token": "verizon"},
    "VIP Desk Connect": {"ats": "greenhouse", "token": "vipdeskconnect"},
    "VIQ": {"ats": "greenhouse", "token": "viq"},
    "Webstaurant Store": {"ats": "greenhouse", "token": "webstaurantstore"},
    "Webtoon": {"ats": "greenhouse", "token": "webtoon"},
    "Welocalize": {"ats": "greenhouse", "token": "welocalize"},
    "Windy City Call Center": {"ats": "greenhouse", "token": "windycitycallcenter"},
    "Working Solutions": {"ats": "greenhouse", "token": "workingsolutions"},
    "World Travel Holdings": {"ats": "greenhouse", "token": "worldtravelholdings"},

    # --- Pre-mapped Lever Companies ---
    "Appen": {"ats": "lever", "token": "appen"},
    "Conversica": {"ats": "lever", "token": "conversica"},
    "Lever": {"ats": "lever", "token": "lever"},
    "Nielsen": {"ats": "lever", "token": "nielsen"},

    # --- Pre-mapped Ashby Companies ---
    "Cambly": {"ats": "ashby", "token": "cambly"},
    "Mercor": {"ats": "ashby", "token": "mercor"},
    "Rev.com": {"ats": "ashby", "token": "rev"},
    "Zapier": {"ats": "ashby", "token": "zapier"},

    # --- Pre-mapped Workday Companies ---
    "Alorica": {"ats": "workday", "token": "alorica.myworkdayjobs.com/wday/cxs/alorica/Alorica"},
    "Concentrix": {"ats": "workday", "token": "concentrix.myworkdayjobs.com/wday/cxs/concentrix/Concentrix"},
    "Conduent": {"ats": "workday", "token": "conduent.myworkdayjobs.com/wday/cxs/conduent/Conduent-Careers"},
    "CVS Health": {"ats": "workday", "token": "cvshealth.myworkdayjobs.com/wday/cxs/cvshealth/CVS_Health_Careers"},
    "eBay": {"ats": "workday", "token": "ebay.wd5.myworkdayjobs.com/wday/cxs/ebayinc/apply"},

    # --- Pre-mapped SmartRecruiters Companies ---
    "Wayfair": {"ats": "smartrecruiters", "token": "Wayfair"},
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
