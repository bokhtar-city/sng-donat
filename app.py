from flask import Flask, request, redirect, render_template_string, jsonify, session
import sqlite3
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import quote
import json
import re

app = Flask(__name__)

app.secret_key = "SNG_DONAT_SECRET_2026"

DB = "sng_shop.db"

PAYMENT_NUMBER = "+992 93 418 42 18"

ADMIN_USER = "admin"
ADMIN_PASSWORD = "123456"


# =========================================================
# PRODUCTS
# =========================================================

PRODUCTS = {

    "sng": [
        ("100 💎", "100", 9),
        ("310 💎", "310", 30),
        ("520 💎", "520", 46),
        ("1060 💎", "1060", 92),
        ("2180 💎", "2180", 175),
        ("5600 💎", "5600", 440),

        ("Еженедельный Lite", "weekly_lite", 5),
        ("Ваучер на неделю", "week_voucher", 17),
        ("Ваучер на месяц", "month_voucher", 70),

        ("EVO Access 3 дня", "evo_3", 5),
        ("EVO Access 7 дней", "evo_7", 9),
        ("EVO Access 30 дней", "evo_30", 27),

        ("Набор новичка", "newbie", 3),

        ("Level Up Package 6", "level_6", 5),
        ("Level Up Package 10", "level_10", 7),
        ("Level Up Package 15", "level_15", 7),
        ("Level Up Package 20", "level_20", 7),
        ("Level Up Package 25", "level_25", 7),
        ("Level Up Package 30", "level_30", 10),
    ],

    "id": [
        ("5 💎", "5", 1),
        ("10 💎", "10", 2),
        ("12 💎", "12", 2),
        ("20 💎", "20", 3),
        ("25 💎", "25", 4),
        ("30 💎", "30", 4),
        ("50 💎", "50", 5),
        ("55 💎", "55", 6),
        ("70 💎", "70", 7),
        ("80 💎", "80", 8),
        ("100 💎", "100", 11),
        ("120 💎", "120", 13),
        ("130 💎", "130", 14),
        ("140 💎", "140", 13),
        ("145 💎", "145", 15),
        ("150 💎", "150", 15),
        ("190 💎", "190", 19),
        ("200 💎", "200", 20),
        ("210 💎", "210", 20),
        ("280 💎", "280", 27),
        ("355 💎", "355", 32),
        ("420 💎", "420", 40),
        ("500 💎", "500", 48),
        ("510 💎", "510", 49),
        ("565 💎", "565", 54),
        ("635 💎", "635", 61),
        ("720 💎", "720", 56),
        ("800 💎", "800", 76),
        ("860 💎", "860", 81),
        ("930 💎", "930", 90),
        ("1000 💎", "1000", 95),
        ("1050 💎", "1050", 100),
        ("1075 💎", "1075", 101),
        ("1080 💎", "1080", 102),
        ("1450 💎", "1450", 129),
        ("2180 💎", "2180", 194),
        ("2200 💎", "2200", 208),
        ("3600 💎", "3600", 322),
        ("7290 💎", "7290", 621),

        ("Level Up Pass 6", "level_6", 4),
        ("Level Up Pass 10", "level_10", 6),
        ("Level Up Pass 15", "level_15", 6),
        ("Level Up Pass 20", "level_20", 6),
        ("Level Up Pass 25", "level_25", 6),
        ("Level Up Pass 30", "level_30", 10),

        ("Weekly Membership", "weekly", 19),
        ("Monthly Membership", "monthly", 56),
    ]
}


# =========================================================
# DATABASE
# =========================================================

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL,
            phone TEXT NOT NULL,
            product TEXT NOT NULL,
            diamonds TEXT NOT NULL,
            price INTEGER NOT NULL,
            server TEXT NOT NULL,
            nickname TEXT,
            status TEXT DEFAULT 'Ожидает оплаты',
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            balance INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS balance_topups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT DEFAULT 'Ожидает проверки',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================================================
# HELPERS
# =========================================================

def money(value):
    return f"{int(value)} сом"


def clean_uid(uid):
    return re.sub(r"\D", "", uid or "")


def get_balance(phone):

    if not phone:
        return 0

    conn = db()

    row = conn.execute(
        "SELECT balance FROM wallets WHERE phone=?",
        (phone,)
    ).fetchone()

    conn.close()

    if row:
        return int(row["balance"])

    return 0


def get_product(server, product_id):

    for name, pid, price in PRODUCTS.get(server, []):

        if pid == product_id:

            return {
                "name": name,
                "id": pid,
                "price": price
            }

    return None


# =========================================================
# FREE FIRE UID API
# =========================================================

def parse_nickname(data):

    if not isinstance(data, dict):
        return None

    possible = []

    basic = data.get("basicInfo")

    if isinstance(basic, dict):
        possible.append(basic.get("nickname"))

    basic_lower = data.get("basicinfo")

    if isinstance(basic_lower, dict):
        possible.append(basic_lower.get("nickname"))

    result = data.get("result")

    if isinstance(result, dict):

        basic2 = result.get("basicInfo")

        if isinstance(basic2, dict):
            possible.append(basic2.get("nickname"))

        basic3 = result.get("basicinfo")

        if isinstance(basic3, dict):
            possible.append(basic3.get("nickname"))

        possible.append(result.get("nickname"))

    possible.append(data.get("nickname"))

    for value in possible:

        if isinstance(value, str):

            value = value.strip()

            if value:
                return value

    return None


def request_json(url):

    try:

        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urlopen(req, timeout=20) as response:

            raw = response.read().decode(
                "utf-8",
                errors="ignore"
            )

            return json.loads(raw)

    except Exception:
        return None


def check_free_fire_uid(uid, server):

    uid = clean_uid(uid)

    if not uid:
        return {
            "ok": False,
            "nickname": None
        }

    region = "CIS" if server == "sng" else "ID"

    urls = [

        (
            "https://free-ff-api-src-5plp.onrender.com"
            "/api/v1/account"
            f"?region={region}&uid={quote(uid)}"
        ),

        (
            "https://freefireapis.lat/info-player"
            f"?uid={quote(uid)}&region={region}"
        ),

        (
            "https://freefireinfo-zy9l.onrender.com"
            "/api/v1/player-profile"
            f"?uid={quote(uid)}&server={region}"
        )
    ]

    for url in urls:

        data = request_json(url)

        nickname = parse_nickname(data)

        if nickname:
            return {
                "ok": True,
                "nickname": nickname
            }

    return {
        "ok": False,
        "nickname": None
    }


