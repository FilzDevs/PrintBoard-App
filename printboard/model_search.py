"""Multi-Platform 3D Model Meta-Search Engine for PrintBoard Studio.
Queries all 6 major 3D model platforms in parallel:
1. Printables (Official GraphQL API)
2. MakerWorld (Official Search Service API)
3. Thingiverse (Official v2 REST API with automatic view-token handshake)
4. MyMiniFactory (Official Search JSON API)
5. Thangs (Live Search Index for thangs.com/designer/.../3d-model)
6. Cults3D (Live Search Index for cults3d.com/en/3d-model)
"""
from __future__ import annotations

import html as html_mod
import json
import re
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) "
    "Gecko/20100101 Firefox/128.0"
)

PLATFORM_META = {
    "Printables": {
        "color": "#FA6831",
        "home": "https://www.printables.com",
        "search_tpl": "https://www.printables.com/search/models?q={q}",
        "desc": "Prusa Community-Plattform mit geprüften STL- & 3MF-Profilen",
    },
    "MakerWorld": {
        "color": "#10B981",
        "home": "https://makerworld.com",
        "search_tpl": "https://makerworld.com/en/search/models?keyword={q}",
        "desc": "Bambu Lab Ökosystem mit fertigen 3MF-Druckprofilen",
    },
    "Thingiverse": {
        "color": "#3B82F6",
        "home": "https://www.thingiverse.com",
        "search_tpl": "https://www.thingiverse.com/search?q={q}&type=things",
        "desc": "Das größte klassische Open-Source-Archiv für 3D-Modelle",
    },
    "MyMiniFactory": {
        "color": "#06B6D4",
        "home": "https://www.myminifactory.com",
        "search_tpl": "https://www.myminifactory.com/search/?query={q}",
        "desc": "Kuratierte Community-Objekte, Tabletop, Gadgets & Zubehör",
    },
    "Thangs": {
        "color": "#8B5CF6",
        "home": "https://thangs.com",
        "search_tpl": "https://thangs.com/search/{q}?scope=all",
        "desc": "Geometrische 3D-Suchmaschine über alle großen Plattformen",
    },
    "Cults3D": {
        "color": "#EC4899",
        "home": "https://cults3d.com",
        "search_tpl": "https://cults3d.com/en/search?q={q}",
        "desc": "Unabhängiger Marktplatz für Designer, Art-Toys & Functional Prints",
    },
}

TRENDING_TOPICS = [
    "Gridfinity",
    "Voron",
    "3DBenchy",
    "Bambu AMS",
    "Spool Holder",
    "Multiboard",
    "Dummy 13",
    "Cable Chain",
    "Calicat",
    "Filament Clip",
]

_SEARCH_CACHE: Dict[str, tuple[float, List[Dict]]] = {}
_CACHE_TTL = 300.0

_TV_TOKEN_LOCK = threading.Lock()
_TV_VIEW_TOKEN: str = ""
_TV_TOKEN_EXP: float = 0.0


def build_platform_links(query: str) -> List[Dict]:
    q_clean = (query or "").strip()
    q_enc = urllib.parse.quote(q_clean) if q_clean else ""
    out = []
    for name, meta in PLATFORM_META.items():
        url = meta["search_tpl"].format(q=q_enc) if q_clean else meta["home"]
        out.append({
            "name": name,
            "color": meta["color"],
            "url": url,
            "home": meta["home"],
            "desc": meta["desc"],
        })
    return out


