"""Hourly update of ohlc.json (daily XAU/USD candles).

- Days missing from the file are filled from Yahoo Finance gold futures (GC=F),
  shifted by the current spot-minus-futures gap so they line up with spot.
- Today's candle is then folded with the live spot price from gold-api.com.
- Days already in the file are never overwritten (except today)."""
import json, datetime, urllib.request
from zoneinfo import ZoneInfo

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 kbtc-gold-live"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()

data = {c["d"]: c for c in json.load(open("ohlc.json"))}
now = datetime.datetime.now(datetime.timezone.utc)
today = now.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

spot = None
try:
    spot = round(float(json.loads(get("https://api.gold-api.com/price/XAU"))["price"]), 2)
    print("spot:", spot)
except Exception as e:
    print("spot failed:", e)

try:
    y = json.loads(get("https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?interval=1d&range=1mo"))
    r = y["chart"]["result"][0]; q = r["indicators"]["quote"][0]
    fut_last = r["meta"].get("regularMarketPrice") or q["close"][-1]
    off = round(spot - fut_last, 2) if spot else 0.0
    print("futures last:", fut_last, "offset:", off)
    for i, ts in enumerate(r["timestamp"]):
        d = datetime.datetime.fromtimestamp(ts, ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        o, h, l, c = (q[k][i] for k in ("open", "high", "low", "close"))
        if None in (o, h, l, c) or (d in data and d != today):
            continue
        data[d] = {"d": d, "o": round(o + off, 2), "h": round(h + off, 2), "l": round(l + off, 2), "c": round(c + off, 2)}
        print("filled", d)
except Exception as e:
    print("futures failed:", e)

if spot and today in data:
    c = data[today]; c["h"] = max(c["h"], spot); c["l"] = min(c["l"], spot); c["c"] = spot

out = [data[k] for k in sorted(data)][-400:]
json.dump(out, open("ohlc.json", "w"), separators=(",", ":"))
print("candles:", len(out), out[-3:])