# =========================================================
# BASE HTML + DESIGN
# =========================================================

BASE_HTML = """
<!doctype html>

<html lang="tg">

<head>

<meta charset="utf-8">

<meta name="viewport"
      content="width=device-width,
               initial-scale=1,
               maximum-scale=1,
               user-scalable=no">

<title>SNG DONAT💎</title>

<style>

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    padding: 0;
    min-height: 100%;
}

body {

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;

    color: #ffffff;

    background:
        radial-gradient(
            circle at 20% 0%,
            rgba(72, 61, 139, .28),
            transparent 32%
        ),
        radial-gradient(
            circle at 100% 20%,
            rgba(0, 140, 255, .20),
            transparent 30%
        ),
        #050711;

    padding-bottom: 90px;
}

a {
    color: inherit;
    text-decoration: none;
}

.container {

    width: 100%;
    max-width: 620px;

    margin: 0 auto;

    padding: 18px 14px 30px;
}

.topbar {

    display: flex;
    align-items: center;
    justify-content: space-between;

    margin-bottom: 18px;
}

.logo {

    font-size: 22px;
    font-weight: 900;

    letter-spacing: -.5px;

    text-shadow:
        0 0 18px rgba(120, 100, 255, .55);
}

.balance-mini {

    padding: 9px 13px;

    border-radius: 18px;

    background:
        rgba(255,255,255,.07);

    border:
        1px solid rgba(255,255,255,.12);

    backdrop-filter: blur(15px);

    font-size: 13px;
}

.hero {

    position: relative;

    overflow: hidden;

    min-height: 235px;

    padding: 25px;

    border-radius: 28px;

    background:
        linear-gradient(
            135deg,
            rgba(80,70,180,.28),
            rgba(0,130,255,.12)
        );

    border:
        1px solid rgba(255,255,255,.12);

    box-shadow:
        0 18px 50px rgba(0,0,0,.35);
}

.hero:after {

    content: "💎";

    position: absolute;

    right: -5px;
    bottom: -28px;

    font-size: 150px;

    opacity: .17;

    transform: rotate(-12deg);
}

.hero-text {
    position: relative;
    z-index: 2;
}

.badge {

    display: inline-block;

    padding: 6px 10px;

    border-radius: 999px;

    background:
        rgba(255,255,255,.08);

    border:
        1px solid rgba(255,255,255,.12);

    color: #b9c7ff;

    font-size: 11px;
    font-weight: 800;

    letter-spacing: .7px;

    margin-bottom: 10px;
}

h1 {

    margin: 0 0 8px;

    font-size: 30px;

    line-height: 1.1;
}

h2,
h3,
p {
    margin-top: 0;
}

.hero p {

    color: #aeb5ca;

    margin-bottom: 20px;
}

.btn {

    display: inline-flex;

    align-items: center;
    justify-content: center;

    min-height: 46px;

    padding: 11px 17px;

    border-radius: 15px;

    border: 1px solid rgba(255,255,255,.13);

    color: #ffffff;

    font-weight: 800;

    cursor: pointer;

    background:
        rgba(255,255,255,.07);

    backdrop-filter: blur(16px);

    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.06),
        0 8px 25px rgba(0,0,0,.18);
}

.btn:active {
    transform: scale(.98);
}

.btn.primary {

    background:
        linear-gradient(
            135deg,
            rgba(91,77,255,.72),
            rgba(0,145,255,.62)
        );

    border-color:
        rgba(160,180,255,.28);

    box-shadow:
        0 10px 30px rgba(45,80,255,.22);
}

.btn.glass {
    background:
        rgba(255,255,255,.06);
}

.full {
    width: 100%;
}

.section-title {

    display: flex;

    align-items: center;
    justify-content: space-between;

    margin: 25px 2px 12px;
}

.section-title h2 {
    margin: 0;
    font-size: 19px;
}

.section-title span {
    color: #858da5;
    font-size: 12px;
}

.server-grid {

    display: grid;

    grid-template-columns:
        repeat(2, 1fr);

    gap: 12px;
}

.server-card {

    padding: 18px;

    border-radius: 22px;

    background:
        rgba(255,255,255,.055);

    border:
        1px solid rgba(255,255,255,.10);

    backdrop-filter: blur(18px);

    box-shadow:
        0 10px 30px rgba(0,0,0,.16);
}

.server-card:active {
    transform: scale(.98);
}

.server-flag {
    font-size: 30px;
    margin-bottom: 8px;
}

.server-card b {
    display: block;
    font-size: 17px;
}

.server-card span {
    color: #8d96ae;
    font-size: 12px;
}

.info-grid {

    display: grid;

    grid-template-columns:
        repeat(3, 1fr);

    gap: 9px;
}

.info-card {

    padding: 15px 9px;

    text-align: center;

    border-radius: 18px;

    background:
        rgba(255,255,255,.045);

    border:
        1px solid rgba(255,255,255,.08);
}

.info-card strong {

    display: block;

    margin-bottom: 6px;

    font-size: 22px;

    color: #aab6ff;
}

.info-card span {

    color: #9299ad;

    font-size: 11px;
}

.page-head {

    margin: 8px 0 18px;
}

.page-head h1 {
    font-size: 28px;
}

.page-head p {
    color: #858da5;
}

.tabs {

    display: flex;

    gap: 8px;

    padding: 5px;

    margin-bottom: 15px;

    border-radius: 17px;

    background:
        rgba(255,255,255,.045);

    border:
        1px solid rgba(255,255,255,.08);
}

.tab {

    flex: 1;

    text-align: center;

    padding: 11px 8px;

    border-radius: 13px;

    color: #8d96ae;

    font-size: 13px;

    font-weight: 800;
}

.tab.active {

    color: white;

    background:
        rgba(255,255,255,.09);

    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.06);
}

.products-grid {

    display: grid;

    grid-template-columns:
        repeat(2, minmax(0, 1fr));

    gap: 11px;
}

.product-card {

    padding: 13px;

    border-radius: 22px;

    background:
        linear-gradient(
            145deg,
            rgba(255,255,255,.075),
            rgba(255,255,255,.035)
        );

    border:
        1px solid rgba(255,255,255,.10);

    backdrop-filter: blur(18px);

    box-shadow:
        0 10px 30px rgba(0,0,0,.18);
}

.diamond-art {

    height: 105px;

    display: flex;

    align-items: center;
    justify-content: center;

    margin-bottom: 9px;

    border-radius: 18px;

    background:
        radial-gradient(
            circle,
            rgba(110,100,255,.22),
            transparent 65%
        );
}

.diamond-art span {

    font-size: 68px;

    filter:
        drop-shadow(
            0 8px 15px
            rgba(75,100,255,.45)
        );
}

.diamond-art.big {
    width: 105px;
    margin: 0;
}

.product-info h3 {

    margin: 0 0 7px;

    font-size: 14px;

    min-height: 34px;
}

.price {

    font-size: 17px;

    font-weight: 900;

    margin-bottom: 11px;

    color: #d9ddff;
}

.label {

    display: block;

    margin: 16px 0 7px;

    color: #a3abc0;

    font-size: 13px;

    font-weight: 700;
}

input,
select {

    width: 100%;

    min-height: 48px;

    padding: 12px 14px;

    border-radius: 15px;

    outline: none;

    color: white;

    background:
        rgba(255,255,255,.055);

    border:
        1px solid rgba(255,255,255,.12);

    font-size: 14px;
}

input::placeholder {
    color: #6f778c;
}

select option {
    background: #101321;
    color: white;
}

.input-row {

    display: grid;

    grid-template-columns:
        1fr auto;

    gap: 8px;
}

.input-row .btn {
    white-space: nowrap;
}

.buy-card,
.payment-card,
.glass-panel,
.profile-card,
.support-card,
.balance-card {

    padding: 18px;

    border-radius: 24px;

    background:
        rgba(255,255,255,.055);

    border:
        1px solid rgba(255,255,255,.10);

    backdrop-filter: blur(18px);

    box-shadow:
        0 15px 40px rgba(0,0,0,.20);
}

.selected-product {

    display: flex;

    align-items: center;

    gap: 14px;

    margin-bottom: 15px;

    padding: 10px;

    border-radius: 19px;

    background:
        rgba(255,255,255,.045);

    border:
        1px solid rgba(255,255,255,.07);
}

.selected-product b {
    display: block;
    margin-bottom: 5px;
}

.selected-product strong {
    color: #aeb8ff;
}

.success-box,
.error-box,
.warning-box,
.loading-box {

    padding: 13px 14px;

    margin: 10px 0;

    border-radius: 15px;

    font-size: 13px;
}

.success-box {
    background: rgba(30,190,120,.10);
    border: 1px solid rgba(30,190,120,.20);
}

.error-box {
    background: rgba(255,70,90,.10);
    border: 1px solid rgba(255,70,90,.20);
}

.warning-box {
    background: rgba(255,180,40,.09);
    border: 1px solid rgba(255,180,40,.18);
    color: #ffd98a;
}

.loading-box {
    background: rgba(100,120,255,.10);
    border: 1px solid rgba(100,120,255,.18);
}

.payment-status {

    display: flex;

    justify-content: space-between;

    gap: 10px;

    padding: 12px 0;

    border-bottom:
        1px solid rgba(255,255,255,.07);
}

.payment-status span {
    color: #858da5;
}

.payment-status b {
    text-align: right;
}

.payment-price {

    margin: 20px 0;

    text-align: center;

    font-size: 34px;

    font-weight: 900;

    color: #dfe3ff;
}

.pay-number {

    padding: 16px;

    text-align: center;

    border-radius: 18px;

    background:
        rgba(90,80,255,.10);

    border:
        1px solid rgba(120,120,255,.15);

    margin-bottom: 12px;
}

.pay-number span {
    display: block;
    color: #858da5;
    font-size: 12px;
    margin-bottom: 6px;
}

.pay-number strong {
    font-size: 21px;
    letter-spacing: .5px;
}

.order-card,
.history-card,
.admin-card {

    margin-bottom: 10px;

    padding: 15px;

    border-radius: 20px;

    background:
        rgba(255,255,255,.05);

    border:
        1px solid rgba(255,255,255,.09);

    backdrop-filter: blur(16px);
}

.order-top {

    display: flex;

    align-items: center;
    justify-content: space-between;

    gap: 8px;

    margin-bottom: 12px;
}

.order-main span,
.order-main strong,
.order-main b {

    display: block;

    margin-bottom: 5px;
}

.order-main span {
    color: #858da5;
    font-size: 12px;
}

.order-card small {
    color: #626b82;
}

.status {

    display: inline-block;

    padding: 6px 9px;

    border-radius: 10px;

    font-size: 10px;

    background:
        rgba(255,255,255,.07);
}

.status.success {
    background: rgba(30,190,120,.13);
    color: #70e5b0;
}

.status.danger {
    background: rgba(255,70,90,.13);
    color: #ff8999;
}

.status.waiting {
    color: #c8cfff;
}

.balance-card {

    text-align: center;

    margin-bottom: 12px;
}

.balance-card span {

    display: block;

    color: #858da5;

    margin-bottom: 8px;
}

.balance-card strong {

    font-size: 35px;
}

.profile-card {
    text-align: center;
    margin-bottom: 12px;
}

.avatar {

    width: 70px;
    height: 70px;

    display: flex;

    align-items: center;
    justify-content: center;

    margin: 0 auto 12px;

    border-radius: 50%;

    font-size: 30px;
    font-weight: 900;

    background:
        linear-gradient(
            135deg,
            rgba(100,80,255,.7),
            rgba(0,150,255,.6)
        );

    box-shadow:
        0 10px 30px rgba(60,80,255,.25);
}

.profile-card h2 {
    margin-bottom: 5px;
}

.profile-card p {
    color: #858da5;
}

.support-card {
    text-align: center;
}

.support-icon {
    font-size: 55px;
    margin-bottom: 10px;
}

.support-card p {
    color: #9299ad;
    line-height: 1.6;
}

.support-item {

    display: flex;

    align-items: center;

    gap: 10px;

    text-align: left;

    padding: 13px;

    margin-top: 8px;

    border-radius: 15px;

    background:
        rgba(255,255,255,.045);
}

.history-card {

    display: flex;

    align-items: center;
    justify-content: space-between;

    gap: 10px;
}

.history-card span {

    display: block;

    color: #737c92;

    font-size: 11px;

    margin-top: 4px;
}

.admin-info span {

    display: block;

    margin-bottom: 6px;

    color: #8d96ae;

    font-size: 12px;
}

.admin-info b {
    color: white;
}

.admin-form {

    display: grid;

    grid-template-columns:
        1fr auto;

    gap: 8px;

    margin-top: 12px;
}

.empty-box {

    padding: 25px;

    text-align: center;

    border-radius: 20px;

    color: #7f879c;

    background:
        rgba(255,255,255,.04);

    border:
        1px solid rgba(255,255,255,.07);
}

.success-page {

    min-height: 65vh;

    display: flex;

    align-items: center;
    justify-content: center;

    flex-direction: column;

    text-align: center;
}

.success-page p {
    color: #858da5;
    margin-bottom: 20px;
}

.success-icon {

    width: 80px;
    height: 80px;

    display: flex;

    align-items: center;
    justify-content: center;

    margin-bottom: 18px;

    border-radius: 50%;

    font-size: 40px;

    background:
        rgba(30,190,120,.12);

    border:
        1px solid rgba(30,190,120,.25);

    color: #70e5b0;
}

.bottom-nav {

    position: fixed;

    left: 50%;

    bottom: 10px;

    transform: translateX(-50%);

    width:
        min(590px, calc(100% - 20px));

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 4px;

    padding: 7px;

    z-index: 50;

    border-radius: 22px;

    background:
        rgba(12,15,28,.78);

    border:
        1px solid rgba(255,255,255,.11);

    backdrop-filter: blur(22px);

    box-shadow:
        0 15px 40px rgba(0,0,0,.40);
}

.bottom-nav a {

    display: flex;

    flex-direction: column;

    align-items: center;
    justify-content: center;

    min-height: 55px;

    border-radius: 16px;

    color: #747d94;

    font-size: 10px;

    font-weight: 700;
}

.bottom-nav a span {

    font-size: 20px;

    margin-bottom: 2px;
}

.bottom-nav a.active {

    color: white;

    background:
        rgba(255,255,255,.07);
}

@media (max-width: 390px) {

    .products-grid {
        grid-template-columns: 1fr 1fr;
    }

    .input-row {
        grid-template-columns: 1fr;
    }

    .hero {
        min-height: 220px;
        padding: 20px;
    }

    h1 {
        font-size: 27px;
    }
}

</style>

</head>

<body>

<div class="container">

    <div class="topbar">

        <a href="/" class="logo">
            SNG DONAT💎
        </a>

        <a href="/balance" class="balance-mini">
            💎 Баланс
        </a>

    </div>

    {{ body|safe }}

</div>


<div class="bottom-nav">

    <a href="/">
        <span>⌂</span>
        Главная
    </a>

    <a href="/shop">
        <span>💎</span>
        Каталог
    </a>

    <a href="/balance">
        <span>💰</span>
        Баланс
    </a>

    <a href="/profile">
        <span>👤</span>
        Профиль
    </a>

</div>

</body>

</html>
"""


