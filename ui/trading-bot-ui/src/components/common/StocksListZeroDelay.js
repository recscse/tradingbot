// components/common/StocksListZeroDelay.js
/**
 * ZERO-DELAY Stocks List (instrument_key-only matching)
 *
 * Behavior:
 *  - Only consider a feed entry as live for a stock when the feed's instrument_key
 *    matches the stock.instrument_key (exact), OR when the feed key is a pipe-separated
 *    string where the RHS (human name) equals the stock.instrument_key RHS.
 *  - Pure compute, batch setState inside effect (no setState during render).
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Box,
  Typography,
  Chip,
  Tooltip,
  IconButton,
  Alert,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  SignalWifi4Bar,
  SignalWifi0Bar,
  Speed,
  Refresh,
} from "@mui/icons-material";
import { green, red, grey } from "@mui/material/colors";
import { useZeroDelayMarketData } from "../../hooks/useZeroDelayMarketData";

// helpers
const safeString = (v) => (v === undefined || v === null ? "" : String(v));
const rhsFromPipe = (s) => {
  if (!s || typeof s !== "string") return s;
  const parts = s
    .split("|")
    .map((p) => p.trim())
    .filter(Boolean);
  return parts.length > 1 ? parts[parts.length - 1] : s;
};

// Strict matching by instrument_key
const matchByInstrumentKey = (marketData, stockInstrumentKey) => {
  if (!marketData || !stockInstrumentKey) return null;

  // 1) direct key exists in feed
  if (marketData[stockInstrumentKey]) {
    return {
      key: stockInstrumentKey,
      entry: marketData[stockInstrumentKey],
      reason: "direct_key",
    };
  }

  // 2) some feeds use RHS of pipe in key or instrument_key inside entry; try to find
  const targetRhs = rhsFromPipe(stockInstrumentKey).toLowerCase();

  const keys = Object.keys(marketData);
  for (let i = 0; i < keys.length; i++) {
    const sk = keys[i];
    // if feed key equals the instrument_token or contains instrument_key as part
    if (sk === stockInstrumentKey) {
      return { key: sk, entry: marketData[sk], reason: "exact_key_match_loop" };
    }
    // attempt RHS match: e.g. feed key = 'NSE_INDEX|Nifty 50', stock.instrument_key = 'NSE_INDEX|Nifty 50' or 'Nifty 50'
    const skRhs = rhsFromPipe(sk).toLowerCase();
    if (skRhs === targetRhs) {
      return { key: sk, entry: marketData[sk], reason: "rhs_key_match" };
    }

    // also inspect entry.instrument_key or entry.instrument_key-like fields
    const entry = marketData[sk];
    if (entry) {
      const entryInst = safeString(
        entry.instrument_key ||
          entry.instrumentKey ||
          entry.instrument ||
          entry.symbol
      );
      if (entryInst && entryInst === stockInstrumentKey) {
        return { key: sk, entry, reason: "entry_instrument_key_exact" };
      }
      const entryRhs = rhsFromPipe(entryInst).toLowerCase();
      if (entryRhs === targetRhs && entryRhs !== "") {
        return { key: sk, entry, reason: "entry_instrument_key_rhs" };
      }
    }
  }

  // not found
  return null;
};

// Extraction helpers
const extractLtp = (entry) => {
  if (!entry) return null;
  if (entry.lp !== undefined) return Number(entry.lp);
  if (entry.ltp !== undefined) return Number(entry.ltp);
  if (entry.last_price !== undefined) return Number(entry.last_price);
  // Upstox-like nested
  try {
    if (
      entry.fullFeed &&
      entry.fullFeed.marketFF &&
      entry.fullFeed.marketFF.ltpc &&
      entry.fullFeed.marketFF.ltpc.ltp !== undefined
    ) {
      return Number(entry.fullFeed.marketFF.ltpc.ltp);
    }
  } catch (e) {}
  try {
    if (
      entry.marketFF &&
      entry.marketFF.ltpc &&
      entry.marketFF.ltpc.ltp !== undefined
    ) {
      return Number(entry.marketFF.ltpc.ltp);
    }
  } catch (e) {}
  return null;
};

const extractVolume = (entry) => {
  if (!entry) return 0;
  if (entry.v !== undefined) return Number(entry.v);
  if (entry.volume !== undefined) return Number(entry.volume);
  try {
    if (
      entry.fullFeed &&
      entry.fullFeed.marketFF &&
      entry.fullFeed.marketFF.marketOHLC &&
      Array.isArray(entry.fullFeed.marketFF.marketOHLC.ohlc) &&
      entry.fullFeed.marketFF.marketOHLC.ohlc[0] &&
      entry.fullFeed.marketFF.marketOHLC.ohlc[0].vol !== undefined
    ) {
      return Number(entry.fullFeed.marketFF.marketOHLC.ohlc[0].vol);
    }
  } catch (e) {}
  return 0;
};

const extractChange = (entry, ltp) => {
  if (!entry) return 0;
  if (entry.cp !== undefined) return Number(entry.cp); // sometimes cp is change
  if (entry.change !== undefined) return Number(entry.change);
  // fallback: ltp - open
  const openVal = entry.op ?? entry.open;
  if (openVal !== undefined && !Number.isNaN(Number(openVal))) {
    return Number(ltp) - Number(openVal);
  }
  return 0;
};

const StocksListZeroDelay = ({
  stocks = [],
  maxRows = 100,
  showLatency = true,
  showPerformanceStats = true,
  onStockClick = null,
  enableAdvancedMetrics = false,
}) => {
  const [processedStocks, setProcessedStocks] = useState([]);
  const [priceHighlights, setPriceHighlights] = useState({});
  const [updateCount, setUpdateCount] = useState(0);

  // streaming hook
  const {
    marketData,
    connectionStatus,

    latency,
    error,
    isConnected,
    lastUpdate,
    requestStats,
    ping,
  } = useZeroDelayMarketData({
    enableStats: showPerformanceStats,
    onDataReceived: useCallback(() => {
      setUpdateCount((c) => c + 1);
    }, []),
  });

  // compute processed stocks (pure) — match only by instrument_key
  const computeProcessedByInstrumentKey = useCallback(() => {
    const result = [];
    const highlights = {};
    if (!Array.isArray(stocks) || stocks.length === 0) {
      return { result, highlights };
    }

    // build quick lookup of previous prices for highlight comparison
    const prevMap = {};
    for (const p of processedStocks) {
      if (p && p.instrument_key)
        prevMap[p.instrument_key] = Number(
          p.current_price ?? p.last_price ?? 0
        );
    }

    for (const stock of stocks.slice(0, maxRows)) {
      const instKey = stock.instrument_key || stock.instrumentKey || null;
      if (!instKey) {
        // no instrument_key on the stock item — keep static
        result.push({
          ...stock,
          _live_data_available: false,
          _source: "no_instrument_key",
          current_price: Number(stock.last_price ?? stock.ltp ?? 0),
          last_price: Number(stock.last_price ?? stock.ltp ?? 0),
          price_change: Number(stock.change ?? 0),
          price_change_percent: Number(stock.change_percent ?? 0),
        });
        continue;
      }

      const match = matchByInstrumentKey(marketData, instKey);

      if (match && match.entry) {
        const entry = match.entry;
        const ltp = extractLtp(entry);
        const finalLtp =
          ltp !== null && !Number.isNaN(ltp)
            ? Number(ltp)
            : Number(stock.last_price ?? stock.ltp ?? 0);
        const changeVal = extractChange(entry, finalLtp);
        const vol = extractVolume(entry);

        const prevPrice =
          prevMap[instKey] ?? Number(stock.last_price ?? stock.ltp ?? 0);
        if (!Number.isNaN(finalLtp) && finalLtp !== prevPrice) {
          highlights[instKey] = {
            direction: finalLtp > prevPrice ? "up" : "down",
            timestamp: Date.now(),
          };
        }

        result.push({
          ...stock,
          current_price: finalLtp,
          last_price: finalLtp,
          open_price: Number(entry.op ?? entry.open ?? stock.open_price ?? 0),
          high_price: Number(entry.h ?? entry.high ?? stock.high_price ?? 0),
          low_price: Number(entry.l ?? entry.low ?? stock.low_price ?? 0),
          price_change: Number(changeVal),
          price_change_percent:
            entry.change_percent !== undefined
              ? Number(entry.change_percent)
              : Number(entry.op ?? entry.open ?? stock.open_price ?? 0)
              ? ((finalLtp -
                  Number(entry.op ?? entry.open ?? stock.open_price ?? 0)) /
                  Number(entry.op ?? entry.open ?? stock.open_price ?? 0)) *
                100
              : 0,
          volume: vol,
          instrument_token:
            entry.instrument_token || stock.instrument_token || null,
          last_trade_time: entry.ltt || entry.last_trade_time || null,
          _matched_key: match.key,
          _live_data_available: true,
          _source: "instrument_key",
          _match_reason: match.reason,
          _last_update: lastUpdate || new Date().toISOString(),
        });
      } else {
        // no live feed match by instrument_key
        result.push({
          ...stock,
          _live_data_available: false,
          _source: "static",
          current_price: Number(stock.last_price ?? stock.ltp ?? 0),
          last_price: Number(stock.last_price ?? stock.ltp ?? 0),
          price_change: Number(stock.change ?? 0),
          price_change_percent: Number(stock.change_percent ?? 0),
        });
      }
    }

    return { result, highlights };
  }, [stocks, marketData, processedStocks, maxRows, lastUpdate]);

  // effect to recompute processedStocks whenever marketData or stocks or updateCount changes
  useEffect(() => {
    const { result, highlights } = computeProcessedByInstrumentKey();
    setProcessedStocks(result);
    if (Object.keys(highlights).length > 0) {
      setPriceHighlights((prev) => ({ ...prev, ...highlights }));
    }
  }, [computeProcessedByInstrumentKey, updateCount, marketData, stocks]);

  // clear highlights older than 2.5s
  useEffect(() => {
    if (!Object.keys(priceHighlights).length) return;
    const t = setTimeout(() => {
      const now = Date.now();
      setPriceHighlights((prev) => {
        const next = { ...prev };
        for (const k of Object.keys(prev)) {
          if (now - prev[k].timestamp > 2500) delete next[k];
        }
        return next;
      });
    }, 1200);
    return () => clearTimeout(t);
  }, [priceHighlights]);

  const PriceChangeIndicator = ({ instKey }) => {
    const change = priceHighlights[instKey];
    const isRecent = change && Date.now() - change.timestamp < 2000;
    if (!isRecent) return null;
    return (
      <Box component="span" sx={{ ml: 0.5 }}>
        {change.direction === "up" ? (
          <TrendingUp sx={{ color: green[500], fontSize: 16 }} />
        ) : (
          <TrendingDown sx={{ color: red[500], fontSize: 16 }} />
        )}
      </Box>
    );
  };

  const formatPrice = (p) => (typeof p === "number" ? p.toFixed(2) : "0.00");
  const formatPercentage = (percent) => {
    if (typeof percent !== "number" || Number.isNaN(percent))
      return <span>0.00%</span>;
    const c = percent >= 0 ? green[600] : red[600];
    return (
      <Typography component="span" sx={{ color: c, fontWeight: 600 }}>
        {percent >= 0 ? "+" : ""}
        {percent.toFixed(2)}%
      </Typography>
    );
  };

  const ConnectionStatusIndicator = () => (
    <Box display="flex" alignItems="center" gap={1}>
      <Tooltip
        title={`Connection: ${connectionStatus} | Latency: ${latency}ms`}
      >
        <Box display="flex" alignItems="center">
          {isConnected ? (
            <SignalWifi4Bar sx={{ color: green[500], fontSize: 20 }} />
          ) : (
            <SignalWifi0Bar sx={{ color: red[500], fontSize: 20 }} />
          )}
          {showLatency && latency !== null && (
            <Typography variant="caption" sx={{ ml: 0.5, color: grey[600] }}>
              {latency}ms
            </Typography>
          )}
        </Box>
      </Tooltip>
      <Tooltip title="Refresh stats">
        <IconButton size="small" onClick={requestStats}>
          <Refresh fontSize="small" />
        </IconButton>
      </Tooltip>
      <Tooltip title="Test ping">
        <IconButton size="small" onClick={ping}>
          <Speed fontSize="small" />
        </IconButton>
      </Tooltip>
    </Box>
  );

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        ZERO-DELAY streaming error: {error}
      </Alert>
    );
  }

  return (
    <Box>
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={2}
      >
        <Box>
          <Typography variant="h6" component="h2">
            🚀 Ultra-Fast Market Data{" "}
            {isConnected && (
              <Typography
                component="span"
                sx={{ color: green[600], ml: 1, fontSize: "0.8em" }}
              >
                LIVE
              </Typography>
            )}
          </Typography>
          {lastUpdate && (
            <Typography variant="caption" color="textSecondary">
              Last update: {new Date(lastUpdate).toLocaleTimeString()}
            </Typography>
          )}
        </Box>
        <ConnectionStatusIndicator />
      </Box>

      <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
        <Table stickyHeader size="small" aria-label="stocks table">
          <TableHead>
            <TableRow>
              <TableCell>Symbol</TableCell>
              <TableCell align="right">Price</TableCell>
              <TableCell align="right">Change</TableCell>
              <TableCell align="right">Change %</TableCell>
              <TableCell align="right">Volume</TableCell>
              <TableCell align="center">Status</TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            {processedStocks.map((stock, idx) => (
              <TableRow
                key={stock.instrument_key || stock.symbol || idx}
                hover
                onClick={onStockClick ? () => onStockClick(stock) : undefined}
                sx={{ cursor: onStockClick ? "pointer" : "default" }}
              >
                <TableCell component="th" scope="row">
                  <Box display="flex" alignItems="center">
                    <Typography variant="body2" fontWeight={600}>
                      {stock.symbol || stock.name}
                    </Typography>
                    <PriceChangeIndicator instKey={stock.instrument_key} />
                  </Box>
                  {stock.name && (
                    <Typography variant="caption" color="textSecondary">
                      {String(stock.name).slice(0, 40)}
                      {String(stock.name).length > 40 ? "..." : ""}
                    </Typography>
                  )}
                </TableCell>

                <TableCell align="right">
                  <Typography fontWeight={600}>
                    ₹{formatPrice(stock.current_price)}
                  </Typography>
                </TableCell>

                <TableCell align="right">
                  <Typography
                    sx={{
                      color: stock.price_change >= 0 ? green[600] : red[600],
                      fontWeight: 600,
                    }}
                  >
                    {stock.price_change >= 0 ? "+" : ""}₹
                    {formatPrice(Math.abs(stock.price_change))}
                  </Typography>
                </TableCell>

                <TableCell align="right">
                  {formatPercentage(stock.price_change_percent)}
                </TableCell>

                <TableCell align="right">
                  <Typography>
                    {stock.volume?.toLocaleString() || "-"}
                  </Typography>
                </TableCell>

                <TableCell align="center">
                  {stock._live_data_available ? (
                    <Tooltip
                      title={`Live via ${stock._source} | key: ${
                        stock._matched_key || stock.instrument_key
                      } | matchReason: ${stock._match_reason || ""}`}
                    >
                      <Chip label="LIVE" color="success" size="small" />
                    </Tooltip>
                  ) : (
                    <Tooltip title="Static/No live data (instrument_key not matched)">
                      <Chip label="STATIC" color="default" size="small" />
                    </Tooltip>
                  )}
                </TableCell>
              </TableRow>
            ))}

            {processedStocks.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                  <Typography color="textSecondary">
                    No stock data available
                  </Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default StocksListZeroDelay;
