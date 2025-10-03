// components/common/StocksListWithLivePrices.js
/**
 * 🚀 Enhanced StocksList component with ZERO-DELAY live prices
 *
 * Robust key-lookup: will try many candidate keys (symbol, instrument_key,
 * pipe-split names, normalized uppercase/no-space names and common synonyms)
 * so indices like NIFTY / BANKNIFTY / FINNIFTY match feed keys like "Nifty 50".
 */

import React from "react";
import StocksList from "./StocksList";
import { useIndicesWithLivePrices } from "../../hooks/useIndicesWithLivePrices";
import useMarketStore from "../../store/marketStore";
import { Box, Chip, Tooltip } from "@mui/material";
import { SignalWifi4Bar, SignalWifi0Bar } from "@mui/icons-material";
import { green, grey } from "@mui/material/colors";

const COMMON_INDEX_ALIAS = {
  NIFTY: "Nifty 50",
  BANKNIFTY: "Nifty Bank",
  FINNIFTY: "Nifty Fin Service",
  SENSEX: "SENSEX",
  MIDCPNIFTY: "Nifty Midcap 50",
};

// normalize for human-readables
const normalizeForKey = (s) => {
  if (s === undefined || s === null) return "";
  return String(s).trim();
};

// compact no-space uppercase
const compactKey = (s) => {
  if (s === undefined || s === null) return "";
  return String(s)
    .replace(/\s+/g, "")
    .replace(/[_-]+/g, "")
    .toUpperCase();
};

// Build candidate strings from the item
const getCandidatesForItem = (item) => {
  const candidates = new Set();

  const push = (v) => {
    if (v === undefined || v === null) return;
    const n = normalizeForKey(v);
    if (!n) return;
    candidates.add(n); // raw
    candidates.add(n.toUpperCase());
    candidates.add(n.toLowerCase());
    candidates.add(compactKey(n)); // compact
  };

  push(item.symbol);
  push(item.name);
  push(item.displayName); // optional
  push(item.intrument_key); // possible typo variant
  if (item.instrument_key) {
    push(item.instrument_key);
    try {
      const parts = String(item.instrument_key)
        .split("|")
        .map((p) => p.trim())
        .filter(Boolean);
      if (parts.length > 0) {
        push(parts[parts.length - 1]); // RHS human readable
        push(parts.join("|"));
      }
    } catch (e) {
      /* ignore */
    }
  }

  // Common aliases by symbol
  if (item.symbol && COMMON_INDEX_ALIAS[item.symbol.toUpperCase()]) {
    push(COMMON_INDEX_ALIAS[item.symbol.toUpperCase()]);
  }

  // Fuzzy symbol variants
  if (typeof item.symbol === "string") {
    push(item.symbol.replace(/[_\-\s]+/g, " "));
    push(item.symbol.replace(/[_\-\s]+/g, ""));
  }

  return Array.from(candidates);
};

