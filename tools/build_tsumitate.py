"""
No!TRADE「積立のようす」の値動きデータ（tsumitate.json）を作るスクリプト。

・すべて円建て・配当込みの「期間の騰落率（％）」にそろえる
・古い年は1年ごと、最新の年は年初からの数か月をまとめた1期間
・出典と計算のしかたは SOURCES.md に書く
・数字はこのファイルに手で書き写したもの（自動でサイトから取ってこない）

使い方:  python3 tools/build_tsumitate.py  →  tsumitate.json を上書き
"""
import json
from pathlib import Path

UPDATED = "2026-09"  # どの月の末までのデータか

# ---------- 為替（1ドルあたりの円・年末） ----------
# FRED CCUSSP01JPA650N（OECD、年末スポット、1円あたりのドル）を 1/x にしたもの。1994〜2011年に使う
FRED_USD_PER_JPY = {
    1994: 0.0100260677762182, 1995: 0.0097247884858504, 1996: 0.0086206896551724,
    1997: 0.0076952674105425, 1998: 0.0086505190311419, 1999: 0.0097847358121331,
    2000: 0.0087032201914708, 2001: 0.0075872534142640, 2002: 0.0083402835696414,
    2003: 0.0093370681605976, 2004: 0.0096043027276220, 2005: 0.0084767313723828,
    2006: 0.0084068936527953, 2007: 0.0087719298245614, 2008: 0.0110192837465565,
    2009: 0.0108624809906583, 2010: 0.0122774708410068, 2011: 0.0128667009778693,
}

# MSCI World のネットリターン（％）。円建てとドル建ての差から、その年の為替の動きを出す（2012〜2025年）
# 円建て：MSCI Japan Index (JPY) ファクトシート（2026/9/30時点）の MSCI World 列
# ドル建て：MSCI ACWI Index (USD) ファクトシート（2026/9/30時点）の MSCI World 列
WORLD_JPY = {2012: 30.16, 2013: 53.99, 2014: 19.70, 2015: -0.54, 2016: 4.24, 2017: 18.22, 2018: -11.09,
             2019: 26.46, 2020: 10.11, 2021: 35.87, 2022: -6.21, 2023: 32.26, 2024: 32.29, 2025: 20.77}
WORLD_USD = {2012: 15.83, 2013: 26.68, 2014: 4.94, 2015: -0.87, 2016: 7.51, 2017: 22.40, 2018: -8.71,
             2019: 27.67, 2020: 15.90, 2021: 21.82, 2022: -18.14, 2023: 23.79, 2024: 18.67, 2025: 21.09}
# 2026年1〜9月（年初来）：同じファクトシートの YTD
WORLD_JPY_2026 = 12.03
WORLD_USD_2026 = 11.75


def fx_factor(year: int) -> float:
    """その年にドルを円に直したとき、何倍になったか（円安なら1より大きい）"""
    if year in WORLD_JPY:
        return (1 + WORLD_JPY[year] / 100) / (1 + WORLD_USD[year] / 100)
    return FRED_USD_PER_JPY[year - 1] / FRED_USD_PER_JPY[year]


FX_2026 = (1 + WORLD_JPY_2026 / 100) / (1 + WORLD_USD_2026 / 100)


def to_jpy(usd_pct: float, factor: float) -> float:
    return ((1 + usd_pct / 100) * factor - 1) * 100


def monthly_total(pcts):
    t = 1.0
    for p in pcts:
        t *= 1 + p / 100
    return (t - 1) * 100


# ---------- ドル建てのトータルリターン（％・配当込み） ----------
# S&P500：ChartRow（1994〜1995年は Damodaran、1996年以降は SPY の配当再投資）
SP500_USD = {1995: 37.2, 1996: 22.5, 1997: 33.5, 1998: 28.7, 1999: 20.4, 2000: -9.7, 2001: -11.8,
             2002: -21.6, 2003: 28.2, 2004: 10.7, 2005: 4.8, 2006: 15.8, 2007: 5.1, 2008: -36.8,
             2009: 26.4, 2010: 15.1, 2011: 1.9, 2012: 16.0, 2013: 32.3, 2014: 13.5, 2015: 1.2,
             2016: 12.0, 2017: 21.7, 2018: -4.6, 2019: 31.2, 2020: 18.3, 2021: 28.7, 2022: -18.2,
             2023: 26.2, 2024: 24.9, 2025: 17.7}