def search_printables(query: str, limit: int = 12) -> List[Dict]:
    """1. Printables Official GraphQL API."""
    gql = {
        "operationName": "SearchModels",
        "variables": {"query": query, "limit": limit, "offset": 0},
        "query": """
        query SearchModels($query: String!, $limit: Int, $offset: Int) {
            searchPrints2(query: $query, limit: $limit, offset: $offset) {
                items {
                    id
                    name
                    slug
                    likesCount
                    downloadCount
                    user { publicUsername }
                    image { filePath }
                }
            }
        }
        """,
    }
    req = urllib.request.Request(
        "https://api.printables.com/graphql/",
        data=json.dumps(gql).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    results = []
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read())
        items = ((data.get("data") or {}).get("searchPrints2") or {}).get("items") or []
        for it in items:
            mid = str(it.get("id") or "")
            slug = str(it.get("slug") or "")
            name = str(it.get("name") or "3D-Modell").strip()
            img_path = ((it.get("image") or {}).get("filePath") or "").lstrip("/")
            thumb = f"https://media.printables.com/{img_path}" if img_path else ""
            user = ((it.get("user") or {}).get("publicUsername")) or "Printables Creator"
            url = f"https://www.printables.com/model/{mid}-{slug}" if slug else f"https://www.printables.com/model/{mid}"
            results.append({
                "id": f"printables_{mid}",
                "title": name,
                "author": user,
                "source": "Printables",
                "source_color": PLATFORM_META["Printables"]["color"],
                "url": url,
                "thumbnail": thumb,
                "likes": int(it.get("likesCount") or 0),
                "downloads": int(it.get("downloadCount") or 0),
                "is_free": True,
                "snippet": f"Printables Modell #{mid} von @{user}",
            })
    except Exception:
        pass
    return results


def search_makerworld(query: str, limit: int = 12) -> List[Dict]:
    """2. MakerWorld Official Search Service API."""
    q_enc = urllib.parse.quote(query)
    url = f"https://makerworld.com/api/v1/search-service/select/design2?keyword={q_enc}&limit={limit}&offset=0"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    results = []
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read())
        hits = data.get("hits") or []
        for it in hits[:limit]:
            mid = str(it.get("id") or "")
            slug = str(it.get("slug") or "")
            title = str(it.get("title") or it.get("titleTranslated") or "MakerWorld 3D-Modell").strip()
            thumb = str(it.get("cover") or it.get("coverLandscape") or "")
            creator = it.get("designCreator") or {}
            author = str(creator.get("name") or creator.get("handle") or "MakerWorld Creator")
            likes = int(it.get("likeCount") or 0)
            downloads = int(it.get("downloadCount") or it.get("printCount") or 0)
            model_url = f"https://makerworld.com/en/models/{mid}-{slug}" if slug else f"https://makerworld.com/en/models/{mid}"
            results.append({
                "id": f"makerworld_{mid}",
                "title": title,
                "author": author,
                "source": "MakerWorld",
                "source_color": PLATFORM_META["MakerWorld"]["color"],
                "url": model_url,
                "thumbnail": thumb,
                "likes": likes,
                "downloads": downloads,
                "is_free": True,
                "snippet": f"MakerWorld 3MF/STL Druckprofil von @{author}",
            })
    except Exception:
        pass
    return results


