# services/sector_utils.py

from services.sector_mapping import SECTOR_STOCKS

# Build a reverse symbol -> sector mapping
SYMBOL_TO_SECTOR = {}
for sector, symbols in SECTOR_STOCKS.items():
    for symbol in symbols:
        SYMBOL_TO_SECTOR[symbol] = sector


def get_sector_for_symbol(symbol: str) -> str:
    """Get sector for a symbol. Returns 'UNKNOWN' if not found."""
    symbol = symbol.upper()
    return SYMBOL_TO_SECTOR.get(symbol, "UNKNOWN")


def get_symbols_for_sector(sector: str) -> list:
    """Get all stock symbols for a sector. Returns empty list if not found."""
    return SECTOR_STOCKS.get(sector.upper(), [])


def get_all_sectors() -> list:
    return list(SECTOR_STOCKS.keys())