SP500_USD_2026_M = [1.5, -0.9, -4.9, 10.5, 5.3, -1.0, 0.1, 2.7, -0.3]  # SPY 2026年1〜9月

# 全米株式：ChartRow（VTI の配当再投資）
US_TOTAL_USD = {2002: -20.5, 2003: 30.7, 2004: 12.8, 2005: 6.3, 2006: 15.7, 2007: 5.4, 2008: -37.0,
                2009: 28.9, 2010: 17.4, 2011: 1.0, 2012: 16.5, 2013: 33.4, 2014: 12.5, 2015: 0.4,
                2016: 12.8, 2017: 21.2, 2018: -5.2, 2019: 30.7, 2020: 21.1, 2021: 25.7, 2022: -19.5,
                2023: 26.0, 2024: 23.8, 2025: 17.1}
US_TOTAL_USD_2026_M = [1.6, -0.5, -5.0, 10.4, 5.2, -0.4, -0.5, 2.7, -0.8]

# NASDAQ100：ChartRow（QQQ の配当再投資）
NASDAQ100_USD = {2000: -36.1, 2001: -33.3, 2002: -37.4, 2003: 49.6, 2004: 9.5, 2005: 1.2, 2006: 6.8,
                 2007: 18.7, 2008: -41.9, 2009: 53.8, 2010: 19.0, 2011: 2.5, 2012: 16.9, 2013: 36.6,
                 2014: 19.2, 2015: 9.4, 2016: 7.1, 2017: 32.7, 2018: -0.1, 2019: 39.0, 2020: 48.6,
                 2021: 27.4, 2022: -32.6, 2023: 54.9, 2024: 25.6, 2025: 20.8}
NASDAQ100_USD_2026_M = [1.2, -2.3, -4.8, 15.7, 10.6, -0.2, -6.5, 4.2, 3.3]

# FANG+：Total Real Returns（FNGS、MicroSectors FANG+ ETN。2019年11月からのデータのため2020年から）
FANG_USD = {2020: 101.99, 2021: 16.96, 2022: -40.32, 2023: 95.24, 2024: 51.99, 2025: 18.64}
FANG_USD_2026 = (82.55 / 68.05 - 1) * 100  # digrin の FNGS 月末価格（2025年12月 → 2026年9月）

# MSCI ACWI（ドル・ネット）：MSCI ACWI Index (USD) ファクトシート
ACWI_USD = {2012: 16.13, 2013: 22.80, 2014: 4.16, 2015: -2.36, 2016: 7.86, 2017: 23.97, 2018: -9.41, 2019: 26.60, 2020: 16.25, 2021: 18.54,
            2022: -18.36, 2023: 22.20, 2024: 17.49, 2025: 22.34}
ACWI_USD_2026 = 13.03

# ---------- 円建て（MSCI 公式） ----------
# MSCI ACWI Index 日本語ファクトシート（2016年4月版）の年間リターン（円建て）
ACWI_JPY_OLD = {2002: -26.64, 2003: 21.59, 2004: 10.68, 2005: 28.29, 2006: 22.69, 2007: 5.18,
                2008: -52.81, 2009: 39.06, 2010: -1.37, 2011: -11.65, 2012: 31.26, 2013: 50.05,
                2014: 19.44, 2015: -1.51}
WORLD_JPY_OLD = {2002: -27.15, 2003: 20.80, 2004: 10.19, 2005: 26.73, 2006: 21.80, 2007: 2.72,
                 2008: -51.58, 2009: 34.32, 2010: -2.13, 2011: -9.89}
# MSCI Japan：日本語ファクトシート（MSCI Japan HDY、2016年版）2002〜2011年 ＋ MSCI Japan (JPY) 2012〜2025年
JAPAN_JPY = {2002: -18.61, 2003: 22.96, 2004: 10.87, 2005: 44.70, 2006: 7.35, 2007: -10.13,
             2008: -42.48, 2009: 9.26, 2010: 0.71, 2011: -18.59, 2012: 21.57, 2013: 54.58,
             2014: 9.48, 2015: 9.93, 2016: -0.74, 2017: 19.75, 2018: -15.15, 2019: 18.48,
             2020: 8.76, 2021: 13.44, 2022: -4.49, 2023: 28.56, 2024: 20.74, 2025: 24.27}
JAPAN_JPY_2026 = 22.98

