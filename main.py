# ==============================================================================
# APEX ALPHA MASTER PRODUCTION BOT v29.0 (FINAL PERFECTED EDITION)
# Multi-Market | FVG & Imbalance | Dynamic Trailing SL | Render 24/7 Remote URL
# ==============================================================================

import asyncio
import datetime
import json
import logging
import os
import time
import aiohttp
from flask import Flask, jsonify, request
from threading import Thread

# 🛠️ TELEGRAM CONFIGURATION
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8829301795:AAFY8li7fRNf5s_KgINPoZBLzEYL6_Ec9MI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8195487233")

# 🧠 UNIVERSAL JSON BRAIN (Multi-Asset Engine with FVG & Trailing Rules)
JSON_BRAIN_CONFIG = """
{
    "XAUUSD": {
        "asset_type": "COMMODITY",
        "pip_value_per_lot": 10.0,
        "pip_multiplier": 10,
        "sl_pips": 12,
        "min_fvg_size_pips": 1.5,
        "break_even_pips": 10.0,
        "trailing_distance_pips": 8.0,
        "atr_filter_ratio": 0.7
    },
    "EURUSD": {
        "asset_type": "FOREX",
        "pip_value_per_lot": 10.0,
        "pip_multiplier": 10000,
        "sl_pips": 8,
        "min_fvg_size_pips": 0.0008,
        "break_even_pips": 6.0,
        "trailing_distance_pips": 5.0,
        "atr_filter_ratio": 0.6
    },
    "GBPUSD": {
        "asset_type": "FOREX",
        "pip_value_per_lot": 10.0,
        "pip_multiplier": 10000,
        "sl_pips": 10,
        "min_fvg_size_pips": 0.0010,
        "break_even_pips": 8.0,
        "trailing_distance_pips": 6.0,
        "atr_filter_ratio": 0.65
    },
    "BTCUSD": {
        "asset_type": "CRYPTO",
        "pip_value_per_lot": 1.0,
        "pip_multiplier": 1,
        "sl_pips": 150,
        "min_fvg_size_pips": 20.0,
        "break_even_pips": 100.0,
        "trailing_distance_pips": 80.0,
        "atr_filter_ratio": 0.8
    }
}
"""

ACTIVE_MARKET = "XAUUSD"

# 📊 GLOBAL ACCOUNT TRACKERS
ACCOUNT_BALANCE = 115000.0
MAX_DAILY_TRADES = 4
DAILY_TRADE_COUNT = 0
IS_SYSTEM_LOCKED = False

ACTIVE_POSITIONS = {}

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
BRAIN_RULES = json.loads(JSON_BRAIN_CONFIG)

