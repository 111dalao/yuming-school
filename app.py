"""Flask backend serving manual + monitoring dashboard."""
import json
import os
import re
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

try:
    import jieba
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False

app = Flask(__name__)

ROOT = Path(__file__).parent
DATA_FILE = str(ROOT / "output" / "master_merged.json")
MANUAL_FILE = str(ROOT / "生活与工作手册.html")

STOP_WORDS = {
    "的", "了", "是", "我", "在", "不", "就", "也", "都", "和", "你",
    "有", "他", "这", "个", "们", "到", "说", "要", "会", "可以", "没有",
    "什么", "那", "很", "吧", "啊", "呢", "吗", "把", "被", "让", "给",
    "从", "对", "但", "还", "而", "着", "得", "能", "又", "去", "来",
    "一", "上", "下", "过", "想", "看", "用", "没", "做", "为", "因为",
    "所以", "如果", "已经", "还是", "就是", "这个", "那个", "怎么", "现在",
    "真的", "而且", "或者", "但是", "然后", "知道", "觉得", "这样", "那样",
    "一下", "一些", "一直", "一个", "不是", "只是", "可能", "应该", "已经",
    "以前", "以后", "为什么", "什么", "自己", "大家", "起来", "出来", "下去",
    "上来", "最后", "还有", "只有", "只要", "其实", "虽然", "不过", "这些",
    "那些", "所有", "不要", "不会", "不能", "没有", "这里", "那里", "时候",
    "他们", "我们", "你们", "人家", "每个", "东西", "事情", "样子", "地方",
    "哈哈", "嗯", "额", "呃", "哦", "噢", "嘿", "呀", "哇",
    "http", "https", "www", "com", "cn", "org",
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "shall",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "neither", "each", "every", "all", "any", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "than", "too",
    "very", "just", "about", "also", "if", "then", "here", "there",
    "when", "where", "why", "how",
    "nbsp", "quot", "amp", "gt", "lt",
    # Chinese commons
    "一个", "一些", "一种", "这个", "那个", "这些", "那些",
    "不要", "可以", "什么", "怎么", "为什么", "因为", "所以",
    "已经", "但是", "而且", "还是", "如果", "虽然", "不过",
}

# ── In-memory cache ────────────────────────────────────────────
_cache: dict = {}

_DATE_FMTS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
)

GROUP_LABELS = {
    "school_core": "学校核心",
    "international_students": "留学生/国际交流",
    "housing": "住宿/租房",
    "safety": "安全/治安",
    "transportation": "交通出行",
    "education_system": "教育体系",
    "community_life": "社区生活",
    "cost_of_living": "生活成本",
    "healthcare": "医疗健康",
    "news": "综合新闻",
    "all": "综合资讯",
    "education": "教育相关",
}


def _parse_date(date_str: str) -> datetime | None:
    if not date_str:
        return None
    s = date_str.strip()
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _load_master():
    """Load the master merged JSON output from scrapers."""
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    raw = data.get("results", [])
    for i, item in enumerate(raw):
        item["_idx"] = i
        item["_dt"] = _parse_date(item.get("date", ""))
        item["_day"] = (item.get("date", "")[:10]) if item.get("date") else ""
        # Normalize platform
        plat = item.get("platform", "").strip()
        if plat.startswith("news_"):
            item["_plat_group"] = "news"
        elif plat == "google_news":
            item["_plat_group"] = "Google News"
        elif plat == "youtube":
            item["_plat_group"] = "YouTube"
        else:
            item["_plat_group"] = plat or "other"
    return raw


def get_data():
    if "data" not in _cache:
        _cache["data"] = _load_master()
    return _cache["data"]


def _filter_by_date(items, date_from, date_to):
    if not date_from and not date_to:
        return items
    dt_from = _parse_date(date_from) if date_from else None
    dt_to = _parse_date(date_to) if date_to else None
    if dt_to:
        dt_to = dt_to.replace(hour=23, minute=59, second=59)
    out = []
    for item in items:
        dt = item.get("_dt")
        if not dt:
            out.append(item)
            continue
        if dt_from and dt < dt_from:
            continue
        if dt_to and dt > dt_to:
            continue
        out.append(item)
    return out


def get_stats(date_from=None, date_to=None):
    key = ("stats", date_from or "", date_to or "")
    if key not in _cache:
        data = _filter_by_date(get_data(), date_from, date_to)
        total = len(data)

        # Relevance score distribution (buckets)
        score_bins = Counter()
        for item in data:
            s = item.get("relevance_score", 0)
            if s >= 0.8:
                score_bins[5] += 1
            elif s >= 0.6:
                score_bins[4] += 1
            elif s >= 0.4:
                score_bins[3] += 1
            elif s >= 0.2:
                score_bins[2] += 1
            else:
                score_bins[1] += 1

        # Topic group distribution
        group_counts = Counter()
        for item in data:
            group_counts[item.get("keyword_group", "other")] += 1

        # Daily counts
        daily = Counter()
        for item in data:
            d = item.get("_day")
            if d:
                daily[d] += 1

        days = sorted(daily.keys())
        daily_result = [
            {"date": d, "count": daily[d]} for d in days
        ]

        # Platform distribution
        plat_counts = Counter()
        for item in data:
            plat_counts[item.get("_plat_group", "other")] += 1

        _cache[key] = {
            "total": total,
            "score_bins": dict(score_bins),
            "group_counts": dict(group_counts),
            "daily": daily_result,
            "platforms": [{"name": k, "value": v} for k, v in plat_counts.most_common()],
            "days": set(days),
        }
    return _cache[key]


