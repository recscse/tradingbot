import logging
from fastapi import APIRouter, Request
from pathlib import Path
import json
from datetime import datetime
from collections import defaultdict

from utils.instrument_key_cache import save_instrument_keys

router = APIRouter()
logger = logging.getLogger("stock_router")

# Global Cache for performance
_INSTRUMENT_CACHE = {
    "instruments": None,
    "top_stocks": None,
    "last_loaded": None,
    "instrument_index": None
}
CACHE_TIMEOUT_SECONDS = 3600  # Cache instruments for 1 hour

def _get_cached_data():
    now = datetime.now()
    top_stocks_path = Path("data/top_stocks.json")
    instrument_path = Path("data/upstox_instruments.json")
    
    if not top_stocks_path.exists() or not instrument_path.exists():
        logger.error("❌ Missing required JSON files.")
        return None, None, None

    # Check if cache is still valid
    if (_INSTRUMENT_CACHE["last_loaded"] and 
        (now - _INSTRUMENT_CACHE["last_loaded"]).total_seconds() < CACHE_TIMEOUT_SECONDS and
        _INSTRUMENT_CACHE["instruments"] is not None):
        return _INSTRUMENT_CACHE["top_stocks"], _INSTRUMENT_CACHE["instruments"], _INSTRUMENT_CACHE["instrument_index"]

    try:
        start_time = datetime.now()
        logger.info("📂 Loading instruments and top stocks from JSON...")
        
        with open(top_stocks_path, "r", encoding="utf-8") as f:
            top_stocks = json.load(f).get("securities", [])

        with open(instrument_path, "r", encoding="utf-8") as f:
            all_instruments = json.load(f)
            
        # Index instruments by (exchange, symbol)
        instrument_index = defaultdict(list)
        for instr in all_instruments:
            if not instr.get("instrument_key"):
                continue

            # Skip expired instruments
            expiry = instr.get("expiry")
            if expiry and datetime.fromtimestamp(expiry / 1000) < now:
                continue

            exchange = instr.get("exchange", "").upper()
            added_symbols = set()
            for field in ("trading_symbol", "asset_symbol", "underlying_symbol"):
                sym = instr.get(field, "").strip().upper()
                if sym and sym not in added_symbols:
                    instrument_index[(exchange, sym)].append(instr)
                    added_symbols.add(sym)

        _INSTRUMENT_CACHE["top_stocks"] = top_stocks
        _INSTRUMENT_CACHE["instruments"] = all_instruments
        _INSTRUMENT_CACHE["instrument_index"] = instrument_index
        _INSTRUMENT_CACHE["last_loaded"] = now
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Loaded {len(all_instruments)} instruments in {elapsed:.2f}s")
        
        return top_stocks, all_instruments, instrument_index
        
    except Exception as e:
        logger.error(f"❌ Failed to load or parse files: {e}")
        return None, None, None


