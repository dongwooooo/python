# app1.py
from __future__ import annotations
from pathlib import Path
from functools import lru_cache
import math
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse

app = FastAPI(title="AdventureWorks 계산 리포트", version="1.0.0")

# ====== 엑셀 경로 자동 탐색 ======
BASE = Path(__file__).parent
CANDIDATES = [
    BASE / "data" / "AdventureWorks Sales.xlsx",
    BASE / "AdventureWorks Sales.xlsx",
]
EXCEL_PATH = next((p for p in CANDIDATES if p.exists()), None)

if EXCEL_PATH is None:
    raise FileNotFoundError(
        "AdventureWorks Sales.xlsx 파일을 찾을 수 없습니다.\n"
        + "\n".join(f"- {c}" for c in CANDIDATES)
    )

# ====== 데이터 로드 (캐시) ======
@lru_cache(maxsize=1)
def load_data():
    xls = pd.ExcelFile(EXCEL_PATH)
    sales = pd.read_excel(xls, sheet_name="Sales_data")
    date  = pd.read_excel(xls, sheet_name="Date_data")[["DateKey", "Date"]]
    cust  = pd.read_excel(xls, sheet_name="Customer_data")[
        ["CustomerKey", "Customer ID", "Customer", "City", "Country-Region"]
    ]
    prod  = pd.read_excel(xls, sheet_name="Product_data")[
        ["ProductKey", "Product", "Category", "Subcategory"]
    ]

    sales = sales.merge(date, left_on="OrderDateKey", right_on="DateKey", how="left")
    sales["Date"] = pd.to_datetime(sales["Date"])
    return sales, cust, prod

SALES, CUSTOMERS, PRODUCTS = load_data()

# ====== 예측/지표 유틸 ======
def _orders_of_customer(df_sales, cid: int):
    return df_sales[df_sales["CustomerKey"] == cid].sort_values("Date")

def _next_purchase(df_sales, cid: int):
    df = _orders_of_customer(df_sales, cid)
    if df.empty or df["Date"].nunique() < 2:
        # 글로벌 중앙 간격 사용
        gaps_by_cust = df_sales.groupby("CustomerKey")["Date"].apply(
            lambda s: s.sort_values().diff().dt.days.median()
        )
        global_median = int(gaps_by_cust.dropna().median()) if gaps_by_cust.notna().any() else 30
        return None, global_median, None  # last, median_gap, next
    gaps = df["Date"].diff().dt.days.dropna()
    median_gap = int(max(1, round(gaps.median())))
    last_date = df["Date"].max().date()
    next_date = (pd.Timestamp(last_date) + pd.Timedelta(days=median_gap)).date()
    return last_date, median_gap, next_date

def _purchase_prob_30d(df_sales, cid: int, days: int = 30):
    df = _orders_of_customer(df_sales, cid)
    monthly_counts = df_sales.groupby(
        ["CustomerKey", df_sales["Date"].dt.to_period("M")]
    ).size().groupby("CustomerKey").mean()
    baseline = float(min(0.95, (monthly_counts.mean() or 0) / 4)) if len(monthly_counts) else 0.25
    if df.empty:
        return round(baseline, 3)
    gaps = df["Date"].diff().dt.days.dropna()
    med = gaps.median() if not gaps.empty else np.nan
    if np.isnan(med):
        med = df_sales.groupby("CustomerKey")["Date"].apply(
            lambda s: s.sort_values().diff().dt.days.median()
        ).dropna().median()
    time_since = (df_sales["Date"].max() - df["Date"].max()).days
    x = (days - (med - time_since)) / max(7, med)
    p = 1.0 / (1.0 + math.exp(-x))
    prob = 0.7 * p + 0.3 * baseline
    return round(float(prob), 3)

def _clv_naive(df_sales, cid: int):
    df = _orders_of_customer(df_sales, cid)
    hist = df["Sales Amount"].sum() if not df.empty else 0.0
    aov = (df["Sales Amount"].mean() if not df.empty else df_sales["Sales Amount"].mean()) or 0.0
    n_orders = df["SalesOrderLineKey"].nunique()
    recent_days = (df_sales["Date"].max() - df["Date"].max()).days if not df.empty else 365
    if n_orders >= 10 and recent_days <= 60:
        expected = 5
    elif n_orders >= 5 and recent_days <= 120:
        expected = 3
    else:
        expected = 1
    clv = hist + expected * aov
    return round(float(hist), 2), round(float(aov), 2), int(expected), round(float(clv), 2)

def _churn(df_sales, cid: int):
    df = _orders_of_customer(df_sales, cid)
    if df.empty:
        return 0.85, "high"
    time_since = (df_sales["Date"].max() - df["Date"].max()).days
    freq = df["SalesOrderLineKey"].nunique()
    ts_rank = min(1.0, time_since / 180)
    freq_rank = 1.0 - min(1.0, freq / 10.0)
    score = float(np.clip(0.6 * ts_rank + 0.4 * freq_rank, 0, 1))
    label = "high" if score >= 0.66 else ("medium" if score >= 0.33 else "low")
    return round(score, 3), label