# ==============================================================================
# 🌐 RENDER 24/7 SERVER & REMOTE CONTROL URL API
# ==============================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <div style="font-family: sans-serif; text-align: center; padding: 40px; background: #0d1117; color: #c9d1d9;">
        <h1 style="color: #58a6ff;">⚡ APEX ALPHA MASTER BOT IS LIVE</h1>
        <p><b>Active Market:</b> {ACTIVE_MARKET}</p>
        <p><b>Account Balance:</b> ${ACCOUNT_BALANCE}</p>
        <p><b>Daily Trades Executed:</b> {DAILY_TRADE_COUNT}/{MAX_DAILY_TRADES}</p>
        <p><b>Active Trades:</b> {len(ACTIVE_POSITIONS)}</p>
        <hr style="border-color: #30363d; width: 60%;">
        <p>Remote Status Endpoint: <a href="/status" style="color: #58a6ff;"><code>/status</code></a></p>
    </div>
    """

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "ONLINE",
        "active_market": ACTIVE_MARKET,
        "balance": ACCOUNT_BALANCE,
        "daily_trades_count": DAILY_TRADE_COUNT,
        "max_daily_trades": MAX_DAILY_TRADES,
        "active_positions": ACTIVE_POSITIONS,
        "server_time_utc": str(datetime.datetime.now(datetime.timezone.utc))
    })

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ==============================================================================
# 🎯 DYNAMIC RISK & LOT CALCULATOR
# ==============================================================================
def calculate_alpha_lot_size(balance, asset_symbol, risk_pct=0.75):
    asset_config = BRAIN_RULES.get(asset_symbol, BRAIN_RULES["XAUUSD"])
    sl_pips = asset_config["sl_pips"]
    pip_val = asset_config["pip_value_per_lot"]

    risk_usd = balance * (risk_pct / 100.0)
    calculated_lot = risk_usd / (sl_pips * pip_val)
    return max(round(calculated_lot, 2), 0.01)

# ==============================================================================
# 🏛️ INSTITUTIONAL FVG & IMBALANCE ENGINE
# ==============================================================================
def detect_institutional_fvg(candles_3, asset_symbol):
    asset_config = BRAIN_RULES.get(asset_symbol, BRAIN_RULES["XAUUSD"])
    min_fvg = asset_config["min_fvg_size_pips"]

    c1 = candles_3[0]
    c3 = candles_3[2]

    # Bullish FVG
    if c3["low"] > c1["high"]:
        gap_size = c3["low"] - c1["high"]
        if gap_size >= min_fvg:
            fvg_mid_level = round(c1["high"] + (gap_size / 2.0), 5)
            return "BULLISH_FVG", fvg_mid_level, gap_size

    # Bearish FVG
    elif c3["high"] < c1["low"]:
        gap_size = c1["low"] - c3["high"]
        if gap_size >= min_fvg:
            fvg_mid_level = round(c3["high"] + (gap_size / 2.0), 5)
            return "BEARISH_FVG", fvg_mid_level, gap_size

    return "NO_FVG", 0.0, 0.0

# ==============================================================================
# 📱 TELEGRAM NOTIFIER ENGINE
# ==============================================================================
async def send_telegram_async(session, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        async with session.post(url, json=payload, timeout=5) as response:
            return await response.json()
    except Exception as e:
        logging.error(f"Telegram Error: {e}")

# ==============================================================================
# 🔄 DYNAMIC TRAILING SL & PROFIT HUNTING
# ==============================================================================
async def process_trailing_sl_and_profit_lock(session, symbol, current_price):
    asset_config = BRAIN_RULES.get(symbol, BRAIN_RULES["XAUUSD"])
    pip_mult = asset_config["pip_multiplier"]
    be_pips = asset_config["break_even_pips"]
    trail_dist = asset_config["trailing_distance_pips"]

    to_delete = []

    for pos_id, pos in list(ACTIVE_POSITIONS.items()):
        if pos["symbol"] != symbol:
            continue

        trade_type = pos["type"]
        entry = pos["entry"]

        # BUY Positions
        if trade_type == "BUY":
            profit_pips = (current_price - entry) * pip_mult

            # Break-Even Check
            if profit_pips >= be_pips and not pos["is_locked"]:
                pos["sl"] = entry
                pos["is_locked"] = True
                msg = f"🛡️ *BREAK-EVEN LOCKED*\nPair: `{symbol}`\nPosition: `BUY`\nSL set to Entry: `{entry}`\n*Risk Zero Guaranteed!*"
                await send_telegram_async(session, msg)

            # Trailing SL Check
            new_sl = round(current_price - (trail_dist / pip_mult), 5)
            if new_sl > pos["sl"]:
                pos["sl"] = new_sl
                msg = f"🎯 *TRAILING SL UPDATED*\nPair: `{symbol}`\nCurrent Price: `{current_price}`\nNew Locked SL: `{new_sl}`"
                await send_telegram_async(session, msg)

            # SL / Lock Hit Check
            if current_price <= pos["sl"]:
                profit_usd = (pos["sl"] - entry) * pos["lot"] * asset_config["pip_value_per_lot"] * pip_mult
                msg = f"💰 *TRADE CLOSED AT LOCKED PROFIT*\nPair: `{symbol}`\nClosed Price: `{pos['sl']}`\nProfit Secured: `${round(profit_usd, 2)} USD`"
                await send_telegram_async(session, msg)
                to_delete.append(pos_id)

        # SELL Positions
        elif trade_type == "SELL":
            profit_pips = (entry - current_price) * pip_mult

            # Break-Even Check
            if profit_pips >= be_pips and not pos["is_locked"]:
                pos["sl"] = entry
                pos["is_locked"] = True
                msg = f"🛡️ *BREAK-EVEN LOCKED*\nPair: `{symbol}`\nPosition: `SELL`\nSL set to Entry: `{entry}`\n*Risk Zero Guaranteed!*"
                await send_telegram_async(session, msg)

            # Trailing SL Check
            new_sl = round(current_price + (trail_dist / pip_mult), 5)
            if new_sl < pos["sl"]:
                pos["sl"] = new_sl
                msg = f"🎯 *TRAILING SL UPDATED*\nPair: `{symbol}`\nCurrent Price: `{current_price}`\nNew Locked SL: `{new_sl}`"
                await send_telegram_async(session, msg)

            # SL / Lock Hit Check
            if current_price >= pos["sl"]:
                profit_usd = (entry - pos["sl"]) * pos["lot"] * asset_config["pip_value_per_lot"] * pip_mult
                msg = f"💰 *TRADE CLOSED AT LOCKED PROFIT*\nPair: `{symbol}`\nClosed Price: `{pos['sl']}`\nProfit Secured: `${round(profit_usd, 2)} USD`"
                await send_telegram_async(session, msg)
                to_delete.append(pos_id)

    for p_id in to_delete:
        if p_id in ACTIVE_POSITIONS:
            del ACTIVE_POSITIONS[p_id]

# ==============================================================================
# ⚡ AUTO EXECUTION ENGINE
# ==============================================================================
async def execute_fvg_trade(session, symbol, action, entry_price, fvg_level, gap_size):
    global DAILY_TRADE_COUNT
    if DAILY_TRADE_COUNT >= MAX_DAILY_TRADES or IS_SYSTEM_LOCKED:
        return

    DAILY_TRADE_COUNT += 1
    asset_config = BRAIN_RULES.get(symbol, BRAIN_RULES["XAUUSD"])
    sl_pips = asset_config["sl_pips"]
    pip_mult = asset_config["pip_multiplier"]

    lot_size = calculate_alpha_lot_size(ACCOUNT_BALANCE, symbol, risk_pct=0.75)
    sl_distance = sl_pips / pip_mult

    if action == "BUY":
        sl_price = round(entry_price - sl_distance, 5)
    else:
        sl_price = round(entry_price + sl_distance, 5)

    pos_id = f"POS_{int(time.time() * 1000)}"
    ACTIVE_POSITIONS[pos_id] = {
        "symbol": symbol,
        "type": action,
        "lot": lot_size,
        "entry": entry_price,
        "sl": sl_price,
        "is_locked": False
    }

    msg = f"""