@router.get("/api/stocks/top")
def get_top_stock_details(request: Request):
    top_stocks, _, instrument_index = _get_cached_data()
    
    if top_stocks is None or instrument_index is None:
        return {"data": {}, "error": "Failed to load stock data."}

    now = datetime.now()

    grouped = {}
    instrument_keys_set = set()

    for stock in top_stocks:
        symbol = stock.get("symbol", "").strip().upper()
        exchange = stock.get("exchange", "").strip().upper()
        name = stock.get("name", "")

        matches = instrument_index.get((exchange, symbol), [])
        if not matches:
            logger.warning(f"⚠️ No instruments found for {symbol} on {exchange}")
            continue

        instrument_map = defaultdict(list)
        for instr in matches:
            itype = (instr.get("instrument_type") or "").upper()
            instrument_map[itype].append(instr)

        data = {
            "name": name,
            "spot": None,
            "futures": [],
            "options": {"call": [], "put": []},
        }

        # Spot instrument (EQ or INDEX)
        for itype in ["EQ", "INDEX"]:
            for instr in instrument_map.get(itype, []):
                payload = prepare_stock_payload(stock, instr, name)
                data["spot"] = payload
                instrument_keys_set.add(payload["instrument_key"])
                break

        # Futures instruments
        for instr in instrument_map.get("FUT", []):
            payload = prepare_stock_payload(stock, instr, name)
            data["futures"].append(payload)
            instrument_keys_set.add(payload["instrument_key"])

        # Options (Call & Put)
        options = instrument_map.get("CE", []) + instrument_map.get("PE", [])
        spot_ltp = (
            data["spot"].get("last_price") or data["spot"].get("close_price")
            if data["spot"]
            else None
        )

        if not spot_ltp:
            strikes = [
                opt.get("strike_price") for opt in options if opt.get("strike_price")
            ]
            if strikes:
                spot_ltp = sum(strikes) / len(strikes)

        if spot_ltp:
            for instr in options:
                strike = instr.get("strike_price")
                if strike and abs(strike - spot_ltp) <= 20:
                    payload = prepare_stock_payload(stock, instr, name)
                    if (instr.get("instrument_type") or "").upper() == "CE":
                        data["options"]["call"].append(payload)
                    else:
                        data["options"]["put"].append(payload)
                    instrument_keys_set.add(payload["instrument_key"])

        grouped[symbol] = data

    # ✅ Save instrument keys to file
    try:
        instrument_keys_list = sorted(list(instrument_keys_set))
        save_instrument_keys(instrument_keys_list)
        logger.info(
            f"💾 Saved {len(instrument_keys_list)} instrument keys to /tmp/today_instrument_keys.json"
        )
    except Exception as e:
        logger.warning(f"⚠️ Failed to save instrument keys: {e}")

    logger.info(f"✅ Final grouped stock response ready: {len(grouped)} stocks")
    return {"data": grouped}


def prepare_stock_payload(stock, instr, name):
    return {
        "name": name,
        "display_name": (
            f"{name} ({instr.get('trading_symbol')})"
            if instr.get("trading_symbol") not in name
            else name
        ),
        "symbol": stock.get("symbol", ""),
        "exchange": stock.get("exchange", ""),
        "segment": instr.get("segment"),
        "expiry": instr.get("expiry"),
        "instrument_type": (instr.get("instrument_type") or "").upper(),
        "is_option": (instr.get("instrument_type") or "") in ["CE", "PE"],
        "option_type": instr.get("instrument_type"),
        "asset_symbol": instr.get("asset_symbol"),
        "underlying_symbol": instr.get("underlying_symbol"),
        "instrument_key": instr.get("instrument_key"),
        "lot_size": instr.get("lot_size"),
        "freeze_quantity": instr.get("freeze_quantity"),
        "exchange_token": instr.get("exchange_token"),
        "minimum_lot": instr.get("minimum_lot"),
        "tick_size": instr.get("tick_size"),
        "asset_type": instr.get("asset_type"),
        "underlying_type": instr.get("underlying_type"),
        "trading_symbol": instr.get("trading_symbol"),
        "strike_price": instr.get("strike_price"),
        "qty_multiplier": instr.get("qty_multiplier"),
        "last_price": instr.get("last_price"),
        "close_price": instr.get("close_price"),
    }


# def get_default_instrument_keys():
#     from collections import defaultdict

#     top_stocks_path = Path("data/top_stocks.json")
#     instrument_path = Path("data/upstox_instruments.json")

#     if not top_stocks_path.exists() or not instrument_path.exists():
#         logger.error("❌ Missing required JSON files for instrument keys.")
#         return []

#     try:
#         with open(top_stocks_path, "r", encoding="utf-8") as f:
#             top_stocks = json.load(f).get("securities", [])

#         with open(instrument_path, "r", encoding="utf-8") as f:
#             all_instruments = json.load(f)
#     except Exception as e:
#         logger.error(f"❌ Failed to load instrument key files: {e}")
#         return []

#     now = datetime.now()
#     instrument_keys = set()

#     # Pre-index instruments by (exchange, symbol)
#     indexed = defaultdict(list)
#     for instr in all_instruments:
#         if not instr.get("instrument_key"):
#             continue

#         expiry = instr.get("expiry")
#         if expiry and datetime.fromtimestamp(expiry / 1000) < now:
#             continue

#         exchange = instr.get("exchange", "").upper()
#         for field in ("trading_symbol", "asset_symbol", "underlying_symbol"):
#             symbol = instr.get(field, "").upper()
#             if symbol:
#                 indexed[(exchange, symbol)].append(instr)