def get_words(top_n=120, date_from=None, date_to=None):
    key = ("words", top_n, date_from or "", date_to or "")
    if key not in _cache:
        data = _filter_by_date(get_data(), date_from, date_to)
        all_text = " ".join(
            (item.get("title", "") + " " + item.get("content", ""))
            for item in data
        )
        if HAS_JIEBA:
            words = jieba.lcut(all_text)
            words = [w.strip() for w in words if len(w.strip()) >= 2]
        else:
            words = re.findall(r"[一-鿿]{2,}", all_text)
            # Also extract English words
            eng_words = re.findall(r"[a-zA-Z]{3,}", all_text.lower())
            words.extend(eng_words)
        filtered = [w for w in words if w not in STOP_WORDS and len(w) >= 2]
        counter = Counter(filtered)
        _cache[key] = [{"name": w, "value": c} for w, c in counter.most_common(top_n)]
    return _cache[key]


def _get_date_params():
    date_from = request.args.get("from", "").strip() or None
    date_to = request.args.get("to", "").strip() or None
    return date_from, date_to


def _precompute():
    try:
        get_data()
        get_stats()
        get_words(120)
    except Exception:
        pass


# ── Page routes ────────────────────────────────────────────────

@app.route("/")
def manual():
    """Serve the self-contained HTML manual."""
    if os.path.exists(MANUAL_FILE):
        return send_file(MANUAL_FILE, mimetype="text/html; charset=utf-8")
    return render_template("dashboard.html")


@app.route("/dashboard")
def index():
    return render_template("dashboard.html")


@app.route("/dashboard/detail")
def detail():
    return render_template("detail.html")


# ── Dashboard APIs ─────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    date_from, date_to = _get_date_params()
    s = get_stats(date_from, date_to)
    days = s["days"]
    return jsonify({
        "total_discussions": s["total"],
        "total_topics": len(s["group_counts"]),
        "total_days": len(days),
        "total_platforms": len(s["platforms"]),
        "date_range": {
            "start": min(days, default=""),
            "end": max(days, default=""),
        },
    })


@app.route("/api/topics")
def api_topics():
    date_from, date_to = _get_date_params()
    s = get_stats(date_from, date_to)
    result = []
    for group_key, count in sorted(s["group_counts"].items(), key=lambda x: -x[1]):
        label = GROUP_LABELS.get(group_key, group_key)
        result.append({"name": label, "key": group_key, "count": count})
    return jsonify(result)


@app.route("/api/relevance")
def api_relevance():
    """Relevance score distribution (replaces sentiment distribution)."""
    date_from, date_to = _get_date_params()
    s = get_stats(date_from, date_to)
    bins = s["score_bins"]
    labels_map = {
        1: "低相关 (0-0.2)",
        2: "一般 (0.2-0.4)",
        3: "中等 (0.4-0.6)",
        4: "高 (0.6-0.8)",
        5: "极高 (0.8-1.0)",
    }
    colors_map = {
        1: "#f87171", 2: "#fb923c", 3: "#facc15", 4: "#4ade80", 5: "#34d399",
    }
    total = sum(bins.values())
    result = []
    for score in range(1, 6):
        count = bins.get(score, 0)
        pct = round(count / total * 100, 1) if total else 0
        result.append({
            "score": score,
            "label": labels_map.get(score, str(score)),
            "count": count,
            "percentage": pct,
            "color": colors_map.get(score, "#888"),
        })
    return jsonify(result)


@app.route("/api/daily")
def api_daily():
    date_from, date_to = _get_date_params()
    return jsonify(get_stats(date_from, date_to)["daily"])


@app.route("/api/words")
def api_words():
    top_n = request.args.get("top", 120, type=int)
    date_from, date_to = _get_date_params()
    words = get_words(top_n, date_from, date_to)
    fallback_key = ("words", top_n, "", "")
    if not words and fallback_key not in _cache:
        return jsonify({"loading": True, "words": []})
    return jsonify({"loading": False, "words": words})


