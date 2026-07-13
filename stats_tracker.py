"""Usage statistics tracking."""
import json
import os
from datetime import datetime

STATS_FILE = os.path.join(os.path.dirname(__file__), "data", "stats.json")


def log_search(keyword: str, provider: str, count: int, username: str = "anonymous", search_type: str = "search"):
    """Log a search event to stats file."""
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    stats = []
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            stats = json.load(f)
    
    stats.append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "keyword": keyword[:50],
        "provider": provider,
        "count": count,
        "user": username,
        "type": search_type,
    })
    
    # Keep last 20k records
    if len(stats) > 20000:
        stats = stats[-20000:]
    
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def get_stats(days: int = 7) -> dict:
    """Get aggregated stats for the last N days."""
    if not os.path.exists(STATS_FILE):
        return {"searches_today": 0, "total_searches": 0, "top_keywords": [], "provider_breakdown": {}, "recent": []}
    
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        stats = json.load(f)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Filter by days
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [s for s in stats if s["time"][:10] >= cutoff]
    today_stats = [s for s in stats if s["time"][:10] == today]
    
    # Top keywords
    kw_count = {}
    for s in recent:
        kw = s["keyword"]
        kw_count[kw] = kw_count.get(kw, 0) + 1
    top_kw = sorted(kw_count.items(), key=lambda x: -x[1])[:20]
    
    # Provider breakdown
    prov_count = {}
    for s in recent:
        p = s["provider"]
        prov_count[p] = prov_count.get(p, 0) + 1
    
    return {
        "searches_today": len(today_stats),
        "total_searches": len(recent),
        "top_keywords": [{"keyword": k, "count": c} for k, c in top_kw],
        "provider_breakdown": prov_count,
        "recent": recent[-50:],
    }