// Improved matching tries:
// 1) direct store key match using candidates
// 2) direct value match (value.symbol or value.instrument_key), both exact and compact
// 3) fallback: scan store keys comparing compacted versions
// Returns {value: storeValue, matchedKey: keyUsed} or null
const findLivePrice = (allLivePrices, item) => {
  if (!allLivePrices || typeof allLivePrices !== "object") return null;

  const candidates = getCandidatesForItem(item);
  if (process.env.NODE_ENV === "development") {
    console.debug(
      "🔎 Candidates for",
      item.symbol || item.name || item.instrument_key,
      candidates.slice(0, 8)
    );
  }

  // 1) direct lookup by candidate keys (fast)
  for (let i = 0; i < candidates.length; i++) {
    const k = candidates[i];
    if (!k) continue;
    if (allLivePrices[k]) {
      return { value: allLivePrices[k], matchedKey: k, reason: "direct_key" };
    }
  }

  // 2) check store values for matching symbol or instrument_key fields
  const storeKeys = Object.keys(allLivePrices);
  for (let i = 0; i < storeKeys.length; i++) {
    const sk = storeKeys[i];
    const val = allLivePrices[sk];
    if (!val) continue;

    // If store value has symbol that matches candidate (exact or compact)
    const valSymbol = normalizeForKey(val.symbol);
    const valInstrumentKey =
      normalizeForKey(val.instrument_key) ||
      normalizeForKey(val.instrumentKey) ||
      "";

    // exact symbol match
    if (valSymbol) {
      for (let c = 0; c < candidates.length; c++) {
        if (
          candidates[c] === valSymbol ||
          candidates[c] === valSymbol.toUpperCase() ||
          candidates[c] === valSymbol.toLowerCase()
        ) {
          return { value: val, matchedKey: sk, reason: "value_symbol_exact" };
        }
      }
    }

    // instrument_key match
    if (valInstrumentKey) {
      for (let c = 0; c < candidates.length; c++) {
        if (
          candidates[c] === valInstrumentKey ||
          candidates[c] === valInstrumentKey.toUpperCase()
        ) {
          return {
            value: val,
            matchedKey: sk,
            reason: "value_instrument_key_exact",
          };
        }
      }
    }

    // compact match (no-space uppercase) for symbol or instrument_key
    const valCompactSymbol = valSymbol ? compactKey(valSymbol) : "";
    const valCompactInst = valInstrumentKey ? compactKey(valInstrumentKey) : "";
    for (let c = 0; c < candidates.length; c++) {
      if (
        compactKey(candidates[c]) === valCompactSymbol ||
        compactKey(candidates[c]) === valCompactInst
      ) {
        return { value: val, matchedKey: sk, reason: "value_compact" };
      }
    }
  }

  // 3) Last-resort: compare compact(storeKey) to compact(candidate) to catch keys like "NSE_EQ|Nifty50" vs "Nifty 50"
  for (let i = 0; i < storeKeys.length; i++) {
    const sk = storeKeys[i];
    const skCompact = compactKey(sk);
    for (let c = 0; c < candidates.length; c++) {
      if (compactKey(candidates[c]) === skCompact) {
        return {
          value: allLivePrices[sk],
          matchedKey: sk,
          reason: "key_compact_match",
        };
      }
    }
  }

  return null;
};

