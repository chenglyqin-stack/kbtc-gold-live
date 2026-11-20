"""Update ohlc.json with daily XAU/USD candles.
1) Try stooq daily CSV (spot XAUUSD) for full candles.
2) Always fold the current gold-api.com spot price into today's candle,
   so the latest day stays current even if stooq is unavailable."""
import csv, io, json, datetime, urllib.request

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 kbtc-gold-live"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()

data = {c["d"]: c for c in json.load(open("ohlc.json"))}

try:
    raw = get("https://stooq.com/q/d/l/?s=xauusd&i=d")
    print("stooq head:", raw[:160].replace("\n", " | "))
    rows = list(csv.DictReader(io.StringIO(raw)))
    n = 0
    for r in rows[-260:]:
        d = r.get("Date")
        if not d or not r.get("Close"):
            continue
        data[d] = {"d": d, "o": round(float(r["Open"]), 2), "h": round(float(r["High"]), 2),
                   "l": round(float(r["Low"]), 2), "c": round(float(r["Close"]), 2)}
        n += 1
    print("stooq rows:", n)
except Exception as e:
    print("stooq failed:", e)

if not any(k >= "2026-11-18" and data[k]["o"] != data[k]["c"] for k in data):
    for sym in ("XAUUSD%3DX", "GC%3DF"):
        try:
            y = json.loads(get("https://query1.finance.yahoo.com/v8/finance/chart/" + sym + "?interval=1d&range=1mo"))
            r = y["chart"]["result"][0]; q = r["indicators"]["quote"][0]
            print("yahoo", sym, "last close", q["close"][-1], "days", len(r["timestamp"]))
        except Exception as e:
            print("yahoo", sym, "failed:", e)

try:
    j = json.loads(get("https://api.gold-api.com/price/XAU"))
    p = round(float(j["price"]), 2)
    day = (datetime.datetime.now(datetime.timezone.utc)).strftime("%Y-%m-%d")
    if datetime.datetime.now(datetime.timezone.utc).weekday() < 5 or day in data:
        c = data.get(day)
        if c:
            c["h"] = max(c["h"], p); c["l"] = min(c["l"], p); c["c"] = p
        else:
            data[day] = {"d": day, "o": p, "h": p, "l": p, "c": p}
    print("spot:", p, day)
except Exception as e:
    print("spot failed:", e)

out = [data[k] for k in sorted(data)][-400:]
json.dump(out, open("ohlc.json", "w"), separators=(",", ":"))
print("candles:", len(out), out[-1])