def page(body):
    return render_template_string(
        BASE_HTML,
        body=body
    )
# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return page("""
    <div class="hero">

        <div class="hero-text">

            <div class="badge">
                💎 SNG DONAT
            </div>

            <h1>
                Алмазҳо барои аккаунти шумо
            </h1>

            <p>
                Зуд, осон ва қулай.
            </p>

            <a class="btn primary" href="/shop">
                Каталогро кушодан
            </a>

        </div>

    </div>


    <div class="section-title">

        <h2>
            Серверҳо
        </h2>

        <span>
            Интихоб кунед
        </span>

    </div>


    <div class="server-grid">

        <a class="server-card" href="/shop?server=sng">

            <div class="server-flag">
                🇷🇺
            </div>

            <b>
                СНГ
            </b>

            <span>
                Free Fire СНГ
            </span>

        </a>


        <a class="server-card" href="/shop?server=id">

            <div class="server-flag">
                🇮🇩
            </div>

            <b>
                Indonesia
            </b>

            <span>
                Free Fire Indonesia
            </span>

        </a>

    </div>


    <div class="section-title">

        <h2>
            Чӣ тавр харидан?
        </h2>

    </div>


    <div class="info-grid">

        <div class="info-card">
            <strong>1</strong>
            <span>
                Маҳсулотро интихоб кунед
            </span>
        </div>

        <div class="info-card">
            <strong>2</strong>
            <span>
                UID-ро санҷед
            </span>
        </div>

        <div class="info-card">
            <strong>3</strong>
            <span>
                Пардохт кунед
            </span>
        </div>

    </div>
    """)


# =========================================================
# SHOP
# =========================================================

@app.route("/shop")
def shop():

    server = request.args.get(
        "server",
        "sng"
    )

    if server not in PRODUCTS:
        server = "sng"

    cards = ""

    for name, product_id, price in PRODUCTS.get(
        server,
        []
    ):

        cards += f"""
        <div class="product-card">

            <div class="diamond-art">
                <span>💎</span>
            </div>

            <div class="product-info">

                <h3>
                    {name}
                </h3>

                <div class="price">
                    {money(price)}
                </div>

            </div>

            <a
                class="btn primary full"
                href="/buy?server={server}&product={quote(product_id)}"
            >
                Купить
            </a>

        </div>
        """

    active_sng = "active" if server == "sng" else ""
    active_id = "active" if server == "id" else ""

    return page(f"""

    <div class="page-head">

        <div>

            <div class="badge">
                💎 КАТАЛОГ
            </div>

            <h1>
                Маҳсулотҳо
            </h1>

        </div>

    </div>


    <div class="tabs">

        <a
            class="tab {active_sng}"
            href="/shop?server=sng"
        >
            🇷🇺 СНГ
        </a>

        <a
            class="tab {active_id}"
            href="/shop?server=id"
        >
            🇮🇩 Indonesia
        </a>

    </div>


    <div class="products-grid">

        {cards}

    </div>

    """)


# =========================================================
# BUY
# =========================================================

@app.route(
    "/buy",
    methods=["GET", "POST"]
)
def buy():

    server = request.args.get(
        "server",
        request.form.get(
            "server",
            "sng"
        )
    )

    product_id = request.args.get(
        "product",
        request.form.get(
            "product",
            ""
        )
    )

    if server not in PRODUCTS:
        return redirect("/shop")


    product = get_product(
        server,
        product_id
    )

    if not product:
        return redirect(
            "/shop?server=" + quote(server)
        )


    # -----------------------------------------------------
    # CREATE ORDER
    # -----------------------------------------------------

    if request.method == "POST":

        uid = clean_uid(
            request.form.get(
                "uid",
                ""
            )
        )

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        nickname = request.form.get(
            "nickname",
            ""
        ).strip()


        if len(uid) < 5:

            return page("""
            <div class="error-box">
                UID нодуруст аст.
            </div>

            <a
                class="btn glass full"
                href="javascript:history.back()"
            >
                ← Бозгашт
            </a>
            """)


        if not phone:

            return page("""
            <div class="error-box">
                Рақами телефонро ворид кунед.
            </div>

            <a
                class="btn glass full"
                href="javascript:history.back()"
            >
                ← Бозгашт
            </a>
            """)


        # Агар nickname аз браузер наомада бошад,
        # UID-ро аз API боз месанҷем.

        if not nickname:

            result = check_free_fire_uid(
                uid,
                server
            )

            if not result["ok"]:

                return page("""
                <div class="error-box">
                    Аккаунт ёфт нашуд ё API ҳоло
                    ҷавоб намедиҳад.
                </div>

                <a
                    class="btn glass full"
                    href="javascript:history.back()"
                >
                    ← Бозгашт
                </a>
                """)

            nickname = result["nickname"]


        conn = db()

        cursor = conn.execute("""
            INSERT INTO orders
            (
                uid,
                phone,
                product,
                diamonds,
                price,
                server,
                nickname,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uid,
            phone,
            product["name"],
            product["id"],
            product["price"],
            server,
            nickname,
            "Ожидает оплаты",
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))


        order_id = cursor.lastrowid

        conn.commit()
        conn.close()


        session["phone"] = phone

        return redirect(
            "/payment/" + str(order_id)
        )


    # -----------------------------------------------------
    # BUY PAGE
    # -----------------------------------------------------

    server_name = (
        "СНГ 🇷🇺"
        if server == "sng"
        else
        "Indonesia 🇮🇩"
    )


    # Ин ҷо f-string истифода намекунем,
    # то JavaScript хато надиҳад.

    body = """
    <div class="page-head">

        <div>

            <div class="badge">
                КУПИТЬ
            </div>

            <h1>
                __PRODUCT_NAME__
            </h1>

            <p>
                __SERVER_NAME__
            </p>

        </div>

    </div>


    <div class="buy-card">


        <div class="selected-product">

            <div class="diamond-art big">

                <span>
                    💎
                </span>

            </div>


            <div>

                <b>
                    __PRODUCT_NAME__
                </b>

                <strong>
                    __PRICE__
                </strong>

            </div>

        </div>


        <label class="label">
            UID Free Fire
        </label>


        <div class="input-row">

            <input
                id="uid"
                name="uid"
                inputmode="numeric"
                placeholder="UID-ро ворид кунед"
                maxlength="20"
            >


            <button
                type="button"
                class="btn glass"
                onclick="checkUID()"
            >
                🔎 Проверить UID
            </button>

        </div>


        <div id="uidResult"></div>


        <label class="label">
            Номер телефона
        </label>


        <input
            id="phone"
            name="phone"
            inputmode="tel"
            placeholder="+992 ..."
        >


        <input
            type="hidden"
            id="nickname"
        >


        <button
            type="button"
            class="btn primary full"
            onclick="continueBuy()"
        >
            Продолжить
        </button>


    </div>


    <script>

    let uidChecked = false;


    async function checkUID() {

        const uid =
            document.getElementById("uid")
            .value
            .trim();


        const result =
            document.getElementById("uidResult");


        if (uid.length < 5) {

            result.innerHTML =
                '<div class="error-box">' +
                'UID-ро дуруст ворид кунед.' +
                '</div>';

            return;
        }


        result.innerHTML =
            '<div class="loading-box">' +
            '⏳ UID санҷида мешавад...' +
            '</div>';


        try {

            const response =
                await fetch(
                    "/api/check_uid?uid=" +
                    encodeURIComponent(uid) +
                    "&server=__SERVER__"
                );


            const data =
                await response.json();


            if (data.ok) {

                uidChecked = true;


                document.getElementById(
                    "nickname"
                ).value =
                    data.nickname;


                result.innerHTML =
                    '<div class="success-box">' +
                    '✅ Аккаунт ёфт шуд<br>' +
                    '<b>' +
                    escapeHtml(data.nickname) +
                    '</b>' +
                    '</div>';

            } else {

                uidChecked = false;


                document.getElementById(
                    "nickname"
                ).value = "";


                result.innerHTML =
                    '<div class="error-box">' +
                    '❌ Аккаунт ёфт нашуд ё API ҷавоб надод.' +
                    '</div>';
            }


        } catch (error) {

            uidChecked = false;


            result.innerHTML =
                '<div class="error-box">' +
                '❌ Хатои пайвастшавӣ ба API.' +
                '</div>';
        }

    }


    function escapeHtml(text) {

        const div =
            document.createElement("div");

        div.textContent = text;

        return div.innerHTML;
    }


    function addField(
        form,
        name,
        value
    ) {

        const input =
            document.createElement("input");

        input.type = "hidden";

        input.name = name;

        input.value = value;

        form.appendChild(input);
    }


    function continueBuy() {

        const uid =
            document.getElementById("uid")
            .value
            .trim();


        const phone =
            document.getElementById("phone")
            .value
            .trim();


        const nickname =
            document.getElementById("nickname")
            .value
            .trim();


        if (!uid) {

            alert(
                "UID-ро ворид кунед."
            );

            return;
        }


        if (!uidChecked || !nickname) {

            alert(
                "Аввал UID-ро санҷед."
            );

            return;
        }


        if (!phone) {

            alert(
                "Рақами телефонро ворид кунед."
            );

            return;
        }


        const form =
            document.createElement("form");


        form.method = "POST";

        form.action = "/buy";


        addField(
            form,
            "server",
            "__SERVER__"
        );


        addField(
            form,
            "product",
            "__PRODUCT__"
        );


        addField(
            form,
            "uid",
            uid
        );


        addField(
            form,
            "phone",
            phone
        );


        addField(
            form,
            "nickname",
            nickname
        );


        document.body.appendChild(form);

        form.submit();
    }

    </script>
    """


    body = body.replace(
        "__SERVER__",
        server
    )

    body = body.replace(
        "__PRODUCT__",
        product["id"]
    )

    body = body.replace(
        "__PRODUCT_NAME__",
        product["name"]
    )

    body = body.replace(
        "__PRICE__",
        money(product["price"])
    )

    body = body.replace(
        "__SERVER_NAME__",
        server_name
    )


    return page(body)