const StocksListWithLivePrices = ({
  data = [],
  title = "",
  enhanceWithLivePrices = true,
  showLiveIndicator = true,
  ...stocksListProps
}) => {
  // Zustand store
  const allLivePrices = useMarketStore((state) => state.prices);
  const connectionStatus = useMarketStore((state) => state.connectionStatus);

  // Hook fallback (analytics)
  const { indices: enhancedData = [], isConnected } = useIndicesWithLivePrices(
    enhanceWithLivePrices ? data : []
  );

  const finalData = React.useMemo(() => {
    if (!enhanceWithLivePrices) return data;

    if (process.env.NODE_ENV === "development") {
      console.debug(
        "🏛️ Zustand store snapshot size:",
        Object.keys(allLivePrices || {}).length
      );
    }

    return data.map((item) => {
      const label =
        item.symbol || item.name || item.instrument_key || "UNKNOWN";

      const found = findLivePrice(allLivePrices, item);
      if (found && found.value) {
        const livePrice = found.value;
        if (process.env.NODE_ENV === "development") {
          console.debug(`✅ Matched live price for ${label}`, {
            matchedKey: found.matchedKey,
            reason: found.reason,
            livePrice,
          });
        }

        // prefer fields ltp / last_price / price-like fields; support different shapes
        const ltp =
          livePrice.ltp ??
          livePrice.last_price ??
          livePrice.last_price_c ??
          livePrice.price ??
          (livePrice.fullFeed &&
            livePrice.fullFeed.marketFF &&
            livePrice.fullFeed.marketFF.ltpc &&
            livePrice.fullFeed.marketFF.ltpc.ltp) ??
          null;
        const change =
          livePrice.change ??
          livePrice.cp ??
          livePrice.fullFeed?.marketFF?.ltpc?.cp ??
          0;
        const change_percent = livePrice.change_percent ?? livePrice.pcp ?? 0;
        const volume =
          livePrice.volume ??
          livePrice.vol ??
          livePrice.fullFeed?.marketFF?.marketOHLC?.ohlc?.[0]?.vol ??
          0;

        // 🔍 DEBUG: Log extracted values for troubleshooting
        if (process.env.NODE_ENV === "development" && (change !== 0 || change_percent !== 0 || volume !== 0)) {
          console.debug(`📊 Extracted data for ${label}:`, {
            ltp,
            change,
            change_percent,
            volume,
            source: livePrice
          });
        }

        return {
          ...item,
          last_price:
            typeof ltp === "number"
              ? ltp
              : Number(ltp) || item.last_price || item.ltp || 0,
          ltp:
            typeof ltp === "number"
              ? ltp
              : Number(ltp) || item.last_price || item.ltp || 0,
          current_price:
            typeof ltp === "number"
              ? ltp
              : Number(ltp) || item.last_price || item.ltp || 0,
          change: Number(change) || item.change || 0,
          change_percent: Number(change_percent) || item.change_percent || 0,
          volume: Number(volume) || item.volume || 0,
          _live_data_available: true,
          _source: "zustand_store",
        };
      }

      // fallback: hook-provided enriched data
      const hookItem = enhancedData.find(
        (e) =>
          (e.symbol && (e.symbol === item.symbol || e.symbol === item.name)) ||
          (e.name && (e.name === item.symbol || e.name === item.name))
      );
      if (hookItem && hookItem._live_data_available) {
        if (process.env.NODE_ENV === "development") {
          console.debug(`🔄 Using hook data fallback for ${label}`, hookItem);
        }
        return hookItem;
      }

      if (process.env.NODE_ENV === "development") {
        console.debug(`❌ No live data for ${label} — using original`, {
          hasHook: !!hookItem,
          storeKeysSample: Object.keys(allLivePrices || {}).slice(0, 8),
        });
      }

      return {
        ...item,
        _live_data_available: false,
        _source: "analytics_only",
      };
    });
  }, [data, allLivePrices, enhancedData, enhanceWithLivePrices]);

  const enhancedSummary = React.useMemo(() => {
    const liveCount = finalData.filter(
      (item) => item._live_data_available
    ).length;
    const totalCount = finalData.length;
    const livePercentage =
      totalCount > 0 ? Math.round((liveCount / totalCount) * 100) : 0;
    return { total: totalCount, live: liveCount, livePercentage };
  }, [finalData]);

  const enhancedTitle = React.useMemo(() => {
    if (!enhanceWithLivePrices || !showLiveIndicator) return title;
    const liveCount = enhancedSummary.live;
    const totalCount = enhancedSummary.total;
    if (liveCount === 0) return title;

    return (
      <Box display="flex" alignItems="center" gap={1}>
        <span>{title}</span>
        {(isConnected || connectionStatus === "connected") && liveCount > 0 && (
          <Tooltip
            title={`${liveCount}/${totalCount} with live prices (${enhancedSummary.livePercentage}%)`}
          >
            <Chip
              size="small"
              icon={<SignalWifi4Bar />}
              label={`${liveCount} LIVE`}
              sx={{
                backgroundColor: green[500],
                color: "white",
                fontSize: "0.7rem",
                height: "20px",
                "& .MuiChip-icon": { fontSize: "14px", color: "white" },
              }}
            />
          </Tooltip>
        )}
        {!isConnected && connectionStatus !== "connected" && (
          <Tooltip title="Not connected to live data stream">
            <Chip
              size="small"
              icon={<SignalWifi0Bar />}
              label="OFFLINE"
              sx={{
                backgroundColor: grey[500],
                color: "white",
                fontSize: "0.7rem",
                height: "20px",
                "& .MuiChip-icon": { fontSize: "14px", color: "white" },
              }}
            />
          </Tooltip>
        )}
      </Box>
    );
  }, [
    title,
    enhanceWithLivePrices,
    showLiveIndicator,
    enhancedSummary,
    isConnected,
    connectionStatus,
  ]);

  return (
    <StocksList {...stocksListProps} data={finalData} title={enhancedTitle} />
  );
};

export default StocksListWithLivePrices;
