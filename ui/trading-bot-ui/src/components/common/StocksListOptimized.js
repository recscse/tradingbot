// components/common/StocksListOptimized.jsx
/**
 * 🚀 StocksListOptimized - ULTRA-OPTIMIZED FOR REAL-TIME PERFORMANCE
 *
 * Each row subscribes to Zustand store with a selector that tries several
 * candidate keys (symbol, instrument_key, compact variant, pipe-RHS, etc.)
 * so live prices stored under e.g. "NSE_EQ|INE002A01018" are correctly found.
 */

import React, { memo, useMemo, useState, useCallback } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Skeleton,
  useTheme,
  IconButton,
  Tooltip,
} from "@mui/material";
import { ShowChart as OptionsIcon } from "@mui/icons-material";
import useMarketStore from "../../store/marketStore";
import OptionChainModal from "../options/OptionChainModal";

/* -------------------------
   Utilities used by rows
   ------------------------- */

// compact key: remove whitespace/underscores/hyphens and uppercase
const compactKey = (s) => {
  if (s === undefined || s === null) return "";
  return String(s)
    .replace(/[\s_-]+/g, "")
    .toUpperCase();
};

// RHS of pipe-format e.g. "NSE_EQ|Nifty 50" -> "Nifty 50"
const rhsFromPipe = (s) => {
  if (!s && s !== 0) return "";
  try {
    const parts = String(s)
      .split("|")
      .map((p) => p.trim())
      .filter(Boolean);
    if (parts.length === 0) return "";
    return parts[parts.length - 1];
  } catch (e) {
    return String(s);
  }
};

