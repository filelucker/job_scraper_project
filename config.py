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

    # # React
    # "React Developer",
    # "React Engineer",
    # "React.js",
    # "ReactJS",
    # "Next.js"
]

# Time limit in hours for jobs posted
JOB_LOOKBACK_HOURS = 24

# Location filtering: If True, only jobs matching 'remote' or 'hybrid' in location/title are processed
ONLY_REMOTE_OR_HYBRID = True

# Truly global search locations and domains
LINKEDIN_GLOBAL_LOCATIONS = ["Worldwide"]

# Curated list of top tech-hiring countries for fast and cost-efficient searches
INDEED_CURATED_DOMAINS = [
    "www.indeed.com",      # United States
    "uk.indeed.com",       # United Kingdom
    "ca.indeed.com",       # Canada
    "au.indeed.com",       # Australia
    "de.indeed.com",       # Germany
    "fr.indeed.com",       # France
    "in.indeed.com",       # India
    "sg.indeed.com",       # Singapore
    "kr.indeed.com",       # South Korea
    "jp.indeed.com",       # Japan
    "nl.indeed.com",       # Netherlands
    "se.indeed.com",       # Sweden
    "ie.indeed.com",       # Ireland
    "ae.indeed.com",       # United Arab Emirates
    "ch.indeed.com"        # Switzerland
]

# Comprehensive list of all 58 country domains supported by Indeed
INDEED_ALL_DOMAINS = [
    "www.indeed.com", "uk.indeed.com", "ca.indeed.com", "au.indeed.com", "de.indeed.com",
    "fr.indeed.com", "in.indeed.com", "sg.indeed.com", "kr.indeed.com", "jp.indeed.com",
    "nl.indeed.com", "se.indeed.com", "ie.indeed.com", "ae.indeed.com", "ch.indeed.com",
    "ar.indeed.com", "at.indeed.com", "be.indeed.com", "br.indeed.com", "cl.indeed.com",
    "co.indeed.com", "cr.indeed.com", "cz.indeed.com", "dk.indeed.com", "ec.indeed.com",
    "eg.indeed.com", "fi.indeed.com", "gr.indeed.com", "hk.indeed.com", "hu.indeed.com",
    "id.indeed.com", "il.indeed.com", "it.indeed.com", "lu.indeed.com", "my.indeed.com",
    "mx.indeed.com", "ma.indeed.com", "nz.indeed.com", "no.indeed.com", "om.indeed.com",
    "pk.indeed.com", "pa.indeed.com", "pe.indeed.com", "ph.indeed.com", "pl.indeed.com",
    "pt.indeed.com", "qa.indeed.com", "ro.indeed.com", "sa.indeed.com", "za.indeed.com",
    "es.indeed.com", "tw.indeed.com", "th.indeed.com", "tr.indeed.com", "ua.indeed.com",
    "uy.indeed.com", "ve.indeed.com", "vn.indeed.com"
]

