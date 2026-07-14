import os
from dotenv import load_dotenv

# Load variables from .env file if it exists
load_dotenv()

# ==========================================
# 1. Target Tracking Criteria
# ==========================================
# The keywords to match in job titles (case-insensitive, whole-word matching)
KEYWORDS = [
    # Flutter / Mobile
    "Flutter",
    "Android",
    "iOS",
    "Dart",
    "Flutter/Android/iOS/Dart",
    "Flutter Developer",
    "Flutter Engineer",
    "Android Developer",
    "Android Engineer",
    "Mobile Developer",
    "Mobile Engineer",

    # AI Application Development
    "AI App Developer",
    "AI Mobile Developer",
    "Mobile AI Engineer",
    "AI Engineer",
    "AI Integration Engineer",
    "Applied AI Engineer",
    "AI Software Engineer",
    "LLM Engineer",
    "LLM Application Developer",
    "GenAI Engineer",

    # Full Stack
    "Full Stack Developer",
    "Full Stack Engineer",
    "Backend Developer",
    "Backend Engineer",

    # React
    "React Developer",
    "React Engineer",
    "React.js",
    "ReactJS",
    "Next.js"
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
    # --- AI Startups ---
    'Abridge': {'ats': 'ashby', 'token': 'abridge'},
    'Anthropic': {'ats': 'greenhouse', 'token': 'anthropic'},
    'Anyscale': {'ats': 'lever', 'token': 'anyscale'},
    'Baseten': {'ats': 'ashby', 'token': 'baseten'},
    'Character.AI': {'ats': 'ashby', 'token': 'character'},
    'Cognition': {'ats': 'ashby', 'token': 'cognition'},
    'Cohere': {'ats': 'ashby', 'token': 'cohere'},
    'Decagon': {'ats': 'ashby', 'token': 'decagon'},
    'DeepL': {'ats': 'ashby', 'token': 'deepl'},
    'ElevenLabs': {'ats': 'ashby', 'token': 'elevenlabs'},
    'Ema': {'ats': 'ashby', 'token': 'ema'},
    'Harvey': {'ats': 'ashby', 'token': 'harvey'},
    'HeyGen': {'ats': 'greenhouse', 'token': 'heygen'},
    'Hugging Face': {'ats': 'workable', 'token': 'huggingface'},
    'Imbue': {'ats': 'greenhouse', 'token': 'imbue'},
    'LangChain': {'ats': 'ashby', 'token': 'langchain'},
    'LlamaIndex': {'ats': 'ashby', 'token': 'llamaindex'},
    'MAGIC': {'ats': 'workable', 'token': 'magic-careers'},
    'Magic': {'ats': 'greenhouse', 'token': 'magic'},
    'Mistral AI': {'ats': 'lever', 'token': 'mistral'},
    'OpenAI': {'ats': 'ashby', 'token': 'openai'},
    'Perplexity': {'ats': 'ashby', 'token': 'perplexity'},
    'Runway': {'ats': 'ashby', 'token': 'runway-ml'},
    'Synthesia': {'ats': 'bamboohr', 'token': 'synthesia'},
    'Together AI': {'ats': 'greenhouse', 'token': 'togetherai'},
    'adept': {'ats': 'bamboohr', 'token': 'adept'},
    'openai': {'ats': 'bamboohr', 'token': 'openai'},
    # --- SaaS / Productivity ---
    'Airtable': {'ats': 'greenhouse', 'token': 'airtable'},
    'Asana': {'ats': 'greenhouse', 'token': 'asana'},
    'Calendly': {'ats': 'greenhouse', 'token': 'calendly'},
    'Canva': {'ats': 'smartrecruiters', 'token': 'Canva'},
    'ClickUp': {'ats': 'ashby', 'token': 'clickup'},
    'Coda': {'ats': 'lever', 'token': 'Coda'},
    'Dropbox': {'ats': 'greenhouse', 'token': 'dropbox'},
    'Figma': {'ats': 'greenhouse', 'token': 'figma'},
    'HubSpot': {'ats': 'greenhouse', 'token': 'hubspotjobs'},
    'Hubspot': {'ats': 'greenhouse', 'token': 'hubspot'},
    'Linear': {'ats': 'ashby', 'token': 'linear'},
    'Loom': {'ats': 'ashby', 'token': 'loom'},
    'Miro': {'ats': 'ashby', 'token': 'miro'},
    'Monday': {'ats': 'personio', 'token': 'monday'},
    'Notion': {'ats': 'ashby', 'token': 'notion'},
    'Salesforce': {'ats': 'workday', 'token': 'salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/External_Career_Site'},
    'Slack': {'ats': 'workday', 'token': 'salesforce.wd12.myworkdayjobs.com/wday/cxs/salesforce/slack'},
    'Zapier': {'ats': 'ashby', 'token': 'zapier'},
    'Zoom': {'ats': 'workday', 'token': 'zoom.wd5.myworkdayjobs.com/wday/cxs/zoom/zoom'},
    'asana': {'ats': 'bamboohr', 'token': 'asana'},
    'calendly': {'ats': 'smartrecruiters', 'token': 'calendly'},
    'framer': {'ats': 'personio', 'token': 'framer'},
    'zapier': {'ats': 'bamboohr', 'token': 'zapier'},
    # --- Developer Tools & Infrastructure ---
    'CircleCI': {'ats': 'greenhouse', 'token': 'circleci'},
    'Cloudflare': {'ats': 'greenhouse', 'token': 'cloudflare'},
    'Cockroach Labs': {'ats': 'greenhouse', 'token': 'cockroachlabs'},
    'Datadog': {'ats': 'greenhouse', 'token': 'datadog'},
    'Docker': {'ats': 'bamboohr', 'token': 'docker'},
    'Fastly': {'ats': 'greenhouse', 'token': 'fastly'},
    'Fivetran': {'ats': 'greenhouse', 'token': 'fivetran'},
    'GitHub': {'ats': 'workable', 'token': 'github'},
    'GitLab': {'ats': 'greenhouse', 'token': 'gitlab'},
    'Grafana Labs': {'ats': 'greenhouse', 'token': 'grafanalabs'},
    'Netlify': {'ats': 'bamboohr', 'token': 'netlify'},
    'Prisma': {'ats': 'rippling', 'token': 'prisma-careers'},
    'Pulumi': {'ats': 'greenhouse', 'token': 'pulumicorporation'},
    'Redis': {'ats': 'ashby', 'token': 'redis'},
    'Sentry': {'ats': 'ashby', 'token': 'sentry'},
    'Snowflake': {'ats': 'ashby', 'token': 'snowflake'},
    'Snyk': {'ats': 'ashby', 'token': 'snyk'},
    'Supabase': {'ats': 'ashby', 'token': 'supabase'},
    'Temporal': {'ats': 'ashby', 'token': 'temporal'},
    'Vercel': {'ats': 'greenhouse', 'token': 'vercel'},
    'Wiz': {'ats': 'ashby', 'token': 'wiz'},
    'pulumi': {'ats': 'bamboohr', 'token': 'pulumi'},
    # --- Fintech ---
    'Adyen': {'ats': 'greenhouse', 'token': 'adyen'},
    'Affirm': {'ats': 'greenhouse', 'token': 'affirm'},
    'Airwallex': {'ats': 'ashby', 'token': 'airwallex'},
    'Bolt': {'ats': 'ashby', 'token': 'bolt'},
    'Bolt.new': {'ats': 'greenhouse', 'token': 'stackblitz'},
    'Brex': {'ats': 'greenhouse', 'token': 'brex'},
    'Carta': {'ats': 'greenhouse', 'token': 'carta'},
    'Chime Financial, Inc': {'ats': 'greenhouse', 'token': 'chime'},
    'Deel': {'ats': 'ashby', 'token': 'deel'},
    'Gemini': {'ats': 'greenhouse', 'token': 'gemini'},
    'Gusto': {'ats': 'breezy', 'token': 'gusto'},
    'Gusto, Inc.': {'ats': 'greenhouse', 'token': 'gusto'},
    'Jeeves': {'ats': 'lever', 'token': 'tryjeeves'},
    'Kraken': {'ats': 'lever', 'token': 'kraken123'},
    'Kraken Digital Asset Exchange': {'ats': 'lever', 'token': 'kraken'},
    'Ledger': {'ats': 'ashby', 'token': 'ledger'},
    'Melio': {'ats': 'greenhouse', 'token': 'melio'},
    'Mercury': {'ats': 'ashby', 'token': 'mercury'},
    'Monzo': {'ats': 'greenhouse', 'token': 'monzo'},
    'Ramp': {'ats': 'ashby', 'token': 'ramp'},
    'Rippling': {'ats': 'rippling', 'token': 'rippling'},
    'Robinhood': {'ats': 'greenhouse', 'token': 'robinhood'},
    'Stripe': {'ats': 'greenhouse', 'token': 'stripe'},
    'gusto': {'ats': 'jazzhr', 'token': 'gusto'},
    'ramp': {'ats': 'jazzhr', 'token': 'ramp'},
    # --- Cloud & Infrastructure ---
    'Azure': {'ats': 'workable', 'token': 'azure'},
    'Backblaze External Website': {'ats': 'greenhouse', 'token': 'backblaze'},
    'CoreWeave': {'ats': 'greenhouse', 'token': 'coreweave'},
    'CoreWeave Europe': {'ats': 'greenhouse', 'token': 'coreweaveu'},
    'Databricks': {'ats': 'greenhouse', 'token': 'databricks'},
    'LAMBDA': {'ats': 'smartrecruiters', 'token': 'lambda'},
    'Lambda': {'ats': 'ashby', 'token': 'lambda'},
    'Linode': {'ats': 'breezy', 'token': 'linode'},
    'Render': {'ats': 'ashby', 'token': 'render'},
    # --- Mobile-First / Consumer Tech ---
    'Airbnb': {'ats': 'greenhouse', 'token': 'airbnb'},
    'Bumble': {'ats': 'ashby', 'token': 'bumble'},
    'Bumble Inc.': {'ats': 'lever', 'token': 'bumbleinc'},
    'ClassPass': {'ats': 'greenhouse', 'token': 'classpass'},
    'Contractor Jobs at Airbnb': {'ats': 'greenhouse', 'token': 'contractorjobs'},
    'DoorDash Australia': {'ats': 'greenhouse', 'token': 'doordashaustralia'},
    'DoorDash Canada': {'ats': 'greenhouse', 'token': 'doordashcanada'},
    'DoorDash High Volume': {'ats': 'greenhouse', 'token': 'high-volume'},
    'DoorDash India': {'ats': 'greenhouse', 'token': 'doordashindia'},
    'DoorDash Quebec': {'ats': 'greenhouse', 'token': 'doordashquebec'},
    'DoorDash USA': {'ats': 'greenhouse', 'token': 'doordashusa'},
    'Duolingo': {'ats': 'breezy', 'token': 'duolingo'},
    'Headspace': {'ats': 'greenhouse', 'token': 'hs'},
    'Headspace Providers': {'ats': 'greenhouse', 'token': 'headspaceproviders'},
    'Headspace Sourcing': {'ats': 'greenhouse', 'token': 'headspacesourcing'},
    'Hopper': {'ats': 'bamboohr', 'token': 'hopper'},
    'Instacart': {'ats': 'smartrecruiters', 'token': 'instacart'},
    'Instagram': {'ats': 'workable', 'token': 'instagram'},
    'Lyft': {'ats': 'smartrecruiters', 'token': 'lyft'},
    'Match Group': {'ats': 'lever', 'token': 'matchgroup'},
    'Pinterest': {'ats': 'greenhouse', 'token': 'pinterest'},
    'Reddit': {'ats': 'greenhouse', 'token': 'reddit'},
    'Spotify': {'ats': 'lever', 'token': 'spotify'},
    'instacart': {'ats': 'greenhouse', 'token': 'instacart'},
    'lyft': {'ats': 'greenhouse', 'token': 'lyft'},
    'whatsapp': {'ats': 'workable', 'token': 'whatsapp'},

    # --- National Public-Sector Aggregators ---
    'Arbetsförmedlingen (SE)': {'ats': 'arbetsformedlingen', 'token': 'arbetsformedlingen'},
    'Bundesagentur (DE)': {'ats': 'bundesagentur', 'token': 'bundesagentur'},
    'Eures (EU)': {'ats': 'eures', 'token': 'eures'},
    'USAJobs (US)': {'ats': 'usajobs', 'token': 'usajobs'},

    # --- Hybrid / General Job Boards ---
    'Welcome to the Jungle': {'ats': 'welcometothejungle', 'token': '*'},
    'We Work Remotely': {'ats': 'fallback', 'token': 'https://weworkremotely.com/remote-jobs.rss'},
    'RemoteOK': {'ats': 'remoteok', 'token': '*'},
    'Wellfound': {'ats': 'wellfound', 'token': '*'},
    'Y Combinator': {'ats': 'ycombinator', 'token': '*'},
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
