"""
Yu Ming Charter School scraping configuration.
Keywords organized by topic group matching the Oakland exchange guide.
"""

from datetime import datetime, timedelta

# --- Date Range ---
DATE_START = datetime(2023, 6, 1)
DATE_END = datetime(2026, 6, 30)

# --- School Geographic Location ---
# Yu Ming Charter School, Chestnut Campus (main): 2501 Chestnut St, Oakland, CA 94607
SCHOOL_LAT = 37.8170
SCHOOL_LON = -122.2840
SEARCH_RADIUS_KM = 50

YU_MING_CAMPUSES = [
    {"name": "Chestnut Campus (K-5)", "address": "2501 Chestnut St, Oakland, CA 94607", "lat": 37.8170, "lon": -122.2840},
    {"name": "Alcatraz Campus (6-8)", "address": "1086 Alcatraz Ave, Oakland, CA 94608", "lat": 37.8485, "lon": -122.2760},
]

# --- Nearby Locations (within 50km) ---
# Organized by region: East Bay, San Francisco / Peninsula, North Bay
NEARBY_LOCATIONS = {
    "east_bay_core": {
        "label": "East Bay 核心区 (<15km)",
        "locations": [
            {"name": "Oakland", "lat": 37.8044, "lon": -122.2712, "distance_km": 2},
            {"name": "Alameda", "lat": 37.7652, "lon": -122.2416, "distance_km": 7},
            {"name": "Piedmont", "lat": 37.8244, "lon": -122.2316, "distance_km": 5},
            {"name": "Emeryville", "lat": 37.8313, "lon": -122.2852, "distance_km": 2},
            {"name": "Berkeley", "lat": 37.8715, "lon": -122.2730, "distance_km": 7},
            {"name": "Albany", "lat": 37.8867, "lon": -122.2977, "distance_km": 8},
            {"name": "El Cerrito", "lat": 37.9157, "lon": -122.3116, "distance_km": 11},
            {"name": "Richmond", "lat": 37.9358, "lon": -122.3477, "distance_km": 14},
            {"name": "San Leandro", "lat": 37.7249, "lon": -122.1561, "distance_km": 14},
            {"name": "Orinda", "lat": 37.8771, "lon": -122.1797, "distance_km": 11},
            {"name": "Castro Valley", "lat": 37.6941, "lon": -122.0864, "distance_km": 19},
        ],
    },
    "east_bay_outer": {
        "label": "East Bay 外围 (15-50km)",
        "locations": [
            {"name": "Lafayette", "lat": 37.8858, "lon": -122.1180, "distance_km": 16},
            {"name": "Moraga", "lat": 37.8349, "lon": -122.1297, "distance_km": 14},
            {"name": "Walnut Creek", "lat": 37.9101, "lon": -122.0652, "distance_km": 21},
            {"name": "Concord", "lat": 37.9780, "lon": -122.0311, "distance_km": 28},
            {"name": "Pleasant Hill", "lat": 37.9480, "lon": -122.0608, "distance_km": 24},
            {"name": "Hayward", "lat": 37.6688, "lon": -122.0808, "distance_km": 23},
            {"name": "Union City", "lat": 37.5934, "lon": -122.0438, "distance_km": 32},
            {"name": "Fremont", "lat": 37.5485, "lon": -121.9886, "distance_km": 38},
            {"name": "Newark", "lat": 37.5297, "lon": -122.0402, "distance_km": 37},
            {"name": "Dublin", "lat": 37.7022, "lon": -121.9358, "distance_km": 33},
            {"name": "Pleasanton", "lat": 37.6624, "lon": -121.8747, "distance_km": 39},
            {"name": "San Ramon", "lat": 37.7799, "lon": -121.9780, "distance_km": 27},
            {"name": "Danville", "lat": 37.8216, "lon": -121.9699, "distance_km": 28},
        ],
    },
    "sf_peninsula": {
        "label": "旧金山 / 半岛",
        "locations": [
            {"name": "San Francisco", "lat": 37.7749, "lon": -122.4194, "distance_km": 13},
            {"name": "Daly City", "lat": 37.6879, "lon": -122.4702, "distance_km": 21},
            {"name": "South San Francisco", "lat": 37.6547, "lon": -122.4077, "distance_km": 21},
            {"name": "San Bruno", "lat": 37.6305, "lon": -122.4111, "distance_km": 23},
            {"name": "Millbrae", "lat": 37.5985, "lon": -122.3872, "distance_km": 26},
            {"name": "Burlingame", "lat": 37.5841, "lon": -122.3661, "distance_km": 27},
            {"name": "San Mateo", "lat": 37.5630, "lon": -122.3255, "distance_km": 30},
            {"name": "Redwood City", "lat": 37.4852, "lon": -122.2364, "distance_km": 37},
            {"name": "Menlo Park", "lat": 37.4530, "lon": -122.1817, "distance_km": 41},
            {"name": "Palo Alto", "lat": 37.4419, "lon": -122.1430, "distance_km": 43},
            {"name": "Stanford", "lat": 37.4241, "lon": -122.1661, "distance_km": 45},
        ],
    },
    "north_bay": {
        "label": "北湾",
        "locations": [
            {"name": "Sausalito", "lat": 37.8591, "lon": -122.4853, "distance_km": 19},
            {"name": "Mill Valley", "lat": 37.9060, "lon": -122.5450, "distance_km": 26},
            {"name": "San Rafael", "lat": 37.9735, "lon": -122.5311, "distance_km": 29},
            {"name": "Novato", "lat": 38.1074, "lon": -122.5697, "distance_km": 41},
            {"name": "Vallejo", "lat": 38.1041, "lon": -122.2566, "distance_km": 32},
        ],
    },
}