# Set the active Indeed domains list. Switch to INDEED_ALL_DOMAINS if you want full global coverage.
INDEED_GLOBAL_DOMAINS = INDEED_CURATED_DOMAINS


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

    # --- Added Direct Boards ---
    'Vanta': {'ats': 'ashby', 'token': 'vanta'},
    'Retool': {'ats': 'gem', 'token': 'retool'},
    'Plaid': {'ats': 'greenhouse', 'token': 'plaid'},
    'Verkada': {'ats': 'greenhouse', 'token': 'verkada'},
    'Scale AI': {'ats': 'greenhouse', 'token': 'scaleai'},
    'Harness': {'ats': 'greenhouse', 'token': 'harness'},
    'Postman': {'ats': 'greenhouse', 'token': 'postman'},
    'Faire': {'ats': 'greenhouse', 'token': 'faire'},
    'Checkr': {'ats': 'greenhouse', 'token': 'checkr'},
    'Remote': {'ats': 'greenhouse', 'token': 'remote'},
    'Weaviate': {'ats': 'greenhouse', 'token': 'weaviate'},
    'Orca Security': {'ats': 'greenhouse', 'token': 'orcasecurity'},
    'Whimsical': {'ats': 'ashby', 'token': 'whimsical'},
    'Webflow': {'ats': 'greenhouse', 'token': 'webflow'},
    'Tailscale': {'ats': 'greenhouse', 'token': 'tailscale'},
    'Railway': {'ats': 'ashby', 'token': 'railway'},
    'Anysphere (Cursor)': {'ats': 'ashby', 'token': 'anysphere'},
    'Atlassian': {'ats': 'lever', 'token': 'atlassian'},
    'Attentive': {'ats': 'greenhouse', 'token': 'attentive'},
    'Clearbit': {'ats': 'lever', 'token': 'clearbit'},
    'dbt Labs': {'ats': 'greenhouse', 'token': 'dbtlabs'},
    'DataStax': {'ats': 'greenhouse', 'token': 'datastax'},
    'Elastic': {'ats': 'greenhouse', 'token': 'elastic'},
    'HashiCorp': {'ats': 'greenhouse', 'token': 'hashicorp'},
    'Klaviyo': {'ats': 'greenhouse', 'token': 'klaviyo'},
    'LaunchDarkly': {'ats': 'greenhouse', 'token': 'launchdarkly'},
    'Modal': {'ats': 'ashby', 'token': 'modal'},
    'Pinecone': {'ats': 'ashby', 'token': 'pinecone'},
    'PlanetScale': {'ats': 'greenhouse', 'token': 'planetscale'},
    '1Password': {'ats': 'lever', 'token': '1password'},
    'Replit': {'ats': 'ashby', 'token': 'replit'},
    'Resend': {'ats': 'ashby', 'token': 'resend'},
    'Sourcegraph': {'ats': 'greenhouse', 'token': 'sourcegraph'},
    'Val Town': {'ats': 'ashby', 'token': 'valtown'},
    'WandB': {'ats': 'ashby', 'token': 'wandb'},
    'Warp': {'ats': 'ashby', 'token': 'warp'},
    'Block / Square': {'ats': 'smartrecruiters', 'token': 'Block'},
    'Celonis': {'ats': 'smartrecruiters', 'token': 'Celonis'},
    'Modern Treasury': {'ats': 'greenhouse', 'token': 'moderntreasury'},
    'N26': {'ats': 'personio', 'token': 'n26'},
    'Palantir': {'ats': 'lever', 'token': 'palantir'},
    'Shopify': {'ats': 'lever', 'token': 'shopify'},
    'Trade Republic': {'ats': 'personio', 'token': 'traderepublic'},
    'Twilio': {'ats': 'lever', 'token': 'twilio'},
    'Typeform': {'ats': 'workable', 'token': 'typeform'},
    'Ubisoft': {'ats': 'smartrecruiters', 'token': 'Ubisoft'},

    # --- Frontier AI & LLM Startups ---
    'Sierra': {'ats': 'ashby', 'token': 'sierra'},
    'Poolside': {'ats': 'greenhouse', 'token': 'poolside'},
    'Physical Intelligence': {'ats': 'ashby', 'token': 'pi'},
    'Midjourney': {'ats': 'ashby', 'token': 'midjourney'},
    'Luma AI': {'ats': 'ashby', 'token': 'lumaai'},
    'Pika': {'ats': 'ashby', 'token': 'pika'},
    'World Labs': {'ats': 'ashby', 'token': 'worldlabs'},
    'Scribe AI': {'ats': 'ashby', 'token': 'scribe'},
    'Jasper AI': {'ats': 'ashby', 'token': 'jasper'},
    'Copy.ai': {'ats': 'lever', 'token': 'copyai'},
    'Contextual AI': {'ats': 'ashby', 'token': 'contextual'},
    'Granola': {'ats': 'ashby', 'token': 'granola'},

    # --- Developer Experience & Infrastructure ---
    'Neon Database': {'ats': 'greenhouse', 'token': 'neon'},
    'Turso': {'ats': 'ashby', 'token': 'turso'},
    'Upstash': {'ats': 'ashby', 'token': 'upstash'},
    'Inngest': {'ats': 'ashby', 'token': 'inngest'},
    'Trigger.dev': {'ats': 'ashby', 'token': 'trigger'},
    'Fly.io': {'ats': 'greenhouse', 'token': 'flyio'},
    'Koyeb': {'ats': 'workable', 'token': 'koyeb'},
    'PostHog': {'ats': 'ashby', 'token': 'posthog'},
    'Mixpanel': {'ats': 'greenhouse', 'token': 'mixpanel'},
    'Amplitude': {'ats': 'greenhouse', 'token': 'amplitude'},
    'Segment': {'ats': 'greenhouse', 'token': 'segment'},

    # --- Mobile & Flutter Ecosystem & Mobile Platforms ---
    'RevenueCat': {'ats': 'ashby', 'token': 'revenuecat'},
    'Superwall': {'ats': 'ashby', 'token': 'superwall'},
    'Appwrite': {'ats': 'ashby', 'token': 'appwrite'},
    'OneSignal': {'ats': 'greenhouse', 'token': 'onesignal'},
    'Expo': {'ats': 'ashby', 'token': 'expo'},
    'Ionic': {'ats': 'greenhouse', 'token': 'ionic'},
    'Snapchat': {'ats': 'greenhouse', 'token': 'snapchat'},
    'Discord': {'ats': 'greenhouse', 'token': 'discord'},
    'Twitch': {'ats': 'greenhouse', 'token': 'twitch'},
    'Roku': {'ats': 'greenhouse', 'token': 'roku'},
    'Sonos': {'ats': 'greenhouse', 'token': 'sonos'},
    'Strava': {'ats': 'greenhouse', 'token': 'strava'},
    'AllTrails': {'ats': 'ashby', 'token': 'alltrails'},
    'Calm': {'ats': 'greenhouse', 'token': 'calm'},
    'Oura': {'ats': 'greenhouse', 'token': 'oura'},
    'Whoop': {'ats': 'greenhouse', 'token': 'whoop'},
    'Flo Health': {'ats': 'workable', 'token': 'flo'},
    'ClassDojo': {'ats': 'greenhouse', 'token': 'classdojo'},
    'Quizlet': {'ats': 'greenhouse', 'token': 'quizlet'},
    'Photomath': {'ats': 'workable', 'token': 'photomath'},
    'Tinder': {'ats': 'greenhouse', 'token': 'tinder'},
    'Hinge': {'ats': 'greenhouse', 'token': 'hinge'},
    'Life360': {'ats': 'greenhouse', 'token': 'life360'},
    'Deliveroo': {'ats': 'greenhouse', 'token': 'deliveroo'},
    'Grab': {'ats': 'greenhouse', 'token': 'grab'},
    'Gojek': {'ats': 'greenhouse', 'token': 'gojek'},
    'AppLovin': {'ats': 'greenhouse', 'token': 'applovin'},
    'IronSource': {'ats': 'greenhouse', 'token': 'ironsource'},
    'Unity': {'ats': 'greenhouse', 'token': 'unity'},
    'Epic Games': {'ats': 'greenhouse', 'token': 'epicgames'},
    'Roblox': {'ats': 'ashby', 'token': 'roblox'},
    'Supercell': {'ats': 'greenhouse', 'token': 'supercell'},
    'Riot Games': {'ats': 'greenhouse', 'token': 'riotgames'},
    'Niantic': {'ats': 'greenhouse', 'token': 'niantic'},
    'Branch Metrics': {'ats': 'greenhouse', 'token': 'branch'},
    'AppsFlyer': {'ats': 'greenhouse', 'token': 'appsflyer'},
    'Adjust': {'ats': 'personio', 'token': 'adjust'},
    'Singular': {'ats': 'greenhouse', 'token': 'singular'},
    'Adapty': {'ats': 'ashby', 'token': 'adapty'},
    'Qonversion': {'ats': 'ashby', 'token': 'qonversion'},
    'Emerge Tools': {'ats': 'ashby', 'token': 'emergetools'},
    'Embrace (Mobile)': {'ats': 'ashby', 'token': 'embrace'},
    'Instabug': {'ats': 'greenhouse', 'token': 'instabug'},
    'Bitrise': {'ats': 'greenhouse', 'token': 'bitrise'},
    'Codemagic': {'ats': 'workable', 'token': 'codemagic'},

    # --- Mobile Mobility, Rideshare & Micro-mobility ---
    'Lime': {'ats': 'greenhouse', 'token': 'lime'},
    'Bird': {'ats': 'greenhouse', 'token': 'bird'},
    'Tier Mobility': {'ats': 'personio', 'token': 'tier'},
    'Voi': {'ats': 'teamtailor', 'token': 'voi'},
    'Via': {'ats': 'greenhouse', 'token': 'via'},
    'Cabify': {'ats': 'lever', 'token': 'cabify'},
    'BlaBlaCar': {'ats': 'greenhouse', 'token': 'blablacar'},

    # --- Mobile Media, Creator & Content Apps ---
    'SoundCloud': {'ats': 'greenhouse', 'token': 'soundcloud'},
    'Deezer': {'ats': 'greenhouse', 'token': 'deezer'},
    'Patreon': {'ats': 'greenhouse', 'token': 'patreon'},
    'Substack': {'ats': 'ashby', 'token': 'substack'},
    'Medium': {'ats': 'lever', 'token': 'medium'},
    'VSCO': {'ats': 'greenhouse', 'token': 'vsco'},
    'Picsart': {'ats': 'greenhouse', 'token': 'picsart'},
    'Photoroom': {'ats': 'ashby', 'token': 'photoroom'},

    # --- Mobile Health, Fitness & Wearables ---
    'Noom': {'ats': 'greenhouse', 'token': 'noom'},
    'MyFitnessPal': {'ats': 'greenhouse', 'token': 'myfitnesspal'},
    'Sweatcoin': {'ats': 'lever', 'token': 'sweatcoin'},
    'Peloton': {'ats': 'greenhouse', 'token': 'peloton'},
    'Freeletics': {'ats': 'personio', 'token': 'freeletics'},
    'Clue': {'ats': 'personio', 'token': 'clue'},

    # --- Mobile Neobanks & Wallet Apps ---
    'Starling Bank': {'ats': 'greenhouse', 'token': 'starlingbank'},
    'Bunq': {'ats': 'recruitee', 'token': 'bunq'},
    'Chipper Cash': {'ats': 'ashby', 'token': 'chippercash'},
    'Wave Money': {'ats': 'ashby', 'token': 'wave'},
    'Phantom Wallet': {'ats': 'ashby', 'token': 'phantom'},
    'Rainbow Wallet': {'ats': 'ashby', 'token': 'rainbow'},
    'Trust Wallet': {'ats': 'greenhouse', 'token': 'trustwallet'},
    'Coinbase': {'ats': 'greenhouse', 'token': 'coinbase'},

    # --- Mobile Gaming & Interactive Studios ---
    'Zynga': {'ats': 'greenhouse', 'token': 'zynga'},
    'King': {'ats': 'greenhouse', 'token': 'king'},
    'Playtika': {'ats': 'greenhouse', 'token': 'playtika'},
    'Miniclip': {'ats': 'workable', 'token': 'miniclip'},
    'Voodoo': {'ats': 'greenhouse', 'token': 'voodoo'},
    'Moon Active': {'ats': 'greenhouse', 'token': 'moonactive'},
    'Scopely': {'ats': 'greenhouse', 'token': 'scopely'},

    # --- Global Unicorns & European Tech Giants ---
    'Revolut': {'ats': 'lever', 'token': 'revolut'},
    'Klarna': {'ats': 'personio', 'token': 'klarna'},
    'Wise': {'ats': 'smartrecruiters', 'token': 'Wise'},
    'Delivery Hero': {'ats': 'smartrecruiters', 'token': 'DeliveryHero'},
    'Just Eat Takeaway': {'ats': 'smartrecruiters', 'token': 'JustEatTakeaway'},
    'Wolt': {'ats': 'greenhouse', 'token': 'wolt'},
    'Personio (Company)': {'ats': 'personio', 'token': 'personio'},
    'Contentful': {'ats': 'greenhouse', 'token': 'contentful'},
    'Strapi': {'ats': 'greenhouse', 'token': 'strapi'},

    # --- Cybersecurity & Web3 ---
    'SentinelOne': {'ats': 'greenhouse', 'token': 'sentinelone'},
    'Chainlink': {'ats': 'greenhouse', 'token': 'chainlink'},
    'Consensys': {'ats': 'greenhouse', 'token': 'consensys'},
    'Uniswap': {'ats': 'ashby', 'token': 'uniswap'},
    'OpenSea': {'ats': 'ashby', 'token': 'opensea'},
    'Solana Labs': {'ats': 'ashby', 'token': 'solana'},
    'Circle (Crypto)': {'ats': 'greenhouse', 'token': 'circle'},
    'Fireblocks': {'ats': 'greenhouse', 'token': 'fireblocks'},

    # --- Regional Tech Aggregators ---
    'BuiltIn': {'ats': 'builtin', 'token': '*'},
    'The Hub (Nordics)': {'ats': 'thehub', 'token': '*'},
    'Wanted (APAC)': {'ats': 'wanted', 'token': '*'},
    'Get on Board (LATAM)': {'ats': 'getonbrd', 'token': '*'},
    'Programathor': {'ats': 'programathor', 'token': '*'},
    'Jobs.cz': {'ats': 'jobs_cz', 'token': '*'},
    'Jobs.ch': {'ats': 'jobsch', 'token': '*'},
    'Manfred (ES)': {'ats': 'manfred', 'token': '*'},

    # --- AI Coding, Vector & Data Platforms ---
    'Braintrust': {'ats': 'ashby', 'token': 'braintrust'},
    'Unstructured': {'ats': 'ashby', 'token': 'unstructured'},
    'Chroma': {'ats': 'ashby', 'token': 'chroma'},
    'Qdrant': {'ats': 'ashby', 'token': 'qdrant'},
    'LanceDB': {'ats': 'ashby', 'token': 'lancedb'},
    'Zilliz / Milvus': {'ats': 'greenhouse', 'token': 'zilliz'},
    'Cleanlab': {'ats': 'ashby', 'token': 'cleanlab'},
    'Codeium / Windsurf': {'ats': 'ashby', 'token': 'codeium'},
    'CodiumAI': {'ats': 'ashby', 'token': 'codium'},
    'Augment Code': {'ats': 'ashby', 'token': 'augment'},
    'Tabnine': {'ats': 'greenhouse', 'token': 'tabnine'},
    'BentoML': {'ats': 'ashby', 'token': 'bentoml'},

    # --- Data Engineering, Analytics & Orchestration ---
    'ClickHouse': {'ats': 'greenhouse', 'token': 'clickhouse'},
    'Timescale': {'ats': 'greenhouse', 'token': 'timescale'},
    'SingleStore': {'ats': 'greenhouse', 'token': 'singlestore'},
    'Confluent': {'ats': 'greenhouse', 'token': 'confluent'},
    'Astronomer': {'ats': 'greenhouse', 'token': 'astronomer'},
    'Dagster': {'ats': 'ashby', 'token': 'dagster'},
    'Prefect': {'ats': 'ashby', 'token': 'prefect'},
    'Airbyte': {'ats': 'ashby', 'token': 'airbyte'},
    'Hightouch': {'ats': 'ashby', 'token': 'hightouch'},
    'Census': {'ats': 'ashby', 'token': 'census'},
    'RudderStack': {'ats': 'ashby', 'token': 'rudderstack'},

    # --- Developer Auth, Identity & Security ---
    'Okta': {'ats': 'greenhouse', 'token': 'okta'},
    'Clerk': {'ats': 'ashby', 'token': 'clerk'},
    'Stytch': {'ats': 'ashby', 'token': 'stytch'},
    'WorkOS': {'ats': 'ashby', 'token': 'workos'},
    'Descope': {'ats': 'ashby', 'token': 'descope'},
    'Teleport': {'ats': 'greenhouse', 'token': 'gravitational'},
    'Chainguard': {'ats': 'greenhouse', 'token': 'chainguard'},
    'Semgrep': {'ats': 'greenhouse', 'token': 'semgrep'},
    'Twingate': {'ats': 'ashby', 'token': 'twingate'},

    # --- SaaS, Collaboration & Customer Ops ---
    'Pitch': {'ats': 'personio', 'token': 'pitch'},
    'Rive': {'ats': 'ashby', 'token': 'rive'},
    'Spline': {'ats': 'ashby', 'token': 'spline'},
    'Intercom': {'ats': 'greenhouse', 'token': 'intercom'},
    'Zendesk': {'ats': 'greenhouse', 'token': 'zendesk'},
    'Freshworks': {'ats': 'greenhouse', 'token': 'freshworks'},
    'Drift': {'ats': 'greenhouse', 'token': 'drift'},
    'Gong': {'ats': 'greenhouse', 'token': 'gong'},
    'Customer.io': {'ats': 'greenhouse', 'token': 'customerio'},
    'Postscript': {'ats': 'ashby', 'token': 'postscript'},
    'Yotpo': {'ats': 'greenhouse', 'token': 'yotpo'},

    # --- Fintech Infrastructure & Banking APIs ---
    'Navan': {'ats': 'greenhouse', 'token': 'navan'},
    'Flexport': {'ats': 'greenhouse', 'token': 'flexport'},
    'Toast': {'ats': 'greenhouse', 'token': 'toast'},
    'SoFi': {'ats': 'greenhouse', 'token': 'sofi'},
    'Marqeta': {'ats': 'greenhouse', 'token': 'marqeta'},
    'Lithic': {'ats': 'ashby', 'token': 'lithic'},
    'Unit': {'ats': 'ashby', 'token': 'unit'},
    'Column Bank': {'ats': 'ashby', 'token': 'column'},

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
    'Adzuna': {'ats': 'adzuna', 'token': '*'},
    'Jooble': {'ats': 'jooble', 'token': '*'},
    'Otta': {'ats': 'welcometothejungle', 'token': '*'},
    'FlexJobs': {'ats': 'flexjobs', 'token': '*'},
    'LinkedIn': {'ats': 'linkedin', 'token': '*'},
    'Indeed': {'ats': 'indeed', 'token': '*'},
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

# Adzuna API configuration
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

# Jooble API configuration
JOOBLE_API_KEY = os.getenv("JOOBLE_API_KEY")

# Apify API configuration
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
APIFY_LINKEDIN_ACTOR = os.getenv("APIFY_LINKEDIN_ACTOR", "curious_coder/linkedin-jobs-scraper")
APIFY_INDEED_ACTOR = os.getenv("APIFY_INDEED_ACTOR", "misceres/indeed-scraper")
APIFY_LINKEDIN_LOCATION = os.getenv("APIFY_LINKEDIN_LOCATION", "Remote")
APIFY_INDEED_LOCATION = os.getenv("APIFY_INDEED_LOCATION", "Remote")
APIFY_INDEED_COUNTRY = os.getenv("APIFY_INDEED_COUNTRY", "US")
