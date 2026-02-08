import React, { useMemo } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from "@mui/material";

/**
 * Enhanced Option Chain Table
 * Optimized for high-speed updates and professional broker-like visualization.
 * Uses CSS classes from OptionChainOverrides.css for maximum visibility.
 */
const EnhancedOptionChainTable = ({
  optionChainData,
  getLivePrice,
  getLivePriceData,
  highlightATM = true,
}) => {
  // Format helpers
  const formatPrice = (val) => (val ? `₹${val.toFixed(2)}` : "–");
  const formatChange = (val) =>
    val ? `${val > 0 ? "+" : ""}${val.toFixed(2)}` : "0.00";
  const formatNumber = (val) => (val ? val.toLocaleString("en-IN") : "–");

  // Sort strikes
  const sortedStrikes = useMemo(() => {
    if (!optionChainData?.options) return [];
    return Object.keys(optionChainData.options)
      .map(Number)
      .sort((a, b) => a - b);
  }, [optionChainData]);

  // Find ATM strike
  const atmStrike = useMemo(() => {
    if (!optionChainData?.spot_price || sortedStrikes.length === 0) return null;
    const spot = optionChainData.spot_price;
    return sortedStrikes.reduce((prev, curr) =>
      Math.abs(curr - spot) < Math.abs(prev - spot) ? curr : prev,
    );
  }, [optionChainData, sortedStrikes]);

  if (!optionChainData) return null;

  return (
    <TableContainer
      component={Paper}
      className="option-chain-container"
      sx={{ maxHeight: "75vh" }}
    >
      <Table stickyHeader size="small" className="option-chain-table">
        <TableHead>
          <TableRow>
            <TableCell
              align="center"
              colSpan={5}
              className="option-chain-header-call"
            >
              CALLS
            </TableCell>
            <TableCell align="center" className="option-chain-header-strike">
              STRIKE
            </TableCell>
            <TableCell
              align="center"
              colSpan={5}
              className="option-chain-header-put"
            >
              PUTS
            </TableCell>
          </TableRow>
          <TableRow>
            {/* CALL HEADERS */}
            <TableCell align="right">OI</TableCell>
            <TableCell align="right">Vol</TableCell>
            <TableCell align="right">IV</TableCell>
            <TableCell align="right">LTP</TableCell>
            <TableCell align="right">Net Chg</TableCell>

            {/* STRIKE HEADER */}
            <TableCell align="center">Price</TableCell>

            {/* PUT HEADERS */}
            <TableCell align="left">Net Chg</TableCell>
            <TableCell align="left">LTP</TableCell>
            <TableCell align="left">IV</TableCell>
            <TableCell align="left">Vol</TableCell>
            <TableCell align="left">OI</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {sortedStrikes.map((strike) => {
            const data = optionChainData.options[strike];
            const ce = data.CE || {};
            const pe = data.PE || {};

            // Get live updates or fallback to static
            const ceLtp =
              getLivePrice(ce.instrument_key) || ce.market_data?.ltp;
            const peLtp =
              getLivePrice(pe.instrument_key) || pe.market_data?.ltp;

            const ceLive = getLivePriceData(ce.instrument_key) || {};
            const peLive = getLivePriceData(pe.instrument_key) || {};

            const isATM = strike === atmStrike;

            // Determine change classes
            const ceChangeClass =
              (ceLive.change || 0) > 0
                ? "option-chain-cell-change-positive"
                : (ceLive.change || 0) < 0
                  ? "option-chain-cell-change-negative"
                  : "option-chain-cell-neutral";

            const peChangeClass =
              (peLive.change || 0) > 0
                ? "option-chain-cell-change-positive"
                : (peLive.change || 0) < 0
                  ? "option-chain-cell-change-negative"
                  : "option-chain-cell-neutral";

            return (
              <TableRow key={strike} className="option-chain-row">
                {/* CALL DATA */}
                <TableCell align="right">
                  <span className="option-chain-cell-neutral">
                    {formatNumber(ce.market_data?.oi)}
                  </span>
                </TableCell>
                <TableCell align="right">
                  <span className="option-chain-cell-neutral">
                    {formatNumber(ceLive.volume || ce.market_data?.volume)}
                  </span>
                </TableCell>
                <TableCell align="right">
                  <span className="option-chain-cell-neutral">
                    {ce.option_greeks?.iv?.toFixed(1) || "0.0"}
                  </span>
                </TableCell>
                <TableCell align="right">
                  <span className="option-chain-cell-ltp">
                    {formatPrice(ceLtp)}
                  </span>
                </TableCell>
                <TableCell align="right">
                  <span className={ceChangeClass}>
                    {formatChange(ceLive.change)}
                  </span>
                </TableCell>

                {/* STRIKE PRICE */}
                <TableCell align="center" className="option-chain-strike-cell">
                  {strike} {isATM && "(ATM)"}
                </TableCell>

                {/* PUT DATA */}
                <TableCell align="left">
                  <span className={peChangeClass}>
                    {formatChange(peLive.change)}
                  </span>
                </TableCell>
                <TableCell align="left">
                  <span className="option-chain-cell-ltp">
                    {formatPrice(peLtp)}
                  </span>
                </TableCell>
                <TableCell align="left">
                  <span className="option-chain-cell-neutral">
                    {pe.option_greeks?.iv?.toFixed(1) || "0.0"}
                  </span>
                </TableCell>
                <TableCell align="left">
                  <span className="option-chain-cell-neutral">
                    {formatNumber(peLive.volume || pe.market_data?.volume)}
                  </span>
                </TableCell>
                <TableCell align="left">
                  <span className="option-chain-cell-neutral">
                    {formatNumber(pe.market_data?.oi)}
                  </span>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default EnhancedOptionChainTable;