# --- Points of Interest (within 50km) ---
NEARBY_POI = {
    "universities": [
        "UC Berkeley",
        "Stanford University",
        "CSU East Bay",
        "Mills College",
        "Holy Names University",
        "Saint Mary's College",
        "City College of San Francisco",
        "San Francisco State University",
        "University of San Francisco",
        "Academy of Art University",
    ],
    "oakland_neighborhoods": [
        "Rockridge",
        "Temescal",
        "Piedmont Avenue",
        "Lake Merritt",
        "Jack London Square",
        "Oakland Chinatown",
        "West Oakland",
        "East Oakland",
        "Montclair Oakland",
        "Dimond District Oakland",
        "Grand Lake Oakland",
        "Uptown Oakland",
        "Adams Point Oakland",
    ],
    "transit_hubs": [
        "Oakland International Airport",
        "San Francisco International Airport",
        "BART MacArthur Station",
        "BART 19th Street Oakland",
        "BART Rockridge Station",
        "BART Downtown Berkeley",
        "BART Embarcadero",
        "BART Powell Street",
    ],
    "landmarks": [
        "Golden Gate Bridge",
        "Bay Bridge",
        "Muir Woods",
        "Fisherman's Wharf",
        "Alcatraz",
        "Exploratorium",
        "Computer History Museum",
        "Monterey Bay Aquarium",
    ],
    "hospitals": [
        "Alta Bates Summit Medical Center",
        "UCSF Medical Center",
        "Stanford Health Care",
        "Kaiser Permanente Oakland",
        "Highland Hospital Oakland",
        "Children's Hospital Oakland",
        "Zuckerberg San Francisco General",
    ],
}

# --- Output ---
OUTPUT_DIR = "output"

# --- Request Settings ---
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # Exponential backoff multiplier
RATE_LIMIT_DELAY = 1.5  # Seconds between requests to same domain

# --- User-Agent Rotation ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

# --- Reddit Configuration ---
REDDIT_CLIENT_ID = ""      # Set via env var REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET = ""  # Set via env var REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT = "yuming_school_research/1.0"

REDDIT_SUBREDDITS = [
    "oakland",
    "bayarea",
    "berkeley",
    "Teachers",
    "education",
    "InternationalStudents",
    "China",
]

