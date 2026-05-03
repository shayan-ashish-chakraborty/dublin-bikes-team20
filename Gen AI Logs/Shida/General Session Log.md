# Claude Code Session Log — Dublin Bikes Team 20

---

## 2026-02-25 — Scrapper went down in the EC2

**User prompt:**
> Scrapper stopped in the ec2, and log attached.

**AI response:**
> Most likely too many open connections to the DB. Each scraper runs in a `while True` loop and opens a new SQLAlchemy connection on every iteration without properly closing the previous one. Over time the connections accumulate until MySQL hits its `max_connections` limit (default 151 on RDS `t2.micro`), at which point new connections are refused and the scraper crashes with a `OperationalError: (2003) Can't connect to MySQL server` or `Too many connections` error.
>
> Check the logs to confirm — you should see something like:
> ```
> sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError)
> (1040, 'Too many connections')
> ```
> The fix is to use a connection pool with a bounded size and make sure each iteration closes or returns its connection. SQLAlchemy's `create_engine` already pools by default — the issue is usually that the session is never closed after each write. Wrap each DB write in a `try/finally` and call `session.close()`, or use a context manager:
> ```python
> with Session(engine) as session:
>     session.add(record)
>     session.commit()
> ```
> That guarantees the connection is returned to the pool after every scrape cycle regardless of whether it succeeds or fails.

---

## 2026-04-08 — Forecast Model Not Loading (`bike_forecast`)

**User prompt:**
```
{"error":"Models could not be loaded: [Errno 2] No such file or directory:
'/Users/sean/Documents/GitHub/dublin-bikes-team20/main_project/main_project/bike_forecast/models/bike_model.pkl'"}
```

**AI response:**
> The path in the error has `main_project` duplicated — `.../main_project/main_project/...`. That means the path is being constructed by appending `"main_project"` onto a base that already points inside `main_project/`. Can you show me the path-building code in `forecast.py`?

---

**User prompt:**
> here:
> ```python
> _BASE         = pathlib.Path(__file__).resolve().parent.parent.parent
> _FORECAST_DIR = _BASE / "main_project" / "bike_forecast" / "models"
> ```

**AI response:**
> That's the bug. `forecast.py` lives at `main_project/bike_forecast/models/forecast.py`, so `.parent.parent.parent` climbs up to `main_project/` — not the repo root. Then you're appending `"main_project"` again, which produces the doubled path.
>
> Change it to anchor `_FORECAST_DIR` directly off `__file__`:
> ```python
> _FORECAST_DIR = pathlib.Path(__file__).resolve().parent   # models/ directly
> _BASE         = _FORECAST_DIR.parent.parent.parent        # repo root
> ```
> That way `_FORECAST_DIR` is always exactly the folder `forecast.py` itself lives in, regardless of the working directory.

---

## 2026-04-13 — Weather Page Not Refreshing (`weather`)