// Build ordered candidate keys to lookup in store
const buildCandidatesForLookup = (symbolOrObj) => {
  // symbolOrObj may be string (symbol) or object { symbol, instrument_key, name }
  const candidates = [];
  if (!symbolOrObj && symbolOrObj !== 0) return candidates;

  // If an object, prefer instrument_key and symbol
  if (typeof symbolOrObj === "object") {
    const { symbol, instrument_key, name } = symbolOrObj;
    if (instrument_key) {
      candidates.push(instrument_key);
      // also push RHS and compact RHS
      const rhs = rhsFromPipe(instrument_key);
      if (rhs) candidates.push(rhs, compactKey(rhs));
    }
    if (symbol) {
      candidates.push(symbol);
      candidates.push(compactKey(symbol));
      // relaxed symbol (replace _ - with space)
      candidates.push(String(symbol).replace(/[_-]+/g, " "));
    }
    if (name) {
      candidates.push(name, compactKey(name));
    }
  } else {
    // primitive: treat as symbol string
    const s = String(symbolOrObj);
    candidates.push(s);
    candidates.push(compactKey(s));
    if (s.includes("|")) {
      const rhs = rhsFromPipe(s);
      if (rhs) candidates.push(rhs, compactKey(rhs));
    }
    candidates.push(s.replace(/[_-]+/g, " "));
  }

  // unique preserve order
  const seen = new Set();
  return candidates.filter((c) => {
    if (c === undefined || c === null || c === "") return false;
    const key = String(c);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

/* -------------------------
   StockRow - per-symbol subscriber
   ------------------------- */

const StockRow = memo(
  ({
    symbol, // can be string symbol or object with instrument_key
    showVolume = true,
    showSector = false,
    compact = false,
    showOptionChain = false,
    onOptionChainClick,
  }) => {
    const theme = useTheme();

    // Build candidates once per symbol prop
    const candidates = useMemo(
      () => buildCandidatesForLookup(symbol),
      [symbol]
    );

    // Selector: returns first store.prices[key] found among candidates
    // (keeps subscription granular to the returned object)
    const stock = useMarketStore(
      useMemo(
        () => (state) => {
          if (!state.prices) return null;
          for (let i = 0; i < candidates.length; i++) {
            const k = candidates[i];
            if (k && state.prices[k]) return state.prices[k];
          }
          // Fallback: if symbol is an object try its symbol key
          if (typeof symbol === "object" && symbol?.symbol) {
            return state.prices[symbol.symbol] || null;
          }
          // fallback by direct symbol string
          return state.prices[String(symbol)] || null;
        },
        [candidates, symbol]
      )
    );

    // Handler for option click - attempt to create a compact stock object
    const handleOptionChainClick = useCallback(
      (e) => {
        e.stopPropagation();
        if (!onOptionChainClick) return;
        const s = stock || (typeof symbol === "object" ? symbol : { symbol });
        onOptionChainClick({
          symbol: s.symbol || (typeof symbol === "string" ? symbol : undefined),
          name: s.name || s.symbol,
          instrument_key:
            s.instrument_key ||
            (typeof symbol === "object" ? symbol.instrument_key : undefined),
          last_price: s.ltp ?? s.last_price,
          change: s.change ?? 0,
          change_percent: s.change_percent ?? 0,
        });
      },
      [onOptionChainClick, stock, symbol]
    );

    // If no data available for this row yet, show skeleton / placeholder
    if (!stock) {
      return (
        <TableRow>
          <TableCell colSpan={showVolume ? 6 : 5}>
            <Skeleton variant="rectangular" height={compact ? 30 : 40} />
          </TableCell>
        </TableRow>
      );
    }

    const isPositive = Number(stock.change || 0) >= 0;
    const changeColor = isPositive
      ? theme.palette.success.main
      : theme.palette.error.main;

    return (
      <TableRow
        sx={{
          height: compact ? 35 : 45,
          "&:hover": { backgroundColor: theme.palette.action.hover },
          transition: "background-color 0.1s ease",
        }}
      >
        {/* Symbol */}
        <TableCell sx={{ py: compact ? 0.5 : 1 }}>
          <Box>
            <Typography variant={compact ? "body2" : "body1"} fontWeight="bold">
              {stock.symbol ||
                (typeof symbol === "string"
                  ? symbol
                  : stock.instrument_key || "")}
            </Typography>
            {showSector && stock.sector && (
              <Typography variant="caption" color="text.secondary">
                {stock.sector}
              </Typography>
            )}
          </Box>
        </TableCell>

        {/* LTP */}
        <TableCell align="right" sx={{ py: compact ? 0.5 : 1 }}>
          <Typography
            variant={compact ? "body2" : "body1"}
            fontWeight="bold"
            color={changeColor}
          >
            ₹{Number(stock.ltp || 0).toFixed(2)}
          </Typography>
        </TableCell>

        {/* Change */}
        <TableCell align="right" sx={{ py: compact ? 0.5 : 1 }}>
          <Typography
            variant={compact ? "body2" : "body1"}
            color={changeColor}
            fontWeight="medium"
          >
            {isPositive ? "+" : ""}₹{Number(stock.change || 0).toFixed(2)}
          </Typography>
        </TableCell>

        {/* Change % */}
        <TableCell align="right" sx={{ py: compact ? 0.5 : 1 }}>
          <Chip
            label={`${isPositive ? "+" : ""}${Number(
              stock.change_percent || 0
            ).toFixed(2)}%`}
            size={compact ? "small" : "medium"}
            sx={{
              backgroundColor: isPositive
                ? theme.palette.success.light
                : theme.palette.error.light,
              color: isPositive
                ? theme.palette.success.contrastText
                : theme.palette.error.contrastText,
              fontWeight: "bold",
              minWidth: compact ? 60 : 80,
            }}
          />
        </TableCell>

        {/* Volume */}
        {showVolume && (
          <TableCell align="right" sx={{ py: compact ? 0.5 : 1 }}>
            <Typography
              variant={compact ? "caption" : "body2"}
              color="text.secondary"
            >
              {Number(stock.volume || 0) > 1000000
                ? `${(Number(stock.volume || 0) / 1000000).toFixed(1)}M`
                : Number(stock.volume || 0) > 1000
                ? `${(Number(stock.volume || 0) / 1000).toFixed(1)}K`
                : String(stock.volume || 0)}
            </Typography>
          </TableCell>
        )}

        {/* High / Low */}
        <TableCell align="right" sx={{ py: compact ? 0.5 : 1 }}>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-end",
              gap: 0.5,
            }}
          >
            <Box>
              <Typography variant="caption" color="text.secondary">
                H: ₹
                {stock.high !== undefined
                  ? Number(stock.high).toFixed(2)
                  : "--"}
              </Typography>
              <br />
              <Typography variant="caption" color="text.secondary">
                L: ₹
                {stock.low !== undefined ? Number(stock.low).toFixed(2) : "--"}
              </Typography>
            </Box>

            {/* Option Chain Button */}
            {showOptionChain && (
              <Tooltip title="View Option Chain" placement="left">
                <IconButton
                  size="small"
                  onClick={handleOptionChainClick}
                  sx={{
                    width: 24,
                    height: 24,
                    color: theme.palette.primary.main,
                    "&:hover": {
                      bgcolor: `${theme.palette.primary.main}20`,
                      transform: "scale(1.1)",
                    },
                    transition: "all 0.15s ease",
                  }}
                >
                  <OptionsIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </TableCell>
      </TableRow>
    );
  }
);

StockRow.displayName = "StockRow";

/* -------------------------
   SkeletonRow
   ------------------------- */

const SkeletonRow = memo(({ showVolume = true, compact = false }) => (
  <TableRow sx={{ height: compact ? 35 : 45 }}>
    <TableCell>
      <Skeleton width={80} height={compact ? 20 : 24} />
    </TableCell>
    <TableCell align="right">
      <Skeleton width={60} height={compact ? 20 : 24} />
    </TableCell>
    <TableCell align="right">
      <Skeleton width={60} height={compact ? 20 : 24} />
    </TableCell>
    <TableCell align="right">
      <Skeleton width={80} height={compact ? 20 : 24} />
    </TableCell>
    {showVolume && (
      <TableCell align="right">
        <Skeleton width={50} height={compact ? 20 : 24} />
      </TableCell>
    )}
    <TableCell align="right">
      <Skeleton width={70} height={compact ? 20 : 24} />
    </TableCell>
  </TableRow>
));

SkeletonRow.displayName = "SkeletonRow";

/* -------------------------
   StocksListOptimized (main)
   ------------------------- */

const StocksListOptimized = memo(
  ({
    title,
    symbols = [], // array of strings OR array of objects { symbol, instrument_key, name }
    isLoading = false,
    titleIcon = "📊",
    emptyMessage = "No data available",
    maxItems = 20,
    showVolume = true,
    showSector = false,
    compact = false,
    containerHeight = "70vh",
    showOptionChain = false,
  }) => {
    const theme = useTheme();

    // Defensive debug logging
    if (process.env.NODE_ENV === "development") {
      let titlePreview = "";
      try {
        if (typeof title === "string") {
          titlePreview =
            title.length > 20 ? `${title.substring(0, 20)}...` : title;
        } else if (title == null) {
          titlePreview = "<<no-title>>";
        } else if (React.isValidElement(title)) {
          const child = title.props?.children;
          if (typeof child === "string") {
            titlePreview =
              child.length > 20 ? `${child.substring(0, 20)}...` : child;
          } else {
            titlePreview = "<<jsx-title>>";
          }
        } else {
          titlePreview = String(title);
        }
      } catch (e) {
        titlePreview = "<<debug-error>>";
      }

      console.log("🔍 StocksListOptimized Debug:", {
        title: titlePreview,
        showOptionChain,
        symbolsLength: Array.isArray(symbols) ? symbols.length : 0,
        hasSymbols: Array.isArray(symbols) ? symbols.length > 0 : false,
      });
    }

    // Option chain modal state
    const [optionChainOpen, setOptionChainOpen] = useState(false);
    const [selectedStock, setSelectedStock] = useState(null);

    const handleOptionChainClick = useCallback((stock) => {
      setSelectedStock(stock);
      setOptionChainOpen(true);
    }, []);

    // Deduplicate symbols to prevent key collisions
    const uniqueSymbols = useMemo(() => {
      if (!Array.isArray(symbols)) return [];
      const seen = new Set();
      return symbols.filter((sym) => {
        const key =
          typeof sym === "string"
            ? sym
            : sym.instrument_key || sym.symbol || JSON.stringify(sym);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      });
    }, [symbols]);

    // Display slice
    const displaySymbols = useMemo(
      () => uniqueSymbols.slice(0, maxItems),
      [uniqueSymbols, maxItems]
    );

    const tableHeader = useMemo(
      () => (
        <TableHead>
          <TableRow>
            <TableCell>
              <Typography variant="subtitle2" fontWeight="bold">
                Symbol
              </Typography>
            </TableCell>
            <TableCell align="right">
              <Typography variant="subtitle2" fontWeight="bold">
                LTP
              </Typography>
            </TableCell>
            <TableCell align="right">
              <Typography variant="subtitle2" fontWeight="bold">
                Change
              </Typography>
            </TableCell>
            <TableCell align="right">
              <Typography variant="subtitle2" fontWeight="bold">
                Change %
              </Typography>
            </TableCell>
            {showVolume && (
              <TableCell align="right">
                <Typography variant="subtitle2" fontWeight="bold">
                  Volume
                </Typography>
              </TableCell>
            )}
            <TableCell align="right">
              <Typography variant="subtitle2" fontWeight="bold">
                H/L
              </Typography>
            </TableCell>
            {showOptionChain && (
              <TableCell align="center">
                <Typography variant="subtitle2" fontWeight="bold">
                  Options
                </Typography>
              </TableCell>
            )}
          </TableRow>
        </TableHead>
      ),
      [showVolume, showOptionChain]
    );

    return (
      <Card
        elevation={3}
        sx={{
          height: containerHeight,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <CardContent sx={{ pb: 1, flexShrink: 0 }}>
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="h6" component="span">
              {titleIcon}
            </Typography>
            <Typography variant="h6" fontWeight="bold" color="primary">
              {typeof title === "string" || typeof title === "number"
                ? title
                : React.isValidElement(title)
                ? title
                : typeof title === "object" && title !== null
                ? String(title)
                : ""}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              ({displaySymbols.length} items)
            </Typography>
          </Box>
        </CardContent>

        <Box sx={{ flex: 1, overflow: "hidden" }}>
          <TableContainer
            component={Paper}
            sx={{
              height: "100%",
              "& .MuiTableContainer-root": { borderRadius: 0 },
            }}
          >
            <Table
              stickyHeader
              size={compact ? "small" : "medium"}
              sx={{
                "& .MuiTableCell-head": {
                  backgroundColor: theme.palette.grey[100],
                  fontWeight: "bold",
                },
              }}
            >
              {tableHeader}
              <TableBody>
                {isLoading ? (
                  Array.from({ length: Math.min(maxItems, 10) }).map(
                    (_, index) => (
                      <SkeletonRow
                        key={`skeleton-${index}`}
                        showVolume={showVolume}
                        compact={compact}
                      />
                    )
                  )
                ) : displaySymbols.length > 0 ? (
                  displaySymbols.map((sym) => (
                    <StockRow
                      key={
                        typeof sym === "string"
                          ? sym
                          : sym.instrument_key ||
                            sym.symbol ||
                            JSON.stringify(sym)
                      }
                      symbol={sym}
                      showVolume={showVolume}
                      showSector={showSector}
                      compact={compact}
                      showOptionChain={showOptionChain}
                      onOptionChainClick={(s) => {
                        setSelectedStock(s);
                        setOptionChainOpen(true);
                        if (handleOptionChainClick) handleOptionChainClick(s);
                      }}
                    />
                  ))
                ) : (
                  <TableRow>
                    <TableCell
                      colSpan={showVolume ? 6 : 5}
                      align="center"
                      sx={{ py: 4 }}
                    >
                      <Typography variant="body2" color="text.secondary">
                        {emptyMessage}
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>

        {showOptionChain && (
          <OptionChainModal
            open={optionChainOpen}
            onClose={() => {
              setOptionChainOpen(false);
              setSelectedStock(null);
            }}
            symbol={selectedStock?.symbol}
            stockData={selectedStock}
          />
        )}
      </Card>
    );
  }
);

StocksListOptimized.displayName = "StocksListOptimized";

export default StocksListOptimized;
