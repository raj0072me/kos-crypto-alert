"""
binance_client.py
-----------------
Free Binance Public API client — no API key required.
Provides live prices (24hr ticker), candlestick/OHLCV data, and coin search/autocomplete.
"""

import requests
import threading
import time

BINANCE_BASE_URL = "https://api.binance.com/api/v3"


class BinanceClient:
    """
    Wrapper around the Binance public REST API.
    No authentication or API key needed.
    """

    EXCHANGE_INFO_CACHE_DURATION = 3600  # seconds (1 hour)

    def __init__(self):
        self._usdt_symbols_info = []      # List of symbol info dicts for USDT pairs
        self._exchange_info_last_updated = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Internal: Exchange Info (cached)
    # ------------------------------------------------------------------

    def _ensure_exchange_info(self) -> bool:
        """Load and cache the list of all active USDT trading pairs from Binance."""
        now = time.time()
        if self._usdt_symbols_info and (now - self._exchange_info_last_updated < self.EXCHANGE_INFO_CACHE_DURATION):
            return True

        try:
            resp = requests.get(f"{BINANCE_BASE_URL}/exchangeInfo", timeout=15)
            resp.raise_for_status()
            data = resp.json()
            symbols = data.get("symbols", [])
            with self._lock:
                self._usdt_symbols_info = [
                    s for s in symbols
                    if s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING"
                ]
                self._exchange_info_last_updated = time.time()
            print(f"[Binance] Exchange info cached: {len(self._usdt_symbols_info)} active USDT pairs.")
            return True
        except Exception as e:
            print(f"[Binance] Error fetching exchange info: {e}")
            return False

    # ------------------------------------------------------------------
    # Search / Autocomplete
    # ------------------------------------------------------------------

    def search_coins(self, query: str) -> list:
        """
        Search for coins matching query. Returns up to 20 matches as:
        [(display_symbol, binance_symbol), ...]  e.g. [("BTC", "BTCUSDT"), ...]
        """
        self._ensure_exchange_info()
        query_upper = query.upper().strip()
        if not query_upper:
            return []

        results = []
        with self._lock:
            for sym_info in self._usdt_symbols_info:
                base = sym_info.get("baseAsset", "")
                full_symbol = sym_info.get("symbol", "")
                if base.startswith(query_upper) or full_symbol.startswith(query_upper):
                    results.append((base, full_symbol))

        # Exact prefix first, then by length
        results.sort(key=lambda x: (not x[0].startswith(query_upper), len(x[0])))
        return results[:20]

    def validate_symbol(self, binance_symbol: str) -> bool:
        """Check if a Binance trading pair exists and is active."""
        self._ensure_exchange_info()
        with self._lock:
            return any(s.get("symbol") == binance_symbol for s in self._usdt_symbols_info)

    def get_display_symbol(self, binance_symbol: str) -> str:
        """Return base asset from a Binance symbol (e.g. 'BTCUSDT' -> 'BTC')."""
        # Strip USDT suffix
        if binance_symbol.endswith("USDT"):
            return binance_symbol[:-4]
        return binance_symbol

    # ------------------------------------------------------------------
    # Live Prices
    # ------------------------------------------------------------------

    def get_all_tickers_24hr(self, binance_symbols: list) -> dict:
        """
        Fetch 24hr ticker stats for all watched symbols in ONE request.
        Returns: {symbol: {price, change_pct, high, low, volume, quote_volume}}
        """
        if not binance_symbols:
            return {}

        results = {}
        try:
            # Fetch all tickers at once (one request, no rate limit concerns)
            resp = requests.get(f"{BINANCE_BASE_URL}/ticker/24hr", timeout=15)
            resp.raise_for_status()
            all_tickers = resp.json()
            symbol_set = set(binance_symbols)
            for ticker in all_tickers:
                sym = ticker.get("symbol")
                if sym in symbol_set:
                    try:
                        results[sym] = {
                            "price": float(ticker["lastPrice"]),
                            "change_pct": float(ticker["priceChangePercent"]),
                            "high": float(ticker["highPrice"]),
                            "low": float(ticker["lowPrice"]),
                            "volume": float(ticker["volume"]),
                            "quote_volume": float(ticker["quoteVolume"]),
                        }
                    except (KeyError, ValueError):
                        pass
        except Exception as e:
            print(f"[Binance] Error fetching all tickers: {e}")
            # Fallback: individual calls for each symbol
            for sym in binance_symbols:
                data = self._get_single_ticker(sym)
                if data:
                    results[sym] = data

        return results

    def _get_single_ticker(self, binance_symbol: str) -> dict | None:
        """Fetch 24hr ticker for a single symbol (fallback)."""
        try:
            resp = requests.get(
                f"{BINANCE_BASE_URL}/ticker/24hr",
                params={"symbol": binance_symbol},
                timeout=10
            )
            resp.raise_for_status()
            t = resp.json()
            return {
                "price": float(t["lastPrice"]),
                "change_pct": float(t["priceChangePercent"]),
                "high": float(t["highPrice"]),
                "low": float(t["lowPrice"]),
                "volume": float(t["volume"]),
                "quote_volume": float(t["quoteVolume"]),
            }
        except Exception as e:
            print(f"[Binance] Error fetching ticker for {binance_symbol}: {e}")
            return None

    # ------------------------------------------------------------------
    # Candlestick / OHLCV Data
    # ------------------------------------------------------------------

    def get_klines(self, binance_symbol: str, interval: str = "1d", limit: int = 90) -> list | None:
        """
        Fetch OHLCV candlestick data from Binance.

        Args:
            binance_symbol: e.g. "BTCUSDT"
            interval: "1m", "5m", "15m", "1h", "4h", "1d", "1w"
            limit: number of candles (max 1000)

        Returns:
            List of dicts: [{time (unix sec), open, high, low, close, volume}, ...]
            or None on error.
        """
        try:
            resp = requests.get(
                f"{BINANCE_BASE_URL}/klines",
                params={"symbol": binance_symbol, "interval": interval, "limit": limit},
                timeout=20
            )
            resp.raise_for_status()
            raw = resp.json()
            candles = []
            for k in raw:
                candles.append({
                    "time":   k[0] / 1000,      # ms -> seconds
                    "open":   float(k[1]),
                    "high":   float(k[2]),
                    "low":    float(k[3]),
                    "close":  float(k[4]),
                    "volume": float(k[5]),
                })
            return candles if candles else None
        except Exception as e:
            print(f"[Binance] Error fetching klines for {binance_symbol} ({interval}): {e}")
            return None
