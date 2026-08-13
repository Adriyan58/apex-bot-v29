# ==============================================================================
# APEX ALPHA MASTER PRODUCTION BOT v39.1 (CLEAN & SECURED)
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

# ==============================================================================
# 🛠️ TELEGRAM & BROKER CONFIGURATION (Loaded from Environment Variables)
# ==============================================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

GOAT_FUNDED_URL = os.getenv("GOAT_FUNDED_URL", "https://mt5-1.goatfundedtrader.com")
GOAT_LOGIN = os.getenv("GOAT_LOGIN", "")
GOAT_PASSWORD = os.getenv("GOAT_PASSWORD", "")
GOAT_EMAIL = os.getenv("GOAT_EMAIL", "")

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# PORT setup for Render
PORT = int(os.getenv("PORT", 5000))

# ==============================================================================
# 🧠 IPDA BRAIN CONFIGURATION
# ==============================================================================
JSON_BRAIN_CONFIG = """
{
    "XAUUSD": {
        "asset_type": "COMMODITY",
        "pip_value_per_lot": 10.0,
        "pip_multiplier": 0.1,
        "sl_pips": 15,
        "min_fvg_size_pips": 1.5,
        "break_even_pips": 10.0,
        "trailing_distance_pips": 8.0,
        "ipda_lookback_candles": 20
    },
    "NAS100": {
        "asset_type": "INDEX",
        "pip_value_per_lot": 1.0,
        "pip_multiplier": 1.0,
        "sl_pips": 35,
        "min_fvg_size_pips": 5.0,
        "break_even_pips": 25.0,
        "trailing_distance_pips": 20.0,
        "ipda_lookback_candles": 20
    }
}
"""

ACTIVE_MARKETS = ["XAUUSD", "NAS100"]
MAX_DAILY_TRADES = 4
DAILY_TRADE_COUNT = 0
LAST_RESET_DAY = datetime.datetime.now(datetime.timezone.utc).day
ACTIVE_POSITIONS = {}
LATEST_LIVE_PRICES = {"XAUUSD": 0.0, "NAS100": 0.0}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
BRAIN_RULES = json.loads(JSON_BRAIN_CONFIG)

# ==============================================================================
# 🏛️ IPDA REAL-TIME ALGORITHM ENGINE
# ==============================================================================
class IPDAEngine:
    @staticmethod
    def is_ipda_killzone():
        now_utc = datetime.datetime.now(datetime.timezone.utc).time()
        london_start, london_end = datetime.time(7, 0), datetime.time(10, 0)
        ny_start, ny_end = datetime.time(12, 0), datetime.time(15, 0)
        return (london_start <= now_utc <= london_end) or (ny_start <= now_utc <= ny_end)

    @staticmethod
    def detect_fvg_pending_level(highs, lows, closes):
        if len(highs) < 3 or len(lows) < 3:
            return None, 0.0, 0.0

        # Bullish FVG
        if lows[-1] > highs[-3]:
            fvg_gap = lows[-1] - highs[-3]
            pending_price = highs[-3]
            return "BUY_LIMIT", fvg_gap, pending_price

        # Bearish FVG
        if highs[-1] < lows[-3]:
            fvg_gap = lows[-3] - highs[-1]
            pending_price = lows[-3]
            return "SELL_LIMIT", fvg_gap, pending_price

        return None, 0.0, 0.0

def calculate_dynamic_lot_size(live_balance, symbol="XAUUSD", risk_pct=0.5):
    asset_config = BRAIN_RULES.get(symbol, BRAIN_RULES["XAUUSD"])
    sl_pips = asset_config["sl_pips"]
    pip_val = asset_config["pip_value_per_lot"]

    risk_usd = live_balance * (risk_pct / 100.0)
    calculated_lot = risk_usd / (sl_pips * pip_val)
    return max(round(calculated_lot, 2), 0.01)

