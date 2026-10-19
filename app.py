# app.py
# runtime: python 3.10+
# deps: flask, requests
# deploy: render.com / railway.app / pythonanywhere free tier

from flask import Flask, request, render_template_string
import requests
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-prod")

BASE = "https://webapi.depop.com"

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Depop Clone + Boost</title>
<style>
  body { font-family: system-ui, sans-serif; background:#0f0f0f; color:#eee; max-width:520px; margin:40px auto; padding:0 16px; }
  h1 { font-size:1.4rem; margin-bottom:8px; }
  label { display:block; margin:14px 0 4px; font-size:0.9rem; color:#aaa; }
  input { width:100%; padding:10px; border-radius:8px; border:1px solid #333; background:#1a1a1a; color:#fff; box-sizing:border-box; }
  button { width:100%; margin-top:20px; padding:12px; border:none; border-radius:8px; background:#ff2e63; color:#fff; font-weight:700; cursor:pointer; }
  button:hover { background:#e02655; }
  .msg { margin-top:16px; padding:12px; border-radius:8px; background:#1e1e1e; white-space:pre-wrap; font-size:0.85rem; }
  .ok { border-left:4px solid #00c853; }
  .err { border-left:4px solid #ff1744; }
  .note { font-size:0.75rem; color:#666; margin-top:24px; }
</style>
</head>
<body>
  <h1>Depop Clone + Boost</h1>
  <p style="color:#888;font-size:0.85rem;">Paste tokens and hit the button. Exact copy goes into your account + tries boost.</p>

  <form method="POST">
    <label>Account Token (Bearer)</label>
    <input type="text" name="account_token" placeholder="eyJhbGciOiJIUzI1NiIs..." required>

    <label>Product Token / ID (listing you want to copy)</label>
    <input type="text" name="product_token" placeholder="abc123-cool-shirt" required>

    <label><input type="checkbox" name="do_boost" checked> Try Boost</label>

    <button type="submit">Clone + Boost</button>
  </form>

  {% if result %}
  <div class="msg {{ 'ok' if result.ok else 'err' }}">{{ result.text }}</div>
  {% endif %}

  <p class="note">Tokens die fast. Never share your account token. Free host: render / railway / pythonanywhere.</p>
</body>
</html>
"""

def get_listing(token: str, product_id: str):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Depop/3.0 (iPhone; iOS 17.0; Scale/3.00)",
    }
    url = f"{BASE}/api/v1/products/{product_id}/"
    return requests.get(url, headers=headers, timeout=25)

def build_payload(src: dict) -> dict:
    pictures = []
    for p in src.get("pictures", []) or src.get("images", []):
        if isinstance(p, dict):
            pictures.append({
                "id": p.get("id"),
                "url": p.get("url") or (p.get("formats", {}) or {}).get("P0", {}).get("url"),
            })
        else:
            pictures.append(p)

    payload = {
        "description": src.get("description", ""),
        "brand": src.get("brand"),
        "category": src.get("category"),
        "condition": src.get("condition"),
        "gender": src.get("gender"),
        "colour": src.get("colour") or src.get("colors"),
        "size": src.get("size") or src.get("sizes"),
        "price_amount": src.get("price_amount") or (src.get("price") or {}).get("price_amount"),
        "price_currency": src.get("price_currency") or (src.get("price") or {}).get("currency_name", "GBP"),
        "national_shipping_cost": src.get("national_shipping_cost") or (src.get("shipping") or {}).get("national"),
        "international_shipping_cost": src.get("international_shipping_cost"),
        "address": src.get("address") or src.get("shipping_address"),
        "pictures": pictures,
        "attributes": src.get("attributes", {}),
        "is_kids": src.get("is_kids", False),
        "quantity": src.get("quantity", 1),
        "status": "S",
    }
    return {k: v for k, v in payload.items() if v is not None}

def create_listing(token: str, payload: dict):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Depop/3.0 (iPhone; iOS 17.0; Scale/3.00)",
    }
    url = f"{BASE}/api/v1/products/"
    return requests.post(url, headers=headers, json=payload, timeout=25)

def boost_listing(token: str, product_id: str) -> bool:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Depop/3.0 (iPhone; iOS 17.0; Scale/3.00)",
    }
    endpoints = [
        f"{BASE}/api/v1/products/{product_id}/boost/",
        f"{BASE}/api/v2/products/{product_id}/boost/",
        f"{BASE}/api/v1/boosts/",
    ]
    body = {"product_id": product_id}
    for url in endpoints:
        r = requests.post(url, headers=headers, json=body, timeout=15)
        if r.status_code in (200, 201, 204):
            return True
    return False

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        token = request.form.get("account_token", "").strip()
        product = request.form.get("product_token", "").strip()
        do_boost = bool(request.form.get("do_boost"))

        if not token or not product:
            result = {"ok": False, "text": "Account token and product token are required"}
        else:
            lines = []
            try:
                r = get_listing(token, product)
                if r.status_code != 200:
                    result = {"ok": False, "text": f"Failed to fetch listing: {r.status_code}\n{r.text[:300]}"}
                else:
                    src = r.json()
                    lines.append(f"[1] Got source listing — desc len={len(src.get('description',''))}")
                    payload = build_payload(src)
                    lines.append("[2] Built payload")
                    cr = create_listing(token, payload)
                    if cr.status_code not in (200, 201):
                        result = {"ok": False, "text": f"Create failed: {cr.status_code}\n{cr.text[:400]}"}
                    else:
                        new = cr.json()
                        new_id = str(new.get("id") or new.get("product_id") or "")
                        lines.append(f"[3] New listing created — id={new_id}")
                        boosted = False
                        if do_boost and new_id:
                            boosted = boost_listing(token, new_id)
                            lines.append(f"[4] Boost = {'success' if boosted else 'failed (listing still live)'}")
                        lines.append("[done] Check your active listings")
                        result = {"ok": True, "text": "\n".join(lines)}
            except Exception as e:
                result = {"ok": False, "text": f"Error: {str(e)}"}

    return render_template_string(HTML, result=result)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)