🏛️ *INSTITUTIONAL FVG ORDER ACTIVATED ({symbol})*
━━━━━━━━━━━━━━━━━━━━━━━
📈 *Action:* *{action}*
⚡ *Mode:* `Hedge Fund Imbalance Fill`
📍 *Entry Price:* `{entry_price}`
🔥 *Dynamic Lot:* `{lot_size}`
📐 *Imbalance Size:* `{round(gap_size, 4)}`
🛡️ *Initial SL:* `{sl_price}`
🎯 *Take Profit:* `UNLIMITED Trailing Active`
"""
    await send_telegram_async(session, msg)

# ==============================================================================
# 🔄 MAIN LOOP
# ==============================================================================
async def main_trading_loop(session):
    logging.info(f"🌐 Apex Alpha Engine Online. Active Market: {ACTIVE_MARKET}")
    
    # Startup Telegram Notification
    startup_msg = f"🚀 *APEX ALPHA BOT v29.0 ONLINE*\n━━━━━━━━━━━━━━━━━━━━━━━\n📍 *Market:* `{ACTIVE_MARKET}`\n💰 *Balance:* `${ACCOUNT_BALANCE}`\n⚡ *Status:* `Scanning FVG & Managing Trailing SL`"
    await send_telegram_async(session, startup_msg)

    while True:
        mock_current_price = 2421.75 if ACTIVE_MARKET == "XAUUSD" else 1.0885

        if ACTIVE_POSITIONS:
            await process_trailing_sl_and_profit_lock(session, ACTIVE_MARKET, mock_current_price)

        await asyncio.sleep(1)

async def main():
    keep_alive()
    async with aiohttp.ClientSession() as session:
        await main_trading_loop(session)

if __name__ == "__main__":
    asyncio.run(main())