# =========================================================
# UID CHECK API
# =========================================================

@app.route("/api/check_uid")
def api_check_uid():

    uid = clean_uid(
        request.args.get(
            "uid",
            ""
        )
    )

    server = request.args.get(
        "server",
        "sng"
    )


    if server not in (
        "sng",
        "id"
    ):

        server = "sng"


    if len(uid) < 5:

        return jsonify({
            "ok": False,
            "error": "invalid_uid"
        })


    result = check_free_fire_uid(
        uid,
        server
    )


    if result["ok"]:

        return jsonify({
            "ok": True,
            "nickname": result["nickname"]
        })


    return jsonify({
        "ok": False,
        "error": "not_found"
    })


# =========================================================
# PAYMENT
# =========================================================

@app.route("/payment/<int:order_id>")
def payment(order_id):

    conn = db()

    order = conn.execute("""
        SELECT *
        FROM orders
        WHERE id = ?
    """, (
        order_id,
    )).fetchone()

    conn.close()


    if not order:
        return redirect("/orders")


    return page(f"""

    <div class="page-head">

        <div>

            <div class="badge">
                ПАРДОХТ
            </div>

            <h1>
                Фармоиш №{order["id"]}
            </h1>

        </div>

    </div>


    <div class="payment-card">


        <div class="payment-status">

            <span>
                Маҳсулот
            </span>

            <b>
                {order["product"]}
            </b>

        </div>


        <div class="payment-status">

            <span>
                Никнейм
            </span>

            <b>
                {order["nickname"]}
            </b>

        </div>


        <div class="payment-status">

            <span>
                UID
            </span>

            <b>
                {order["uid"]}
            </b>

        </div>


        <div class="payment-status">

            <span>
                Телефон
            </span>

            <b>
                {order["phone"]}
            </b>

        </div>


        <div class="payment-price">
            {money(order["price"])}
        </div>


        <div class="pay-number">

            <span>
                Рақами пардохт
            </span>

            <strong>
                {PAYMENT_NUMBER}
            </strong>

        </div>


        <div class="warning-box">

            Аввал маблағро ба рақами боло
            пардохт кунед, баъд тугмаи
            «Я оплатил»-ро пахш кунед.

        </div>


        <a
            class="btn primary full"
            href="/paid/{order["id"]}"
        >
            Я оплатил
        </a>


        <br>


        <a
            class="btn glass full"
            href="/orders"
        >
            Фармоишҳои ман
        </a>


    </div>

    """)