# 配当込みTOPIX（JPX 東証統計月報の年末値）。両端の年末値がそろう年は、MSCI Japan の代わりにこちらを使う
TOPIX_TR_YEAR_END = {2012: 859.80, 2013: 1302.29, 2014: 1407.51, 2023: 3977.63, 2024: 4791.22, 2025: 6010.98}

# 日経平均株価の年末終値（2024・2025年は報道で確認）。2026年9月30日終値は共同通信
NIKKEI_YEAR_END = {1994: 19723.06, 1995: 19868.15, 1996: 19361.35, 1997: 15258.74, 1998: 13842.17,
                   1999: 18934.34, 2000: 13785.69, 2001: 10542.62, 2002: 8578.95, 2003: 10676.64,
                   2004: 11488.76, 2005: 16111.43, 2006: 17225.83, 2007: 15307.78, 2008: 8859.56,
                   2009: 10546.44, 2010: 10228.92, 2011: 8455.35, 2012: 10395.18, 2013: 16291.31,
                   2014: 17450.77, 2015: 19033.71, 2016: 19114.37, 2017: 22764.94, 2018: 20014.77,
                   2019: 23656.62, 2020: 27444.17, 2021: 28791.71, 2022: 26094.50, 2023: 33464.17,
                   2024: 39894.54, 2025: 50339.48}
NIKKEI_2026_09 = 66753.72


# ---------- 現実に近づけるための補正 ----------
# 2002〜2011年の MSCI の古い円建て資料はグロス（配当にかかる税を引く前）のため、ネットに直す。
# 補正幅は、MSCI ACWI（ドル・ネット）の設定来年率 7.41%（2000/12/29〜2026/9/30）と為替から逆算した
# 2002年1月〜2026年9月の伸びに、データの積み上げが一致するように決めた（1年あたり約0.46%）
GROSS_TO_NET_WORLD = 0.46
GROSS_TO_NET_JAPAN = 0.30  # 日本株は配当利回りが低めのため、少し小さく

# 信託報酬など、投資信託を持っているあいだにかかる費用（％・年）。
# 指数そのものの数字には費用が入っていないため、代表的な低コストの投資信託の水準を引く。
# ETF の数字を使っているカテゴリは ETF の経費がすでに入っているので、その差だけ引く
FEE = {
    "ALL_WORLD": 0.058,    # eMAXIS Slim 全世界株式（オール・カントリー）0.05775%
    "WORLD_EX_JP": 0.058,  # eMAXIS Slim 全世界株式（除く日本）0.05775%
    "DEVELOPED": 0.099,    # eMAXIS Slim 先進国株式インデックス 0.09889%
    "SP500": 0.0,          # SPY（0.0945%）≒ eMAXIS Slim 米国株式（S&P500）0.0814%
    "US_TOTAL": 0.13,      # 楽天・全米株式 0.162% − VTI 0.03%
    "NASDAQ100": 0.0,      # QQQ（0.20%）≒ 国内のNASDAQ100インデックスファンド
    "FANG_PLUS": 0.20,     # iFreeNEXT FANG+ 0.7755% − FNGS 0.58%
    "TOPIX": 0.143,        # eMAXIS Slim 国内株式（TOPIX）0.143%
    "NIKKEI225": 0.143,    # eMAXIS Slim 国内株式（日経平均）0.143%
}


def with_fee(periods, key):
    """期間の騰落率から、その期間ぶんの費用を引く（複利で）"""
    fee = FEE[key] / 100
    out = []
    for p in periods:
        y0, m0 = map(int, p["from"].split("-"))
        y1, m1 = map(int, p["to"].split("-"))
        months = (y1 - y0) * 12 + (m1 - m0) + 1
        r = ((1 + p["r"] / 100) * (1 - fee) ** (months / 12) - 1) * 100
        out.append({**p, "r": round(r, 2)})
    return out


def gross_to_net(d, years, pct):
    return {y: (((1 + v / 100) * (1 - pct / 100) - 1) * 100 if y in years else v) for y, v in d.items()}


def nikkei_dividend(year: int) -> float:
    """日経平均の配当利回りの目安（％・年）。株価の動きに足して、配当込みの概算にする"""
    if year <= 2003:
        return 0.8
    if year <= 2008:
        return 1.2
    if year <= 2015:
        return 1.7
    return 1.8