#     def normalize_type(t):
#         return (t or "").strip().upper()

#     for stock in top_stocks:
#         symbol = stock.get("symbol", "").strip().upper()
#         exchange = stock.get("exchange", "").strip().upper()

#         if not symbol or not exchange:
#             continue

#         # Handle optional aliases
#         symbol_aliases = [symbol]
#         if symbol == "CRUDEOIL":
#             symbol_aliases.append("CRUDEOILM")
#         elif symbol == "GOLD":
#             symbol_aliases.append("GOLDM")

#         # Collect all matches
#         all_matches = []
#         for alias in symbol_aliases:
#             all_matches.extend(indexed.get((exchange, alias), []))

#         if not all_matches:
#             logger.warning(f"⚠️ No instruments found for {symbol} on {exchange}")
#             continue

#         # Group by type
#         instrument_types = {
#             "EQ": [],
#             "INDEX": [],
#             "FUT": [],
#             "CE": [],
#             "PE": [],
#         }

#         for m in all_matches:
#             t = normalize_type(m.get("instrument_type"))
#             if t in instrument_types:
#                 instrument_types[t].append(m)

#         # Add EQ/INDEX/FUT always
#         for t in ["EQ", "INDEX", "FUT"]:
#             for m in instrument_types[t]:
#                 instrument_keys.add(m["instrument_key"])

#         # For CE/PE, calculate spot LTP
#         all_options = instrument_types["CE"] + instrument_types["PE"]

#         spot_ltp = None
#         for m in instrument_types["EQ"] + instrument_types["INDEX"]:
#             spot_ltp = m.get("last_price") or m.get("close_price")
#             if spot_ltp:
#                 break

#         if not spot_ltp:
#             strikes = [
#                 m.get("strike_price") for m in all_options if m.get("strike_price")
#             ]
#             if strikes:
#                 spot_ltp = sum(strikes) / len(strikes)

#         if spot_ltp:
#             for opt in all_options:
#                 strike = opt.get("strike_price") or 0
#                 if abs(strike - spot_ltp) <= 20:
#                     instrument_keys.add(opt["instrument_key"])

#     logger.info(f"✅ Final instrument keys resolved: {len(instrument_keys)}")
#     return list(instrument_keys)


def get_default_instrument_keys():
    top_stocks_path = Path("data/top_stocks.json")
    instrument_path = Path("data/upstox_instruments.json")

    if not top_stocks_path.exists() or not instrument_path.exists():
        logger.error("❌ Missing required JSON files for instrument keys.")
        return []

    try:
        with open(top_stocks_path, "r", encoding="utf-8") as f:
            top_stocks = json.load(f).get("securities", [])

        with open(instrument_path, "r", encoding="utf-8") as f:
            all_instruments = json.load(f)
    except Exception as e:
        logger.error(f"❌ Failed to load instrument key files: {e}")
        return []

    instrument_keys = set()
    now = datetime.now()

    # Index by (exchange, symbol)
    indexed = defaultdict(list)
    for instr in all_instruments:
        if not instr.get("instrument_key"):
            continue

        expiry = instr.get("expiry")
        if expiry and datetime.fromtimestamp(expiry / 1000) < now:
            continue

        exchange = instr.get("exchange", "").upper()
        for key in ("trading_symbol", "asset_symbol", "underlying_symbol"):
            symbol = instr.get(key, "").upper()
            if symbol:
                indexed[(exchange, symbol)].append(instr)

    def normalize_type(t):
        return (t or "").strip().upper()

    for stock in top_stocks:
        symbol = stock.get("symbol", "").strip().upper()
        exchange = stock.get("exchange", "").strip().upper()

        if not symbol or not exchange:
            continue

        matches = []
        for sym in [symbol]:
            matches.extend(indexed.get((exchange, sym), []))

        found = False
        for m in matches:
            t = normalize_type(m.get("instrument_type"))
            if t in ("EQ", "INDEX"):
                instrument_keys.add(m["instrument_key"])
                found = True

        if not found:
            logger.warning(f"⚠️ No EQ/INDEX instrument found for {symbol} on {exchange}")

    logger.info(f"✅ Spot instrument keys resolved: {len(instrument_keys)}")
    return list(instrument_keys)