# =========================================================
# PAID
# =========================================================

@app.route("/paid/<int:order_id>")
def paid(order_id):

    conn = db()

    conn.execute("""
        UPDATE orders
        SET status = ?
        WHERE id = ?
    """, (
        "Проверка оплаты",
        order_id
    ))

    conn.commit()
    conn.close()


    return page(f"""

    <div class="success-page">

        <div class="success-icon">
            ✓
        </div>


        <h1>
            Пардохт фиристода шуд
        </h1>


        <p>
            Фармоиш №{order_id}
            барои санҷиш фиристода шуд.
        </p>


        <a
            class="btn primary"
            href="/orders"
        >
            Фармоишҳои ман
        </a>

    </div>

    """)


# =========================================================
# ORDERS
# =========================================================

@app.route("/orders")
def orders():

    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM orders
        ORDER BY id DESC
    """).fetchall()

    conn.close()


    cards = ""


    if not rows:

        cards = """
        <div class="empty-box">
            Ҳоло фармоиш нест.
        </div>
        """


    for order in rows:

        status_class = "waiting"


        if order["status"] == "Готово":
            status_class = "success"


        elif order["status"] == "Отменено":
            status_class = "danger"


        cards += f"""

        <div class="order-card">


            <div class="order-top">

                <b>
                    Фармоиш №{order["id"]}
                </b>


                <span class="status {status_class}">
                    {order["status"]}
                </span>

            </div>


            <div class="order-main">

                <strong>
                    {order["nickname"]}
                </strong>

                <span>
                    UID: {order["uid"]}
                </span>

                <span>
                    {order["product"]}
                </span>

                <b>
                    {money(order["price"])}
                </b>

            </div>


            <small>
                {order["created_at"]}
            </small>


        </div>

        """


    return page(f"""

    <div class="page-head">

        <div>

            <div class="badge">
                ORDERS
            </div>

            <h1>
                Фармоишҳои ман
            </h1>

        </div>

    </div>


    <div class="orders-list">

        {cards}

    </div>

    """)


# =========================================================
# BALANCE
# =========================================================

@app.route("/balance")
def balance():

    phone = session.get(
        "phone",
        ""
    )


    current_balance = get_balance(
        phone
    )


    return page(f"""

    <div class="page-head">

        <div>

            <div class="badge">
                BALANCE
            </div>

            <h1>
                Баланс
            </h1>

        </div>

    </div>


    <div class="balance-card">

        <span>
            Баланс
        </span>

        <strong>
            {money(current_balance)}
        </strong>

    </div>


    <div class="glass-panel">

        <h3>
            Пополнить баланс
        </h3>


        <form
            method="POST"
            action="/balance/topup"
        >


            <label class="label">
                Номер телефона
            </label>


            <input
                name="phone"
                inputmode="tel"
                value="{session.get("phone", "")}"
                placeholder="+992 ..."
                required
            >


            <label class="label">
                Маблағ
            </label>


            <input
                name="amount"
                type="number"
                min="1"
                step="1"
                placeholder="Масалан: 50"
                required
            >


            <button
                class="btn primary full"
                type="submit"
            >
                Пополнить
            </button>


        </form>

    </div>


    <br>


    <a
        class="btn glass full"
        href="/balance/history"
    >
        Таърихи баланс
    </a>

    """)


# =========================================================
# BALANCE TOPUP
# =========================================================

@app.route(
    "/balance/topup",
    methods=["POST"]
)
def balance_topup():

    phone = request.form.get(
        "phone",
        ""
    ).strip()

    amount_text = request.form.get(
        "amount",
        ""
    ).strip()


    try:

        amount = int(
            amount_text
        )

    except ValueError:

        return page("""
        <div class="error-box">
            Маблағ нодуруст аст.
        </div>

        <a
            class="btn glass full"
            href="/balance"
        >
            Бозгашт
        </a>
        """)


    if not phone or amount <= 0:

        return page("""
        <div class="error-box">
            Маълумотро пурра ворид кунед.
        </div>

        <a
            class="btn glass full"
            href="/balance"
        >
            Бозгашт
        </a>
        """)


    session["phone"] = phone


    conn = db()

    cursor = conn.execute("""
        INSERT INTO balance_topups
        (
            phone,
            amount,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        phone,
        amount,
        "Ожидает проверки",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    ))


    topup_id = cursor.lastrowid


    conn.commit()
    conn.close()


    return redirect(
        "/balance/topup/paid/"
        + str(topup_id)
    )