@app.route("/api/insights")
def api_insights():
    date_from, date_to = _get_date_params()
    s = get_stats(date_from, date_to)
    data = _filter_by_date(get_data(), date_from, date_to)

    high_relevance = sum(
        1 for item in data if item.get("relevance_score", 0) >= 0.6
    )
    total = s["total"]

    daily_counts = Counter(item.get("_day") for item in data if item.get("_day"))
    peak_day = daily_counts.most_common(1)[0] if daily_counts else ("", 0)

    top_group = max(s["group_counts"].items(), key=lambda x: x[1]) if s["group_counts"] else ("", 0)

    total_words = sum(
        len(item.get("content", "")) + len(item.get("title", ""))
        for item in data
    )

    return jsonify({
        "high_relevance_pct": round(high_relevance / total * 100, 1) if total else 0,
        "total_discussions": total,
        "peak_day": {"date": peak_day[0], "count": peak_day[1]},
        "top_group": {
            "name": GROUP_LABELS.get(top_group[0], top_group[0]),
            "count": top_group[1],
        },
        "total_words_k": round(total_words / 1000, 1),
    })


@app.route("/api/platforms")
def api_platforms():
    date_from, date_to = _get_date_params()
    s = get_stats(date_from, date_to)
    return jsonify(s["platforms"])


# ── Detail APIs ────────────────────────────────────────────────

@app.route("/api/discussion/<int:idx>")
def api_discussion_detail(idx):
    data = get_data()
    if idx < 0 or idx >= len(data):
        return jsonify({"error": "not found"}), 404
    item = data[idx]
    title = item.get("title_zh", "") or item.get("title", "")
    return jsonify({
        "title": title,
        "title_en": item.get("title", ""),
        "content": item.get("content", ""),
        "date": item.get("date", ""),
        "platform": item.get("_plat_group", item.get("platform", "")),
        "url": item.get("url", ""),
        "author": item.get("author", ""),
        "keyword_group": GROUP_LABELS.get(
            item.get("keyword_group", ""), item.get("keyword_group", "")
        ),
        "keyword_group_key": item.get("keyword_group", ""),
        "relevance_score": item.get("relevance_score", 0),
        "matched_keyword": item.get("matched_keyword_zh", "") or item.get("matched_keyword", ""),
    })


@app.route("/api/discussions")
def api_discussions():
    data = get_data()

    q = request.args.get("q", "").strip()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    platform = request.args.get("platform", "").strip()
    groups_raw = request.args.get("groups", "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(50, max(1, request.args.get("per_page", 50, type=int)))

    groups_set = {g.strip() for g in groups_raw.split(",") if g.strip()}

    dt_from = _parse_date(date_from) if date_from else None
    dt_to = None
    if date_to:
        dt_to = _parse_date(date_to)
        if dt_to:
            dt_to = dt_to.replace(hour=23, minute=59, second=59)

    filtered = []
    for item in data:
        if platform and item.get("_plat_group", "") != platform:
            continue
        if dt_from or dt_to:
            dt = item.get("_dt")
            if dt:
                if dt_from and dt < dt_from:
                    continue
                if dt_to and dt > dt_to:
                    continue
        if q:
            searchable = f"{item.get('title', '')} {item.get('content', '')}".lower()
            if q.lower() not in searchable:
                continue
        if groups_set:
            if item.get("keyword_group", "") not in groups_set:
                continue
        filtered.append(item)

    filtered.sort(
        key=lambda x: x.get("_dt") or datetime(1970, 1, 1),
        reverse=True,
    )

    total = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    start = (page - 1) * per_page
    page_items = filtered[start : start + per_page]

    items = [
        {
            "idx": item["_idx"],
            "title": item.get("title_zh", "") or item.get("title", ""),
            "title_en": item.get("title", ""),
            "content": item.get("content", "")[:300],
            "date": item.get("date", ""),
            "platform": item.get("_plat_group", item.get("platform", "")),
            "keyword_group": GROUP_LABELS.get(
                item.get("keyword_group", ""), item.get("keyword_group", "")
            ),
            "keyword_group_key": item.get("keyword_group", ""),
            "relevance_score": item.get("relevance_score", 0),
        }
        for item in page_items
    ]

    return jsonify({
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    })


@app.route("/api/group-options")
def api_group_options():
    date_from, date_to = _get_date_params()
    s = get_stats(date_from, date_to)
    result = [
        {"value": k, "label": GROUP_LABELS.get(k, k)}
        for k in s["group_counts"]
    ]
    result.sort(key=lambda x: x["label"])
    return jsonify(result)


@app.route("/api/summary")
def api_summary():
    """Return a quick text summary for the hero section."""
    date_from, date_to = _get_date_params()
    s = get_stats(date_from, date_to)
    data = _filter_by_date(get_data(), date_from, date_to)

    top_topics = sorted(
        s["group_counts"].items(), key=lambda x: -x[1]
    )[:3]
    topics_str = "、".join(
        GROUP_LABELS.get(k, k) for k, _ in top_topics
    )

    platforms = sorted(s["platforms"], key=lambda x: -x["value"])
    top_plat = platforms[0]["name"] if platforms else "多平台"

    return jsonify({
        "summary": f"涵盖 {len(s['group_counts'])} 个主题维度，"
                   f"最活跃话题: {topics_str}，"
                   f"数据主要来自 {top_plat} 等多个来源。",
    })


if __name__ == "__main__":
    threading.Thread(target=_precompute, daemon=True).start()
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