# --- Keywords by Topic Group ---
KEYWORD_GROUPS = {
    "school_core": {
        "label": "学校核心信息",
        "en": [
            "Yu Ming Charter School",
            "Yu Ming School Oakland",
            '"Yu Ming" Oakland',
        ],
        "zh": [
            "育明特许学校",
            "育明学校 奥克兰",
        ],
    },
    "international_students": {
        "label": "留学生/国际交流",
        "en": [
            "Oakland international student",
            "J-1 teacher Oakland",
            "Oakland exchange student",
            "Chinese teacher Oakland",
            "international student Bay Area",
        ],
        "zh": [
            "留学生 奥克兰",
            "奥克兰 交流访问",
            "J-1 签证 老师",
            "湾区 中国留学生",
        ],
    },
    "housing": {
        "label": "住宿/租房",
        "en": [
            "Oakland rental",
            "Berkeley housing",
            "Oakland apartment",
            "Bay Area rent",
            "Oakland roommate",
            "Rockridge rental",
        ],
        "zh": [
            "奥克兰 租房",
            "伯克利 租房",
            "湾区 房租",
            "奥克兰 合租",
        ],
    },
    "safety": {
        "label": "安全/治安",
        "en": [
            "Oakland safety",
            "Oakland crime",
            "East Oakland safety",
            "Oakland neighborhoods safe",
            "Bay Area car break-in",
        ],
        "zh": [
            "奥克兰 治安",
            "奥克兰 安全",
            "奥克兰 犯罪率",
            "湾区 砸车",
        ],
    },
    "transportation": {
        "label": "交通出行",
        "en": [
            "BART Oakland",
            "AC Transit Oakland",
            "Oakland public transit",
            "Oakland commute Berkeley",
        ],
        "zh": [
            "奥克兰 交通",
            "湾区 BART",
            "奥克兰 公交",
        ],
    },
    "education_system": {
        "label": "教育体系/双语教学",
        "en": [
            "bilingual immersion California",
            "mandarin immersion Oakland",
            "charter school Oakland",
            "Chinese immersion program Bay Area",
            "dual language immersion school",
        ],
        "zh": [
            "中英双语学校 加州",
            "特许学校 奥克兰",
            "沉浸式中文教学",
        ],
    },
    "community_life": {
        "label": "社区生活",
        "en": [
            "Oakland Chinatown",
            "Lake Merritt Oakland",
            "Berkeley international",
            "living in Oakland",
            "moving to Oakland",
        ],
        "zh": [
            "湾区 生活",
            "奥克兰 生活体验",
            "奥克兰 唐人街",
            "伯克利 生活",
        ],
    },
    "cost_of_living": {
        "label": "生活成本",
        "en": [
            "Oakland cost of living",
            "Bay Area student budget",
            "Oakland living expenses",
        ],
        "zh": [
            "奥克兰 生活费",
            "湾区 花费",
            "奥克兰 物价",
        ],
    },
    "healthcare": {
        "label": "医疗健康",
        "en": [
            "Oakland urgent care",
            "Bay Area health insurance international",
            "Alta Bates Oakland",
        ],
        "zh": [
            "奥克兰 看病",
            "美国 留学生 医保",
            "湾区 医院",
        ],
    },
}

# --- News RSS Feeds ---
NEWS_RSS_FEEDS = [
    {
        "name": "The Oaklandside",
        "url": "https://oaklandside.org/feed/",
        "topic": "all",
    },
    {
        "name": "The Oaklandside - Education",
        "url": "https://oaklandside.org/category/education/feed/",
        "topic": "education",
    },
    {
        "name": "SF Chronicle - Education",
        "url": "https://www.sfchronicle.com/rss/education/",
        "topic": "education",
    },
    {
        "name": "East Bay Times - Education",
        "url": "https://www.eastbaytimes.com/category/news/education/feed/",
        "topic": "education",
    },
    {
        "name": "Berkeleyside",
        "url": "https://www.berkeleyside.org/feed/",
        "topic": "all",
    },
    {
        "name": "KQED - Education",
        "url": "https://www.kqed.org/news/education/feed/",
        "topic": "education",
    },
    {
        "name": "EdSource - Charter Schools",
        "url": "https://edsource.org/feed/topics/charter-schools",
        "topic": "charter",
    },
]

# --- Google News Search Queries ---
GOOGLE_NEWS_QUERIES = [
    # School core
    '"Yu Ming Charter School"',
    '"Yu Ming" Oakland school',
    'Oakland charter school Chinese immersion',
    'Oakland education bilingual',
]