def _get_thingiverse_view_token() -> str:
    """Acquire and cache anonymous JWT view token from Thingiverse v2 auth endpoint."""
    global _TV_VIEW_TOKEN, _TV_TOKEN_EXP
    now = time.time()
    with _TV_TOKEN_LOCK:
        if _TV_VIEW_TOKEN and now < _TV_TOKEN_EXP:
            return _TV_VIEW_TOKEN
        req = urllib.request.Request(
            "https://api.thingiverse.com/v2/auth/view",
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
        tok = str(data.get("access") or "")
        if tok:
            _TV_VIEW_TOKEN = tok
            _TV_TOKEN_EXP = now + 1800.0
        return tok


def search_thingiverse(query: str, limit: int = 12) -> List[Dict]:
    """3. Thingiverse Official v2 Search REST API."""
    results = []
    try:
        tok = _get_thingiverse_view_token()
        if not tok:
            return results
        q_enc = urllib.parse.quote(query)
        url = f"https://api.thingiverse.com/v2/search/things?term={q_enc}&page=1&per_page={limit}&sort=relevant"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Authorization": f"Bearer {tok}",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read())
        hits = data.get("hits") or []
        for it in hits[:limit]:
            mid = str(it.get("id") or "")
            name = str(it.get("name") or "Thingiverse 3D-Modell").strip()
            pub_url = str(it.get("public_url") or f"https://www.thingiverse.com/thing:{mid}")
            raw_thumb = str(it.get("preview_image") or it.get("thumbnail") or "")
            if "url=https://cdn.thingiverse.com/" in raw_thumb:
                thumb = raw_thumb.split("url=", 1)[1].split("&", 1)[0]
            else:
                thumb = raw_thumb
            creator = it.get("creator") or {}
            author = str(creator.get("name") or creator.get("first_name") or "Thingiverse Maker")
            likes = int(it.get("like_count") or 0)
            downloads = int(it.get("collect_count") or it.get("make_count") or likes * 3)
            results.append({
                "id": f"thingiverse_{mid}",
                "title": name,
                "author": author,
                "source": "Thingiverse",
                "source_color": PLATFORM_META["Thingiverse"]["color"],
                "url": pub_url,
                "thumbnail": thumb,
                "likes": likes,
                "downloads": downloads,
                "is_free": True,
                "snippet": f"Thingiverse thing:{mid} von @{author}",
            })
    except Exception:
        pass
    return results


def search_myminifactory(query: str, limit: int = 12) -> List[Dict]:
    """4. MyMiniFactory Official Search JSON API."""
    q_enc = urllib.parse.quote(query)
    url = f"https://www.myminifactory.com/search/fetch_search?query={q_enc}&page=1"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/javascript, */*",
        },
    )
    results = []
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            data = json.loads(r.read())
        items = data.get("objectResults") or []
        for it in items[:limit]:
            mid = str(it.get("id") or "")
            name = str(it.get("name") or "3D-Modell").strip()
            abs_url = str(it.get("absolute_url") or "")
            if not abs_url and it.get("url"):
                abs_url = f"https://www.myminifactory.com/object/{it['url']}"
            thumb = str(it.get("obj_img") or it.get("obj_original_img") or "")
            author = str(it.get("user_name") or it.get("user_username") or "MMF Designer")
            visits = int(it.get("visits") or 0)
            price_obj = it.get("price") or {}
            price_val = float(price_obj.get("value") or 0.0) if isinstance(price_obj, dict) else 0.0
            results.append({
                "id": f"mmf_{mid}",
                "title": name,
                "author": author,
                "source": "MyMiniFactory",
                "source_color": PLATFORM_META["MyMiniFactory"]["color"],
                "url": abs_url or f"https://www.myminifactory.com/search/?query={q_enc}",
                "thumbnail": thumb,
                "likes": max(1, visits // 12),
                "downloads": visits,
                "is_free": price_val <= 0.0,
                "snippet": "Kostenloses 3D-Modell" if price_val <= 0.0 else f"Premium Design ({price_val:.2f} $)",
            })
    except Exception:
        pass
    return results


def _search_startpage_site(query: str, site_filter: str, source_name: str, limit: int = 10) -> List[Dict]:
    """Query Startpage image/model index for Thangs & Cults3D to obtain both direct 3D model URLs and real thumbnails."""
    data = urllib.parse.urlencode({"query": f"{query} site:{site_filter}", "cat": "pics"}).encode("utf-8")
    req = urllib.request.Request(
        "https://www.startpage.com/sp/search",
        data=data,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
        },
    )
    results = []
    try:
        with urllib.request.urlopen(req, timeout=6) as r:
            raw_html = r.read().decode("utf-8", errors="ignore")

        seen_urls = set()
        for idx, m in enumerate(re.finditer(r"\{[^{}]*\"altClickUrl\":\"(https://[^\"]+)\"[^{}]*\}", raw_html)):
            block_str = m.group(0)
            try:
                obj = json.loads(block_str)
            except Exception:
                continue

            base_url = str(obj.get("altClickUrl") or "").split("?srsltid=")[0]
            if not base_url or base_url in seen_urls:
                continue
            seen_urls.add(base_url)

            raw_title = str(obj.get("title") or "").strip()
            title = re.sub(r"<[^>]+>", "", html_mod.unescape(raw_title)).strip()

            author = f"{source_name} Designer"
            m_by = re.search(r"3D model by\s+(.+?)\s+on Thangs", title, re.I)
            if m_by:
                author = m_by.group(1).strip()
            elif "/designer/" in base_url:
                try:
                    des_part = urllib.parse.unquote(base_url.split("/designer/", 1)[1].split("/", 1)[0])
                    if des_part:
                        author = des_part
                except Exception:
                    pass

            title = re.sub(r"\s*[-・|]\s*(?:3D model by .*|Free .*?Cults.*|Cults\s*3D.*|Thangs.*)$", "", title, flags=re.I).strip()

            # Prefer the fast cached Bing/Startpage thumbnail URL (piurl) or rawImageUrl
            thumb = ""
            t_url = str(obj.get("thumbnailUrl") or "")
            if "piurl=" in t_url:
                thumb = urllib.parse.unquote(t_url.split("piurl=", 1)[1].split("&", 1)[0])
            if not thumb:
                thumb = str(obj.get("rawImageUrl") or "")

            results.append({
                "id": f"{source_name.lower()}_{idx}_{abs(hash(base_url)) % 100000}",
                "title": title or f"{query} ({source_name})",
                "author": author,
                "source": source_name,
                "source_color": PLATFORM_META[source_name]["color"],
                "url": base_url,
                "thumbnail": thumb,
                "likes": 0,
                "downloads": 0,
                "is_free": True,
                "snippet": f"3D-Druckmodell auf {source_name} von {author}",
            })
            if len(results) >= limit:
                break
    except Exception:
        pass
    return results


def search_thangs(query: str, limit: int = 10) -> List[Dict]:
    """5. Thangs 3D Model Search."""
    return _search_startpage_site(query, "thangs.com/designer", "Thangs", limit=limit)


def search_cults3d(query: str, limit: int = 10) -> List[Dict]:
    """6. Cults3D 3D Model Search."""
    return _search_startpage_site(query, "cults3d.com/en/3d-model", "Cults3D", limit=limit)


def search_models(query: str = "", site: str = "all", sort: str = "popular", limit: int = 60) -> Dict:
    """Unified multi-platform 3D model search across all 6 platforms."""
    effective_query = (query or "").strip() or "Gridfinity"
    site_norm = (site or "all").strip().lower()
    cache_key = f"{effective_query.lower()}::all"

    now = time.time()
    cached = _SEARCH_CACHE.get(cache_key)
    if cached and (now - cached[0]) < _CACHE_TTL:
        all_items = list(cached[1])
    else:
        all_items = []
        providers = [
            ("printables", search_printables, 12),
            ("makerworld", search_makerworld, 12),
            ("thingiverse", search_thingiverse, 12),
            ("myminifactory", search_myminifactory, 12),
            ("thangs", search_thangs, 10),
            ("cults3d", search_cults3d, 10),
        ]
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(fn, effective_query, lim) for _, fn, lim in providers]
            for fut in futures:
                try:
                    all_items.extend(fut.result(timeout=7))
                except Exception:
                    pass

        if all_items:
            _SEARCH_CACHE[cache_key] = (now, list(all_items))

    # Compute counts across all 6 platforms before filtering by active site tab
    counts_by_source: Dict[str, int] = {}
    for it in all_items:
        s_name = it.get("source", "Web")
        counts_by_source[s_name] = counts_by_source.get(s_name, 0) + 1

    if site_norm != "all":
        items = [it for it in all_items if it.get("source", "").lower() == site_norm]
    else:
        items = list(all_items)

    # Sort items
    if sort == "downloads":
        items.sort(key=lambda x: (int(x.get("downloads") or 0), int(x.get("likes") or 0)), reverse=True)
    elif sort == "likes":
        items.sort(key=lambda x: (int(x.get("likes") or 0), int(x.get("downloads") or 0)), reverse=True)
    elif sort == "title":
        items.sort(key=lambda x: str(x.get("title") or "").lower())
    else:
        # Round-robin interleave across all 6 platforms so every platform is visible right at the top!
        by_src: Dict[str, List[Dict]] = {}
        for it in items:
            by_src.setdefault(it["source"], []).append(it)
        interleaved = []
        order = ("Printables", "MakerWorld", "Thingiverse", "MyMiniFactory", "Thangs", "Cults3D")
        max_len = max((len(v) for v in by_src.values()), default=0)
        for i in range(max_len):
            for src_name in order:
                lst = by_src.get(src_name)
                if lst and i < len(lst):
                    interleaved.append(lst[i])
        items = interleaved

    return {
        "ok": True,
        "query": effective_query,
        "site": site_norm,
        "sort": sort,
        "total": len(all_items),
        "filtered_total": len(items),
        "counts": counts_by_source,
        "items": items[:limit],
        "platforms": build_platform_links(effective_query),
        "trending": TRENDING_TOPICS,
    }