def japan_weight(year: int, in_acwi: bool) -> float:
    """MSCI World / ACWI の中の日本の比率の目安（年初）。日本を除く指数の概算に使う"""
    w = 0.095 if year <= 2006 else 0.09 if year <= 2011 else 0.08 if year <= 2019 else 0.06
    return w * 0.88 if in_acwi else w


def ex_japan(total_pct: float, japan_pct: float, w: float) -> float:
    return (total_pct - w * japan_pct) / (1 - w)


def yearly(d):
    return [{"from": f"{y}-01", "to": f"{y}-12", "r": round(v, 2)} for y, v in sorted(d.items())]


def ytd(v):
    return [{"from": "2026-01", "to": UPDATED, "r": round(v, 2)}]


def build():
    old = range(2002, 2012)
    acwi = gross_to_net({y: v for y, v in ACWI_JPY_OLD.items() if y in old}, old, GROSS_TO_NET_WORLD)
    for y, v in ACWI_USD.items():
        acwi[y] = to_jpy(v, fx_factor(y))
    acwi_2026 = to_jpy(ACWI_USD_2026, FX_2026)

    world = gross_to_net(WORLD_JPY_OLD, old, GROSS_TO_NET_WORLD)
    world.update(WORLD_JPY)

    japan = gross_to_net(JAPAN_JPY, old, GROSS_TO_NET_JAPAN)
    topix = dict(japan)
    for y in TOPIX_TR_YEAR_END:
        if y - 1 in TOPIX_TR_YEAR_END:
            topix[y] = (TOPIX_TR_YEAR_END[y] / TOPIX_TR_YEAR_END[y - 1] - 1) * 100

    nikkei = {}
    for y in range(1995, 2026):
        price = NIKKEI_YEAR_END[y] / NIKKEI_YEAR_END[y - 1]
        nikkei[y] = (price * (1 + nikkei_dividend(y) / 100) - 1) * 100
    nikkei_2026 = (NIKKEI_2026_09 / NIKKEI_YEAR_END[2025] * (1 + nikkei_dividend(2026) * 0.75 / 100) - 1) * 100

    cats = {
        "ALL_WORLD": yearly(acwi) + ytd(acwi_2026),
        "WORLD_EX_JP": yearly({y: ex_japan(v, japan[y], japan_weight(y, True)) for y, v in acwi.items()})
        + ytd(ex_japan(acwi_2026, JAPAN_JPY_2026, japan_weight(2026, True))),
        "DEVELOPED": yearly({y: ex_japan(v, japan[y], japan_weight(y, False)) for y, v in world.items()})
        + ytd(ex_japan(WORLD_JPY_2026, JAPAN_JPY_2026, japan_weight(2026, False))),
        "SP500": yearly({y: to_jpy(v, fx_factor(y)) for y, v in SP500_USD.items()})
        + ytd(to_jpy(monthly_total(SP500_USD_2026_M), FX_2026)),
        "US_TOTAL": yearly({y: to_jpy(v, fx_factor(y)) for y, v in US_TOTAL_USD.items()})
        + ytd(to_jpy(monthly_total(US_TOTAL_USD_2026_M), FX_2026)),
        "NASDAQ100": yearly({y: to_jpy(v, fx_factor(y)) for y, v in NASDAQ100_USD.items()})
        + ytd(to_jpy(monthly_total(NASDAQ100_USD_2026_M), FX_2026)),
        "FANG_PLUS": yearly({y: to_jpy(v, fx_factor(y)) for y, v in FANG_USD.items()})
        + ytd(to_jpy(FANG_USD_2026, FX_2026)),
        "TOPIX": yearly(topix) + ytd(JAPAN_JPY_2026),
        "NIKKEI225": yearly(nikkei) + ytd(nikkei_2026),
    }
    cats = {k: with_fee(v, k) for k, v in cats.items()}
    return {
        "updated": UPDATED,
        "sample": False,
        "note": "円建て・配当込み・信託報酬の目安を差し引いた騰落率（％）。r は期間の騰落率。出典と計算方法は SOURCES.md",
        "categories": cats,
    }


if __name__ == "__main__":
    data = build()
    out = Path(__file__).resolve().parent.parent / "tsumitate.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for k, v in data["categories"].items():
        print(f"{k:12s} {v[0]['from']}〜 {len(v)}期間  直近: {v[-2]['from'][:4]} {v[-2]['r']:+.1f}%  2026年1〜9月 {v[-1]['r']:+.1f}%")