# --- Nearby Location Google News Queries ---
# Generated for each location within 50km, combined with topic keywords
NEARBY_NEWS_QUERIES = [
    # School + nearby cities
    '"Yu Ming" Oakland charter',
    'Oakland school Mandarin immersion',
    # Campus area coverage
    'West Oakland education',
    'Oakland Chinatown community',
    'Lake Merritt Oakland',
    # Nearby cities + school/education
    'Berkeley school bilingual',
    'Alameda education charter',
    'San Leandro school',
    'Richmond CA education',
    # Transit
    'BART Oakland safety',
    'AC Transit Oakland service',
    # Safety
    'Oakland neighborhood safety',
    'East Bay crime trend',
    'Bay Area car break-in prevention',
    # Housing + nearby
    'Oakland housing rent 2024',
    'Berkeley student housing',
    'East Bay rental market',
    'Bay Area affordable housing',
    # International / education
    'California charter school Mandarin',
    'Bay Area Chinese immersion school',
    'Oakland international student',
    'J-1 teacher California',
    # Community
    'Oakland Chinatown revitalization',
    'East Bay Chinese community',
    'Bay Area Asian American education',
    # UC Berkeley + Stanford
    'UC Berkeley international student',
    'Stanford education school',
    'UC Berkeley education department',
    # Life / cost
    'Oakland cost of living 2024',
    'Bay Area student budget',
    'East Bay living expenses',
    # Healthcare
    'Oakland hospital Alta Bates',
    'Bay Area health insurance student',
    'Oakland urgent care',
]

# --- Expanded News RSS Feeds (including nearby cities) ---
NEWS_RSS_FEEDS_EXTRA = [
    {
        "name": "SF Chronicle - Bay Area",
        "url": "https://www.sfchronicle.com/rss/bayarea/",
        "topic": "bayarea",
    },
    {
        "name": "East Bay Times - News",
        "url": "https://www.eastbaytimes.com/latest-headlines/feed/",
        "topic": "all",
    },
    {
        "name": "East Bay Times - Crime & Public Safety",
        "url": "https://www.eastbaytimes.com/category/news/crime-public-safety/feed/",
        "topic": "safety",
    },
    {
        "name": "East Bay Times - Housing",
        "url": "https://www.eastbaytimes.com/category/business/real-estate/feed/",
        "topic": "housing",
    },
    {
        "name": "SF Chronicle - Transportation",
        "url": "https://www.sfchronicle.com/rss/transportation/",
        "topic": "transportation",
    },
    {
        "name": "SF Chronicle - Food & Dining",
        "url": "https://www.sfchronicle.com/rss/food/",
        "topic": "food",
    },
    {
        "name": "Oakland North (UC Berkeley)",
        "url": "https://oaklandnorth.net/feed/",
        "topic": "all",
    },
    {
        "name": "Hoodline Oakland",
        "url": "https://hoodline.com/category/oakland/feed/",
        "topic": "all",
    },
    {
        "name": "The Daily Californian (UCB)",
        "url": "https://www.dailycal.org/feed/",
        "topic": "university",
    },
    {
        "name": "Stanford Daily",
        "url": "https://www.stanforddaily.com/feed/",
        "topic": "university",
    },
    {
        "name": "SFist",
        "url": "https://sfist.com/feed/",
        "topic": "all",
    },
    {
        "name": "Mission Local",
        "url": "https://missionlocal.org/feed/",
        "topic": "all",
    },
    {
        "name": "Berkeley Scanner",
        "url": "https://www.berkeleyscanner.com/feed/",
        "topic": "safety",
    },
]

# --- Review Sites ---
REVIEW_SITES = {
    "niche": {
        "url": "https://www.niche.com/k12/yu-ming-charter-school-oakland-ca/",
        "name": "Niche",
    },
    "greatschools": {
        "url": "https://www.greatschools.org/california/oakland/19632-Yu-Ming-Charter-School/",
        "name": "GreatSchools",
    },
}

# --- Chinese Platforms ---
CHINESE_PLATFORM_CONFIG = {
    "1point3acres": {
        "base_url": "https://www.1point3acres.com/bbs/",
        "search_paths": [
            "forum.php?mod=forumdisplay&fid=293",  # 留学申请
            "forum.php?mod=forumdisplay&fid=99",   # 生活版
        ],
    },
    "zhihu": {
        "search_url": "https://www.zhihu.com/search",
    },
    "xiaohongshu": {
        "search_url": "https://www.xiaohongshu.com/search_result/",
    },
}