**User prompt:**
> 为什么weather page 不会在更新了，Live conditions & hourly forecast · Updated: Mon, 13 Apr 09:24 a.m.
> *(Why is the weather page not updating — it's been stuck on Mon 13 Apr 09:24 a.m.)*

**AI response:**
> Two things are happening together.
>
> **Primary cause — the EC2 scrapers have stopped.** The `current` and `hourly` MySQL tables are populated by two background workers on EC2 (`current_weather.py` and `hourly_weather.py`). They both stopped at ~09:24 a.m., so the DB has been serving stale data since then. Check `/logs/current_weather.log` and `/logs/hourly_weather.log` to see why they died, then restart them.
>
> **Code issue — the frontend fallback never triggers.** `loadCurrent()` calls `/api/weather/db/current` first. When the scrapers are down that route still returns HTTP 200 with stale data, so the JS never falls back to the live OpenWeather API. The fallback only fires on a request error, not on stale content.

---

## 2026-04-08 — Forecast Model Not Loading (`bike_forecast`)

**User prompt:**
> scrapers were down, restarted them. but how do I fix the frontend so this doesn't break silently next time?

**AI response:**
> For current conditions, skip the DB entirely — always call the live OpenWeather endpoint directly. The DB is only useful for historical data; a "live conditions" widget should never serve a stale row.
>
> In `weather.html`, find `loadCurrent()` (around line 378) and `fetchCurrentWeatherRow()` (around line 321). In both functions, remove the DB fetch block and go straight to `/api/weather/openweather/current`. The hourly forecast can stay on DB-first since forward-looking data is less time-sensitive.

---

## 2026-04-13 — Page is loaded very slow

**User prompt:**
> how can I improve the efficiency of the weather data fetching?

**AI response:**
> The main win is hitting the DB first before calling the OpenWeather API. The DB is local to your network — a query on RDS typically comes back in a few milliseconds. An external API call to OpenWeather adds a full round-trip over the internet, usually 200–500ms, plus you're rate-limited and using up your API quota on every request.
>
> The pattern should be:
> 1. Try DB — if it has fresh data, return it immediately
> 2. Only call the OpenWeather API if the DB is empty, unreachable, or the data is stale
>
> This way the fast path (DB hit) handles the vast majority of requests, and the API is purely a safety net.

---

**User prompt:**
> so when should I use DB first vs going straight to the API?

**AI response:**
> It depends on how time-sensitive the data is and how frequently it changes:
>
> | Situation | Approach |
> |-----------|----------|
> | **Hourly forecast** | DB first — scrapers refresh it every 5 min, data is forward-looking so a few minutes of staleness is fine |
> | **Live current conditions** | API first (or API only) — users expect this to be real-time; a 10-minute-old "current" temperature is misleading |
> | **Station bike counts** | API first — JCDecaux updates every minute, DB cache goes stale quickly |
> | **Historical / chart data** | DB only — no point hitting an external API for data you've already stored |
>
> The rule of thumb: if the user sees the word "live" or "current" on screen, go straight to the API. If it's a forecast or trend, DB first is fine.

---

**User prompt:**
> the whole app feels slow when running on EC2, page loads are taking a while. any idea why?

**AI response:**
> Most likely you're running Flask's built-in development server directly (`app.run()`). That server is single-threaded — it handles one request at a time, so if one request is slow (a DB query, an API call) everything else queues behind it.
>
> The fix is to put **nginx + Gunicorn** in front of Flask:
> - **Gunicorn** runs multiple worker processes (typically `2 * CPU cores + 1`), so requests are handled in parallel
> - **nginx** sits in front as a reverse proxy — it handles static files itself without touching Python at all, manages keep-alive connections, and buffers slow clients so your workers stay free
>
> On a `t2.micro` (1 vCPU) a starting config would be:
> ```
> gunicorn --workers 3 --bind 127.0.0.1:8000 "main_project:create_app()"
> ```
> Then nginx proxies `localhost:80` → `localhost:8000`. Static assets (`/static/`) should be served by nginx directly via `alias` so they never hit Python.

---

**User prompt:**
> does nginx really make that much of a difference for static files?

**AI response:**
> Yes — significantly. Flask serving a static file means a Python process wakes up, the request goes through Werkzeug's routing, finds the file on disk, reads it, and sends it back. nginx does the same thing in C with memory-mapped I/O and kernel-level sendfile. For a JS bundle or a CSS file that's requested on every page load, nginx is typically 10–50× faster and uses a fraction of the CPU. More importantly it frees your Gunicorn workers to handle actual application logic instead of sitting idle waiting for a browser to finish downloading `main.js`.

---

## 2026-04-20 — Dead Code & Code Quality Review (general)

**User prompt:**
> 请检查，并给出一些代码/架构优化
> *(Please review and suggest code/architecture optimizations)*

**AI response:**
> A few things stand out:
>
> **Dead files — just delete these:**
>
> | File | Why it's safe to remove |
> |------|------------------------|
> | `main_project/journey/api.py` (72 LOC) | Duplicate of `journey/routes.py` with broken imports, not registered anywhere |
> | `main_project/station/bikes_original.py` (82 LOC) | Blueprint commented out in `__init__.py:5`, never loaded |
>
> **Security — worth doing before going public:**
> - `var.env` has live DB password and API keys committed to the repo — add it to `.gitignore` and rotate the secrets
> - `app.py:22` has `debug=True` hardcoded — change to `os.getenv("FLASK_DEBUG", "false").lower() == "true"`
> - `app.py:12` CORS defaults to `"*"` — set an explicit `CORS_ORIGINS` env var instead
>
> **Code quality:**
> - `journey/routes.py` has `except Exception as e:` at 20+ places — this swallows real errors silently; catch `SQLAlchemyError` and `RequestException` specifically so bugs actually surface
> - `auth/auth.py:34-35` calls `load_dotenv()` again even though `config.py` already loads it — remove the duplicate call

---
