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
    "AI App Developer",
    "AI Mobile Developer",
    "Mobile AI Engineer",
    "GenAI Application Developer",
    "AI Integration Engineer",
    "LLM Application Developer",
    "AI/ML",
    "Reactjs",
    "Backend",
    "Full Stack"
]

# Time limit in hours for jobs posted
JOB_LOOKBACK_HOURS = 24

# Location filtering: If True, only jobs matching 'remote' or 'hybrid' in location/title are processed
ONLY_REMOTE_OR_HYBRID = True


# ==========================================
# 2. Portal Mappings
# ==========================================
# Dictionary of company names mapping to their ATS and board token/ID.
#
# Supported ATS & API types (via jobhive-py adapter):
# 1. Multi-tenant ATS: greenhouse, lever, ashby, smartrecruiters, workable, rippling,
#    personio, gem, join_com, icims, jazzhr, breezy, teamtailor, pinpoint, bamboohr,
#    cornerstone, recruitee, recruiterbox, eightfold, avature, phenom, workday, oracle,
#    successfactors, taleo, mercor
# 2. Custom big-tech APIs: amazon, apple, google, tiktok, uber
# 3. National public-sector aggregators: bundesagentur (DE), arbetsformedlingen (SE), eures (EU)
# 4. Hybrid job boards: welcometothejungle
# 5. Browser-required (set JOBHIVE_USE_BROWSERBASE=1, BROWSERBASE_API_KEY, BROWSERBASE_PROJECT_ID): meta, tesla
#
COMPANY_BOARDS = {
    # --- Greenhouse Companies ---
    "1-800 Contacts": {"ats": "greenhouse", "token": "1800contacts"},
    "1-800-GOT-JUNK?": {"ats": "greenhouse", "token": "1800gotjunk"},
    "10a Labs": {"ats": "greenhouse", "token": "10alabs"},
    "10x Genomics": {"ats": "greenhouse", "token": "10xgenomics"},
    "12twenty": {"ats": "greenhouse", "token": "12twenty"},
    "143 Studios LLC": {"ats": "greenhouse", "token": "143studiosinc"},
    "21Shares": {"ats": "greenhouse", "token": "21shares"},
    "2K": {"ats": "greenhouse", "token": "2k"},
    "2U": {"ats": "greenhouse", "token": "2u"},
    "3 Day Blinds (Sales)": {"ats": "greenhouse", "token": "3dayblindssales"},
    "31st Union": {"ats": "greenhouse", "token": "31stunion"},
    "3Cloud": {"ats": "greenhouse", "token": "3cloud"},
    "3Red Partners": {"ats": "greenhouse", "token": "3redpartners"},
    "8AM Golf": {"ats": "greenhouse", "token": "8amgolf"},
    "Ethernovia": {"ats": "greenhouse", "token": "2bc11c2c7us"},
    "Carvana": {"ats": "greenhouse", "token": "carvana"},
    "GoDaddy": {"ats": "greenhouse", "token": "godaddy"},
    "Hubspot": {"ats": "greenhouse", "token": "hubspot"},
    "Reddit": {"ats": "greenhouse", "token": "reddit"},

    # --- Lever Companies ---
    "Appen": {"ats": "lever", "token": "appen"},
    "Conversica": {"ats": "lever", "token": "conversica"},
    "Lever": {"ats": "lever", "token": "lever"},
    "Nielsen": {"ats": "lever", "token": "nielsen"},
    "TTEC": {"ats": "lever", "token": "ttecdigital"},
    "100MS": {"ats": "lever", "token": "100ms"},
    "15Five": {"ats": "lever", "token": "15five"},
    "1inch": {"ats": "lever", "token": "1inch"},
    "32Co": {"ats": "lever", "token": "32Co"},
    "360Learning": {"ats": "lever", "token": "360learning"},
    "4Front Ventures": {"ats": "lever", "token": "4front"},
    "90 Seconds": {"ats": "lever", "token": "90seconds"},
    "ACORD Corporation": {"ats": "lever", "token": "acord"},
    "AIFund": {"ats": "lever", "token": "AIFund"},
    "AMIRI": {"ats": "lever", "token": "AMIRI"},

    # --- Ashby Companies ---
    "Cambly": {"ats": "ashby", "token": "cambly"},
    "Mercor": {"ats": "ashby", "token": "mercor"},
    "Rev.com": {"ats": "ashby", "token": "rev"},
    "Zapier": {"ats": "ashby", "token": "zapier"},
    "0g Labs": {"ats": "ashby", "token": "0g"},
    "0x": {"ats": "ashby", "token": "0x"},
    "10x Team": {"ats": "ashby", "token": "10xteam"},
    "115 Ventures LLC": {"ats": "ashby", "token": "115ventures"},
    "1X": {"ats": "ashby", "token": "1x"},
    "1mind": {"ats": "ashby", "token": "1mind"},
    "3Commas": {"ats": "ashby", "token": "3commas"},
    "3Y Health": {"ats": "ashby", "token": "3y-health"},
    "3i Members": {"ats": "ashby", "token": "3imembers"},
    "8Fleet Inc.": {"ats": "ashby", "token": "8fleet-inc"},
    "9fin": {"ats": "ashby", "token": "9fin"},
    "Abacum": {"ats": "ashby", "token": "abacum"},
    "Abound": {"ats": "ashby", "token": "abound"},

    # --- SmartRecruiters Companies ---
    "Wayfair": {"ats": "smartrecruiters", "token": "Wayfair"},
    "A.P. Moller - Maersk": {"ats": "smartrecruiters", "token": "maersk"},
    "ABOUT YOU SE & Co. KG": {"ats": "smartrecruiters", "token": "aboutyougmbh"},
    "Acumatica": {"ats": "smartrecruiters", "token": "acumatica"},
    "1Huddle": {"ats": "smartrecruiters", "token": "1huddle"},
    "1stopbedrooms": {"ats": "smartrecruiters", "token": "1stopbedrooms"},
    "315 Logistics LLC": {"ats": "smartrecruiters", "token": "315logisticsllc"},
    "3H Partners": {"ats": "smartrecruiters", "token": "3hpartners"},
    "3SIGHT SERVICES LTD.": {"ats": "smartrecruiters", "token": "3sightservicesltd"},
    "9ESTR Handyman Services": {"ats": "smartrecruiters", "token": "9estrhandymanservices"},
    "ACI Group": {"ats": "smartrecruiters", "token": "acigroup"},
    "AFW": {"ats": "smartrecruiters", "token": "afw"},
    "Abercrombie and Fitch Co.": {"ats": "smartrecruiters", "token": "abercrombieandfitchco"},
    "Abuse Refuge Org": {"ats": "smartrecruiters", "token": "abuserefugeorg"},
    "Accel Learning": {"ats": "smartrecruiters", "token": "accellearning"},
    "Accenture Federal Services": {"ats": "smartrecruiters", "token": "accenturefederalservices"},

    # --- Workable Companies ---
    "Working Solutions": {"ats": "workable", "token": "working-solutions"},
    "1000heads": {"ats": "workable", "token": "1000heads"},
    "10x Banking": {"ats": "workable", "token": "10xbanking"},
    "1915 South / Ashley": {"ats": "workable", "token": "1915-south-ashley"},
    "1GLOBAL": {"ats": "workable", "token": "1global"},
    "1Kosmos": {"ats": "workable", "token": "1kosmos"},
    "2070Health": {"ats": "workable", "token": "2070health"},
    "2Modern": {"ats": "workable", "token": "2modern"},
    "3 Oaks Gaming": {"ats": "workable", "token": "3-oaks-gaming"},
    "360dialog GmbH": {"ats": "workable", "token": "360dialog-gmbh"},
    "3:15": {"ats": "workable", "token": "315"},
    "3E": {"ats": "workable", "token": "3e"},
    "4th & Reckless": {"ats": "workable", "token": "4th-and-reckless"},
    "7thSENSE GmbH": {"ats": "workable", "token": "7thsense"},
    "9D Technologies & Imagination AI": {"ats": "workable", "token": "9dtechnologies-1"},
    "A2MAC1": {"ats": "workable", "token": "a2mac1"},

    # --- Workday Companies ---
    "Concentrix": {"ats": "workday", "token": "cnx.wd1.myworkdayjobs.com/wday/cxs/cnx/external_global"},
    "eBay": {"ats": "workday", "token": "ebay.wd5.myworkdayjobs.com/wday/cxs/ebay/apply"},
    "2020 Companies": {"ats": "workday", "token": "2020companies.wd1.myworkdayjobs.com/wday/cxs/2020companies/external_careers"},
    "3M": {"ats": "workday", "token": "3m.wd1.myworkdayjobs.com/wday/cxs/3m/search"},
    "7-Eleven": {"ats": "workday", "token": "7eleven.wd3.myworkdayjobs.com/wday/cxs/7eleven/7eleven"},
    "8x8": {"ats": "workday", "token": "8x8inc.wd5.myworkdayjobs.com/wday/cxs/8x8inc/8x8_external_careers"},
    "A&K Travel Group": {"ats": "workday", "token": "abercrombiekent.wd12.myworkdayjobs.com/wday/cxs/abercrombiekent/abercrombiekent_careers"},
    "Aalto University": {"ats": "workday", "token": "aalto.wd3.myworkdayjobs.com/wday/cxs/aalto/aalto"},
    "Abglobal": {"ats": "workday", "token": "abglobal.wd1.myworkdayjobs.com/wday/cxs/abglobal/alliancebernsteincareers"},
    "Abrdn": {"ats": "workday", "token": "abrdn.wd3.myworkdayjobs.com/wday/cxs/abrdn/abrdn"},
    "Advocate Health": {"ats": "workday", "token": "aah.wd5.myworkdayjobs.com/wday/cxs/aah/external"},
    "Avanade": {"ats": "workday", "token": "accenture.wd103.myworkdayjobs.com/wday/cxs/accenture/avanadecareers"},
    "CSAA Insurance Group": {"ats": "workday", "token": "aaaie.wd1.myworkdayjobs.com/wday/cxs/aaaie/csaacareers"},
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