# ==============================================================================
# 📱 TELEGRAM NOTIFICATION SYSTEM
# ==============================================================================
async def send_telegram_msg(session, message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram token or Chat ID is missing. Skipping notification.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        async with session.post(url, json=payload) as resp:
            if resp.status != 200:
                logging.error(f"Telegram alert failed with status {resp.status}")
    except Exception as e:
        logging.error(f"Telegram dispatch error: {e}")

# ==============================================================================
# 🌐 GOAT FUNDED TRADER WEB API BRIDGE
# ==============================================================================
class GoatFundedWebAPI:
    def __init__(self, session):
        self.session = session
        self.auth_token = None

    async def authenticate(self):
        url = f"{GOAT_FUNDED_URL}/api/v1/auth/login"
        payload = {"email": GOAT_EMAIL, "password": GOAT_PASSWORD, "login": GOAT_LOGIN}
        try:
            async with self.session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.auth_token = data.get("token")
                    logging.info("Successfully authenticated with Goat Funded Trader API.")
                    return True
                else:
                    logging.error(f"Authentication failed: HTTP {resp.status}")
                    return False
        except Exception as e:
            logging.error(f"Broker connection error: {e}")
            return False

    async def place_order(self, symbol, order_type, lot_size, limit_price, sl_price, tp_price):
        if not self.auth_token:
            await self.authenticate()
        
        url = f"{GOAT_FUNDED_URL}/api/v1/trading/order"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        payload = {
            "symbol": symbol,
            "action": order_type,
            "volume": lot_size,
            "price": limit_price,
            "sl": sl_price,
            "tp": tp_price,
            "comment": "Apex IPDA Auto-Execution"
        }
        try:
            async with self.session.post(url, json=payload, headers=headers) as resp:
                if resp.status in [200, 201]:
                    res_data = await resp.json()
                    logging.info(f"Order Executed Successfully: {res_data}")
                    return True, res_data.get("order_id", "N/A")
                else:
                    logging.error(f"Execution Error: {await resp.text()}")
                    return False, None
        except Exception as e:
            logging.error(f"Broker Execution Exception: {e}")
            return False, None

# ==============================================================================
# 🌐 FLASK WEBHOOK SERVER
# ==============================================================================
app = Flask(__name__)

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ONLINE", "bot": "Apex Alpha Master IPDA Engine v39.1"}), 200

@app.route("/webhook", methods=["POST"])
def tradingview_webhook():
    global LATEST_LIVE_PRICES
    try:
        data = request.get_json(force=True)
        symbol = data.get("symbol", "XAUUSD").upper()
        price = float(data.get("price", 0.0))
        
        if symbol in LATEST_LIVE_PRICES and price > 0:
            LATEST_LIVE_PRICES[symbol] = price
            logging.info(f"Updated live price for {symbol}: {price}")
            return jsonify({"status": "SUCCESS", "message": f"Updated {symbol} price"}), 200
        return jsonify({"status": "IGNORED", "reason": "Invalid payload"}), 400
    except Exception as e:
        logging.error(f"Webhook processing error: {e}")
        return jsonify({"status": "ERROR", "message": str(e)}), 500

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# ==============================================================================
# 🔄 MAIN ASYNC ENGINE LOOP
# ==============================================================================
async def main_trading_loop():
    global DAILY_TRADE_COUNT, LAST_RESET_DAY
    
    async with aiohttp.ClientSession() as session:
        broker_api = GoatFundedWebAPI(session)
        await send_telegram_msg(session, "🚀 <b>Apex Alpha Master Bot Engine Started on Render!</b>")

        while True:
            try:
                # 1. Reset Daily Counter at UTC Midnight
                current_day = datetime.datetime.now(datetime.timezone.utc).day
                if current_day != LAST_RESET_DAY:
                    DAILY_TRADE_COUNT = 0
                    LAST_RESET_DAY = current_day
                    logging.info("Daily trade counter reset.")

                # 2. Check Daily Limits & Killzone
                if DAILY_TRADE_COUNT >= MAX_DAILY_TRADES:
                    await asyncio.sleep(60)
                    continue

                if not IPDAEngine.is_ipda_killzone():
                    await asyncio.sleep(30)
                    continue

                # 3. Market Scan
                for symbol in ACTIVE_MARKETS:
                    live_price = LATEST_LIVE_PRICES.get(symbol, 0.0)
                    if live_price <= 0:
                        continue

                    # Mock Market Array Structure (In production, replace with real candle history)
                    highs = [live_price - 2.0, live_price - 1.0, live_price + 3.0]
                    lows = [live_price - 4.0, live_price + 1.0, live_price + 0.5]
                    closes = [live_price - 1.5, live_price, live_price + 2.0]

                    order_type, fvg_gap, pending_price = IPDAEngine.detect_fvg_pending_level(highs, lows, closes)
                    
                    config = BRAIN_RULES.get(symbol)
                    min_gap = config["min_fvg_size_pips"] * config["pip_multiplier"]

                    if order_type and fvg_gap >= min_gap:
                        lot_size = calculate_dynamic_lot_size(100000, symbol) # Base balance $100k
                        
                        if order_type == "BUY_LIMIT":
                            sl = pending_price - (config["sl_pips"] * config["pip_multiplier"])
                            tp = pending_price + (config["sl_pips"] * 3 * config["pip_multiplier"])
                        else:
                            sl = pending_price + (config["sl_pips"] * config["pip_multiplier"])
                            tp = pending_price - (config["sl_pips"] * 3 * config["pip_multiplier"])

                        success, order_id = await broker_api.place_order(symbol, order_type, lot_size, pending_price, sl, tp)
                        
                        if success:
                            DAILY_TRADE_COUNT += 1
                            msg = (
                                f"🎯 <b>IPDA ORDER EXECUTED</b>\n"
                                f"<b>Symbol:</b> {symbol}\n"
                                f"<b>Type:</b> {order_type}\n"
                                f"<b>Lot:</b> {lot_size}\n"
                                f"<b>Entry:</b> {pending_price}\n"
                                f"<b>SL:</b> {sl} | <b>TP:</b> {tp}\n"
                                f"<b>Order ID:</b> {order_id}"
                            )
                            await send_telegram_msg(session, msg)

            except Exception as e:
                logging.error(f"Error in trading loop: {e}")

            await asyncio.sleep(10)

# ==============================================================================
# 🚀 INITIALIZATION
# ==============================================================================
if __name__ == "__main__":
    # Flask Server Start (Background Thread)
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Asyncio Trading Loop Start
    asyncio.run(main_trading_loop())
