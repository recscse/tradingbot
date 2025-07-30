# services/sector_mapping.py

from typing import Dict, Optional, List


SECTOR_STOCKS = {
    "BANKING": [
        "HDFCBANK",
        "SBIN",
        "SBI",  # Added for SBI (different from SBILIFE)
        "ICICIBANK",
        "ICICI",  # Added FNO symbol
        "KOTAKBANK",
        "AXISBANK",
        "INDUSINDBK",
        "BANDHANBNK",
        "FEDERALBNK",
        "RBLBANK",
        "AUBANK",
        "IDFCFIRSTB",
        "PNB",
        "YESBANK",
        "BANKBARODA",  # Added
        "BANKINDIA",  # Added
        "CANBK",  # Added
        "INDIANB",  # Added
        "UNIONBANK",  # Added
    ],
    "IT": [
        "TCS",
        "INFY",
        "WIPRO",
        "HCLTECH",
        "HCL",  # Added FNO symbol
        "TECHM",
        "LTIM",
        "COFORGE",
        "PERSISTENT",
        "MPHASIS",
        "BSOFT",  # Added
        "CYIENT",  # Added
        "KPITTECH",  # Added
        "OFSS",  # Added
        "TATAELXSI",  # Added
        "TATATECH",  # Added
    ],
    "PHARMA": [
        "SUNPHARMA",
        "DRREDDY",
        "CIPLA",
        "DIVISLAB",
        "LUPIN",
        "BIOCON",
        "APOLLOHOSP",
        "ALKEM",
        "AUROPHARMA",
        "ZYDUSLIFE",
        "GLENMARK",
        "GRANULES",  # Added
        "LAURUSLABS",  # Added
        "MANKIND",  # Added
        "PPLPHARMA",  # Added
        "SYNGENE",  # Added
        "TORNTPHARM",  # Added
    ],
    "AUTO": [
        "MARUTI",
        "TATAMOTORS",
        "M&M",
        "EICHERMOT",
        "BAJAJ-AUTO",
        "HEROMOTOCO",
        "TVSMOTOR",
        "ASHOKLEY",
        "BALKRISIND",
        "BOSCHLTD",
        "MOTHERSON",  # Added
        "SONACOMS",  # Added
        "TIINDIA",  # Added
        "UNOMINDA",  # Added
    ],
    "ENERGY": [
        "RELIANCE",
        "ONGC",
        "BPCL",
        "IOC",
        "POWERGRID",
        "NTPC",
        "TATAPOWER",
        "GAIL",
        "ADANIGREEN",
        "OIL",
        "ADANIENSOL",  # Added
        "IREDA",  # Added
        "JSWENERGY",  # Added
        "NHPC",  # Added
        "PFC",  # Added
        "RECLTD",  # Added
        "SJVN",  # Added
        "TORNTPOWER",  # Added
        "IEX",  # Added - Indian Energy Exchange
    ],
    "CONSUMER": [
        "HINDUNILVR",
        "ITC",
        "NESTLEIND",
        "BRITANNIA",
        "TITAN",
        "ASIANPAINT",
        "DABUR",
        "COLPAL",
        "GODREJCP",
        "MARICO",
        "TATACONSUM",
        "AMBER",  # Added
        "ASTRAL",  # Added
        "BLUESTARCO",  # Added
        "CROMPTON",  # Added
        "DIXON",  # Added
        "HAVELLS",  # Added
        "KALYANKJIL",  # Added
        "NYKAA",  # Added
        "PAGEIND",  # Added
        "PATANJALI",  # Added
        "POLYCAB",  # Added
        "VOLTAS",  # Added
    ],
    "METALS": [
        "TATASTEEL",
        "JSWSTEEL",
        "JSW",  # Added FNO symbol for JSW Steel
        "HINDALCO",
        "VEDL",
        "COALINDIA",
        "NMDC",
        "NATIONALUM",
        "JINDALSTEL",
        "SAIL",
        "HINDZINC",  # Added
        "JSL",  # Added
        "HINDCOPPER",  # Added
    ],
    "FMCG": [
        "HINDUNILVR",
        "ITC",
        "NESTLEIND",
        "BRITANNIA",
        "DABUR",
        "COLPAL",
        "GODREJCP",
        "MARICO",
        "TATACONSUM",
        "UNITDSPR",  # Added
    ],
    "FINANCIAL_SERVICES": [
        "HDFCLIFE",
        "HDFC",
        "BAJFINANCE",
        "BAJAJFINSV",
        "ICICIPRULI",
        "SBILIFE",
        "ICICIGI",
        "CHOLAFIN",
        "MUTHOOTFIN",
        "PEL",
        "SHRIRAMFIN",
        "HDFCAMC",
        "ABCAPITAL",  # Added
        "ANGELONE",  # Added
        "IIFL",  # Added
        "JIOFIN",  # Added
        "LICHSGFIN",  # Added
        "LICI",  # Added
        "LIC",  # Added
        "LTF",  # Added
        "M&MFIN",  # Added
        "MANAPPURAM",  # Added
        "MFSL",  # Added
        "PAYTM",  # Added
        "POLICYBZR",  # Added
        "POONAWALLA",  # Added
        "SBICARD",  # Added
    ],
    "REALTY": [
        "DLF",
        "GODREJPROP",
        "OBEROIRLTY",
        "PHOENIXLTD",
        "LODHA",
        "PRESTIGE",  # Added
    ],
    "CEMENT": [
        "ULTRACEMCO",
        "GRASIM",
        "AMBUJACEM",
        "ACC",
        "SHREECEM",
        "DALBHARAT",  # Added
    ],
    "CHEMICALS": [
        "PIIND",
        "SRF",
        "AARTIIND",
        "TATACHEM",
        "CHAMBLFERT",  # Added
        "PIDILITIND",  # Added
        "SUPREMEIND",  # Added
        "UPL",  # Added
    ],
    "OIL_GAS": [
        "ONGC",
        "IOC",
        "BPCL",
        "GAIL",
        "OIL",
        "RELIANCE",
        "IGL",
        "MGL",
        "PETRONET",
        "HINDPETRO",  # Added
    ],
    "TELECOM": [
        "BHARTIARTL",
        "IDEA",
        "TATACOMM",
        "HFCL",  # Added
        "INDUSTOWER",  # Added
    ],
    "POWER": [
        "POWERGRID",
        "NTPC",
        "TATAPOWER",
        "ADANIGREEN",
        "CESC",  # Added
        "CGPOWER",  # Added
        "HUDCO",  # Added
    ],
    "INFRASTRUCTURE": [
        "LT",  # Added (Larsen & Toubro)
        "ADANIPORTS",
        "SEZ",  # Added (Adani Ports SEZ symbol)
        "IRCTC",
        "NBCC",
        "GMRAIRPORT",  # Added
        "IRB",  # Added
        "NCC",  # Added
        "RVNL",  # Added
        "TITAGARH",  # Added
    ],
    "LOGISTICS": [
        "CONCOR",
        "DELHIVERY",
    ],
    "DEFENSE": [
        "BEL",
        "HAL",
        "BDL",
        "MAZDOCK",  # Added
    ],
    "HEALTHCARE": [
        "APOLLOHOSP",
        "FORTIS",
        "MAXHEALTH",
    ],
    "INSURANCE": [
        "HDFCLIFE",
        "ICICIPRULI",
        "SBILIFE",
        "ICICIGI",
    ],
    "PAINTS": [
        "ASIANPAINT",
    ],
    "RETAIL": [
        "DMART",
        "TRENT",
        "VBL",
        "ABFRL",
    ],
    "TRAVEL_LEISURE": [
        "INDIGO",
        "INDHOTEL",  # Added
    ],
    "INDUSTRIAL": [
        "ABB",  # Added
        "APLAPOLLO",  # Added
        "BHARATFORG",  # Added
        "BHEL",  # Added
        "CUMMINSIND",  # Added
        "EXIDEIND",  # Added
        "KEI",  # Added
        "SIEMENS",  # Added
    ],
    "FINANCIAL_TECH": [
        "BSE",  # Added
        "CAMS",  # Added
        "CDSL",  # Added
        "KFINTECH",  # Added
        "MCX",  # Added
    ],
    "FOOD": [
        "JUBLFOOD",  # Added
    ],
    "RENEWABLE_ENERGY": [
        "INOXWIND",  # Added
        "SOLARINDS",  # Added
    ],
    "DIVERSIFIED": [
        "ADANIENT",  # Added
        "ETERNAL",  # Added
    ],
    "SPECIALTY": [
        "KAYNES",  # Added
        "PGEL",  # Added
        "NAUKRI",  # Added
        "PNBHOUSING",  # Added
        "IRFC",  # Added
    ],
    "INDICES": [
        "NIFTY",
        "BANKNIFTY",
        "FINNIFTY",
        "MIDCPNIFTY",
        "NIFTY-NEXT50",  # Added
    ],
}

SYMBOL_TO_SECTOR = {
    symbol: sector for sector, syms in SECTOR_STOCKS.items() for symbol in syms
}


def get_sector_stocks(sector: str) -> List[str]:
    """
    Get the list of stocks for a given sector.

    Args:
        sector (str): The sector name.

    Returns:
        List[str]: List of stock symbols in the specified sector.
    """
    return SECTOR_STOCKS.get(sector.upper(), [])


def get_all_sectors() -> List[str]:
    """
    Get a list of all sectors.

    Returns:
        List[str]: List of all sector names.
    """
    return list(SECTOR_STOCKS.keys())


def get_sector_for_stock(symbol: str) -> Optional[str]:
    """
    Get the sector for a given stock symbol.

    Args:
        symbol (str): The stock symbol.

    Returns:
        Optional[str]: The sector name if found, otherwise None.
    """
    return SYMBOL_TO_SECTOR.get(symbol.upper())


def get_sector_mapping() -> Dict[str, List[str]]:
    """
    Get a mapping of all sectors to their respective stock symbols.

    Returns:
        Dict[str, List[str]]: A dictionary where the keys are sector names
        and the values are lists of stock symbols in each sector.
    """
    return SECTOR_STOCKS