def _top_rec(df_sales, df_prod, cid: int):
    merged = df_sales.merge(df_prod, on="ProductKey", how="left")
    df = _orders_of_customer(df_sales, cid)
    if not df.empty:
        mine = df.merge(df_prod, on="ProductKey", how="left")
        if mine["Subcategory"].notna().any():
            fav = mine["Subcategory"].value_counts().idxmax()
            cand = merged[merged["Subcategory"] == fav]
        else:
            cand = merged
    else:
        cand = merged
    top = (
        cand.groupby(["ProductKey", "Product"])["Order Quantity"]
        .sum().sort_values(ascending=False).head(1)
    )
    if len(top) == 0:
        return None
    (pk, name), _ = top.index[0], top.iloc[0]
    return name

# ====== 홈: 계산 결과 표 렌더링 ======
@app.get("/", response_class=HTMLResponse)
def home():
    try:
        # --- 요약 지표 ---
        total_rows = len(SALES)
        unique_customers = SALES["CustomerKey"].nunique()
        unique_products = SALES["ProductKey"].nunique()
        date_min = SALES["Date"].min().date()
        date_max = SALES["Date"].max().date()
        total_sales_amount = float(SALES["Sales Amount"].sum())

        summary_df = pd.DataFrame({
            "지표": ["총 주문 행 수","고객 수","상품 수","기간(시작)","기간(종료)","총 매출액"],
            "값":  [f"{total_rows:,}", f"{unique_customers:,}", f"{unique_products:,}",
                    str(date_min), str(date_max), f"{total_sales_amount:,.2f}"]
        })

        # --- 상위 고객 30명 기준 예측 테이블 ---
        cust_sales = SALES.groupby("CustomerKey")["Sales Amount"].sum().sort_values(ascending=False)
        top_customers = cust_sales.head(30).index.tolist()

        rows = []
        for cid in top_customers:
            last_date, median_gap, next_date = _next_purchase(SALES, cid)
            prob30 = _purchase_prob_30d(SALES, cid, days=30)
            hist, aov, expected_orders, clv = _clv_naive(SALES, cid)
            score, risk = _churn(SALES, cid)
            rec = _top_rec(SALES, PRODUCTS, cid)
            crow = CUSTOMERS[CUSTOMERS["CustomerKey"] == cid]
            name = None if crow.empty else crow.iloc[0]["Customer"]
            city = None if crow.empty else crow.iloc[0]["City"]
            country = None if crow.empty else crow.iloc[0]["Country-Region"]
            rows.append({
                "CustomerKey": cid,
                "Customer": name, "City": city, "Country": country,
                "Last Purchase": None if last_date is None else str(last_date),
                "Median Gap (days)": None if median_gap is None else int(median_gap),
                "Next Expected Purchase": None if next_date is None else str(next_date),
                "Prob. Purchase (30d)": prob30,
                "Historical Sales": hist, "AOV": aov,
                "Expected Future Orders": expected_orders, "Naive CLV": clv,
                "Churn Score": score, "Churn Risk": risk, "Top Recommendation": rec,
            })
        pred_df = pd.DataFrame(rows)

        # 표 렌더링 (pandas.to_html)
        summary_html = summary_df.to_html(index=False, classes="table table-sm", border=0)
        pred_html    = pred_df.to_html(index=False, classes="table table-sm", border=0)

        # HTML 스켈레톤 (f-string 아님; placeholder 치환)
        html = """
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>AdventureWorks 계산 리포트</title>
<style>
  :root { --bg:#0b0f19; --card:#111827; --line:#1f2937; --text:#e5e7eb; --muted:#9ca3af; }
  *{box-sizing:border-box;} body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;}
  .wrap{max-width:1200px;margin:28px auto;padding:0 16px;}
  h1{margin:0 0 12px;font-size:28px;}
  .muted{color:var(--muted);}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin-top:14px;}
  table{width:100%;border-collapse:collapse;font-size:14px;}
  th,td{padding:8px 10px;border-bottom:1px solid #1f2937;vertical-align:top;}
  th{text-align:left;color:#cbd5e1;}
  code{color:#c7d2fe;}
  .grid{display:grid;grid-template-columns:1fr;gap:16px;}
  .small{font-size:12px;}
</style>
</head>
<body>
  <div class="wrap">
    <h1>AdventureWorks 계산 리포트</h1>
    <div class="muted small">엑셀: <code>%%EXCEL%%</code></div>

    <div class="card">
      <h2 style="margin:0 0 12px;">요약 지표</h2>
      %%SUMMARY%%
    </div>

    <div class="card">
      <h2 style="margin:0 0 12px;">고객 예측 (상위 30명 · 매출 기준)</h2>
      <div class="muted small">다음 구매 시기/구매 확률(30일)/CLV/이탈 위험/추천 상품 포함</div>
      <div style="overflow:auto; max-height:70vh;">%%PRED%%</div>
    </div>
  </div>
</body>
</html>
"""
        html = html.replace("%%EXCEL%%", EXCEL_PATH.as_posix())
        html = html.replace("%%SUMMARY%%", summary_html)
        html = html.replace("%%PRED%%", pred_html)
        return HTMLResponse(html)
    except Exception as e:
        return PlainTextResponse("오류: " + repr(e), status_code=500)

@app.get("/health")
def health():
    return {"status": "ok"}