# =========================================================
# BALANCE TOPUP PAYMENT
# =========================================================

@app.route(
    "/balance/topup/paid/<int:topup_id>"
)
def balance_topup_paid(topup_id):

    conn = db()

    topup = conn.execute("""
        SELECT *
        FROM balance_topups
        WHERE id = ?
    """, (
        topup_id,
    )).fetchone()

    conn.close()


    if not topup:
        return redirect("/balance")


    return page(f"""

    <div class="payment-card">


        <div class="badge">
            ПОПОЛНЕНИЕ
        </div>


        <h1>
            {money(topup["amount"])}
        </h1>


        <p>
            Рақами пардохт:
        </p>


        <div class="pay-number">

            <strong>
                {PAYMENT_NUMBER}
            </strong>

        </div>


        <div class="warning-box">

            Маблағро ба рақами боло
            пардохт кунед.

        </div>


        <a
            class="btn primary full"
            href="/admin"
        >
            Ман пардохт кардам
        </a>


        <br>


        <a
            class="btn glass full"
            href="/balance"
        >
            Бозгашт
        </a>


    </div>

    """)


# =========================================================
# BALANCE HISTORY
# =========================================================

@app.route("/balance/history")
def balance_history():

    phone = session.get(
        "phone",
        ""
    )


    if not phone:
        return redirect("/balance")


    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM balance_topups
        WHERE phone = ?
        ORDER BY id DESC
    """, (
        phone,
    )).fetchall()

    conn.close()


    items = ""


    if not rows:

        items = """
        <div class="empty-box">
            Таърихи пополнения холӣ аст.
        </div>
        """


    for row in rows:

        items += f"""

        <div class="history-card">

            <div>

                <b>
                    {money(row["amount"])}
                </b>

                <span>
                    {row["created_at"]}
                </span>

            </div>


            <span class="status waiting">
                {row["status"]}
            </span>

        </div>

        """


    return page(f"""

    <div class="page-head">

        <div>

            <div class="badge">
                HISTORY
            </div>

            <h1>
                Таърихи баланс
            </h1>

        </div>

    </div>


    {items}

    """)
# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
def profile():

    phone = session.get(
        "phone",
        ""
    )

    balance = get_balance(phone)

    conn = db()

    if phone:

        order_count = conn.execute("""
            SELECT COUNT(*)
            FROM orders
            WHERE phone = ?
        """, (
            phone,
        )).fetchone()[0]

    else:

        order_count = 0

    conn.close()


    phone_display = phone if phone else "Ҳоло ворид нашудааст"


    return page(f"""

    <div class="page-head">

        <div class="badge">
            PROFILE
        </div>

        <h1>
            Профиль
        </h1>

    </div>


    <div class="profile-card">

        <div class="avatar">
            👤
        </div>

        <h2>
            SNG DONAT
        </h2>

        <p>
            {phone_display}
        </p>

    </div>


    <div class="info-grid">

        <div class="info-card">

            <strong>
                {order_count}
            </strong>

            <span>
                Фармоишҳо
            </span>

        </div>


        <div class="info-card">

            <strong>
                {balance}
            </strong>

            <span>
                Баланс
            </span>

        </div>


        <div class="info-card">

            <strong>
                💎
            </strong>

            <span>
                SNG DONAT
            </span>

        </div>

    </div>


    <br>


    <a
        class="btn glass full"
        href="/orders"
    >
        📦 Фармоишҳои ман
    </a>


    <br>


    <a
        class="btn glass full"
        href="/balance"
    >
        💰 Баланс
    </a>


    <br>


    <a
        class="btn glass full"
        href="/support"
    >
        💬 Помощь
    </a>

    """)


# =========================================================
# SUPPORT
# =========================================================

@app.route("/support")
def support():

    return page("""

    <div class="page-head">

        <div class="badge">
            SUPPORT
        </div>

        <h1>
            Помощь
        </h1>

    </div>


    <div class="support-card">

        <div class="support-icon">
            💬
        </div>


        <h2>
            Поддержка SNG DONAT
        </h2>


        <p>
            Агар ҳангоми харид мушкилӣ пайдо шавад,
            бо дастгирӣ тамос гиред.
        </p>


        <div class="support-item">

            <span>
                📱
            </span>

            <div>

                <b>
                    Телефон
                </b>

                <br>

                <span>
                    +992 93 418 42 18
                </span>

            </div>

        </div>


        <div class="support-item">

            <span>
                💎
            </span>

            <div>

                <b>
                    UID
                </b>

                <br>

                <span>
                    Пеш аз харид UID-ро санҷед.
                </span>

            </div>

        </div>


        <br>


        <a
            class="btn primary full"
            href="/shop"
        >
            Ба каталог
        </a>

    </div>

    """)


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        if (
            username == ADMIN_USER
            and
            password == ADMIN_PASSWORD
        ):

            session["admin"] = True

            return redirect("/admin")


        return page("""

        <div class="error-box">
            Логин ё пароль нодуруст аст.
        </div>

        <a
            class="btn glass full"
            href="/admin/login"
        >
            Боз кӯшиш кардан
        </a>

        """)


    return page("""

    <div class="page-head">

        <div class="badge">
            ADMIN
        </div>

        <h1>
            Панели админ
        </h1>

    </div>


    <div class="glass-panel">

        <form method="POST">

            <label class="label">
                Логин
            </label>

            <input
                name="username"
                autocomplete="username"
                placeholder="admin"
                required
            >


            <label class="label">
                Пароль
            </label>

            <input
                type="password"
                name="password"
                autocomplete="current-password"
                placeholder="Пароль"
                required
            >


            <br>


            <button
                class="btn primary full"
                type="submit"
            >
                Войти
            </button>

        </form>

    </div>

    """)


# =========================================================
# ADMIN
# =========================================================

@app.route("/admin")
def admin():

    if not session.get("admin"):

        return redirect("/admin/login")


    conn = db()


    orders = conn.execute("""
        SELECT *
        FROM orders
        ORDER BY id DESC
    """).fetchall()


    topups = conn.execute("""
        SELECT *
        FROM balance_topups
        ORDER BY id DESC
    """).fetchall()


    conn.close()


    order_html = ""


    if not orders:

        order_html = """
        <div class="empty-box">
            Фармоиш нест.
        </div>
        """


    for order in orders:

        order_html += f"""

        <div class="admin-card">

            <div class="order-top">

                <b>
                    №{order["id"]}
                </b>

                <span class="status waiting">
                    {order["status"]}
                </span>

            </div>


            <div class="admin-info">

                <span>
                    Маҳсулот:
                    <b>{order["product"]}</b>
                </span>

                <span>
                    Ник:
                    <b>{order["nickname"]}</b>
                </span>

                <span>
                    UID:
                    <b>{order["uid"]}</b>
                </span>

                <span>
                    Телефон:
                    <b>{order["phone"]}</b>
                </span>

                <span>
                    Сумма:
                    <b>{money(order["price"])}</b>
                </span>

                <span>
                    Сервер:
                    <b>{order["server"]}</b>
                </span>

            </div>


            <form
                class="admin-form"
                method="POST"
                action="/admin/order/{order["id"]}/status"
            >

                <select name="status">

                    <option
                        value="Ожидает оплаты"
                        {"selected" if order["status"] == "Ожидает оплаты" else ""}
                    >
                        Ожидает оплаты
                    </option>

                    <option
                        value="Проверка оплаты"
                        {"selected" if order["status"] == "Проверка оплаты" else ""}
                    >
                        Проверка оплаты
                    </option>

                    <option
                        value="Готово"
                        {"selected" if order["status"] == "Готово" else ""}
                    >
                        Готово
                    </option>

                    <option
                        value="Отменено"
                        {"selected" if order["status"] == "Отменено" else ""}
                    >
                        Отменено
                    </option>

                </select>


                <button
                    class="btn primary"
                    type="submit"
                >
                    Сохранить
                </button>

            </form>

        </div>

        """


    topup_html = ""


    if not topups:

        topup_html = """
        <div class="empty-box">
            Пополнение нест.
        </div>
        """


    for topup in topups:

        topup_html += f"""

        <div class="admin-card">

            <div class="order-top">

                <b>
                    Пополнение №{topup["id"]}
                </b>

                <span class="status waiting">
                    {topup["status"]}
                </span>

            </div>


            <div class="admin-info">

                <span>
                    Телефон:
                    <b>{topup["phone"]}</b>
                </span>

                <span>
                    Сумма:
                    <b>{money(topup["amount"])}</b>
                </span>

                <span>
                    Время:
                    <b>{topup["created_at"]}</b>
                </span>

            </div>


            <a
                class="btn primary full"
                href="/admin/topup/{topup["id"]}/approve"
            >
                Подтвердить пополнение
            </a>

        </div>

        """


    return page(f"""

    <div class="page-head">

        <div class="badge">
            ADMIN PANEL
        </div>

        <h1>
            Управление
        </h1>

    </div>


    <div class="section-title">

        <h2>
            Фармоишҳо
        </h2>

        <span>
            {len(orders)}
        </span>

    </div>


    {order_html}


    <div class="section-title">

        <h2>
            Пополнение баланс
        </h2>

        <span>
            {len(topups)}
        </span>

    </div>


    {topup_html}


    <br>


    <a
        class="btn glass full"
        href="/"
    >
        ← Сайт
    </a>

    """)


# =========================================================
# ADMIN ORDER STATUS
# =========================================================

@app.route(
    "/admin/order/<int:order_id>/status",
    methods=["POST"]
)
def admin_order_status(order_id):

    if not session.get("admin"):

        return redirect("/admin/login")


    status = request.form.get(
        "status",
        "Ожидает оплаты"
    )


    allowed = [
        "Ожидает оплаты",
        "Проверка оплаты",
        "Готово",
        "Отменено"
    ]


    if status not in allowed:

        status = "Ожидает оплаты"


    conn = db()


    conn.execute("""
        UPDATE orders
        SET status = ?
        WHERE id = ?
    """, (
        status,
        order_id
    ))


    conn.commit()
    conn.close()


    return redirect("/admin")


# =========================================================
# ADMIN APPROVE BALANCE TOPUP
# =========================================================

@app.route(
    "/admin/topup/<int:topup_id>/approve"
)
def admin_topup_approve(topup_id):

    if not session.get("admin"):

        return redirect("/admin/login")


    conn = db()


    topup = conn.execute("""
        SELECT *
        FROM balance_topups
        WHERE id = ?
    """, (
        topup_id,
    )).fetchone()


    if not topup:

        conn.close()

        return redirect("/admin")


    if topup["status"] != "Готово":

        conn.execute("""
            INSERT INTO wallets
            (
                phone,
                balance,
                created_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(phone)
            DO UPDATE SET balance =
                balance + excluded.balance
        """, (
            topup["phone"],
            topup["amount"],
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        ))


        conn.execute("""
            UPDATE balance_topups
            SET status = ?
            WHERE id = ?
        """, (
            "Готово",
            topup_id
        ))


        conn.commit()


    conn.close()


    return redirect("/admin")


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin",
        None
    )

    return redirect("/admin/login")


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    print("=" * 40)
    print("          SNG DONAT💎")
    print("=" * 40)
    print("Сайт: http://127.0.0.1:5000")
    print("Admin: http://127.0.0.1:5000/admin")
    print("UID CHECK: ENABLED")
    print("=" * 40)

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
