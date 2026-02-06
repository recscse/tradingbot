import React, { useEffect, useRef } from 'react';
import { createChart, ColorType } from 'lightweight-charts';

/**
 * Production-grade TradingView Chart Component
 * 
 * Features:
 * - Real-time price action rendering
 * - Dynamic Trade Markers (Entry, Stop Loss, Target)
 * - Automatic resizing and scaling
 * - Optimized for high-frequency updates
 */
const TradingViewChart = ({ data, markers = [], height = 300 }) => {
    const chartContainerRef = useRef();
    const chartRef = useRef();
    const seriesRef = useRef();
    
    // Persistent Line Refs for dynamic updates (trailing SL)
    const lineRefs = useRef({
        entry: null,
        sl: null,
        target: null
    });

    useEffect(() => {
        if (!chartContainerRef.current) return;

        // Initialize Chart
        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#94a3b8',
            },
            grid: {
                vertLines: { color: 'rgba(30, 41, 59, 0.5)' },
                horzLines: { color: 'rgba(30, 41, 59, 0.5)' },
            },
            rightPriceScale: {
                borderColor: 'rgba(71, 85, 105, 0.5)',
                autoScale: true,
            },
            timeScale: {
                borderColor: 'rgba(71, 85, 105, 0.5)',
                timeVisible: true,
                secondsVisible: false,
            },
            handleScroll: true,
            handleScale: true,
        });

        const series = chart.addAreaSeries({
            lineColor: '#06b6d4',
            topColor: 'rgba(6, 182, 212, 0.2)',
            bottomColor: 'rgba(6, 182, 212, 0.0)',
            lineWidth: 2,
            priceFormat: { precision: 2, minMove: 0.05 },
        });

        chartRef.current = chart;
        seriesRef.current = series;

        // Resize handler
        const handleResize = () => {
            chart.applyOptions({ width: chartContainerRef.current.clientWidth });
        };
        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, []);

    // Handle Price Data Updates
    useEffect(() => {
        if (seriesRef.current && data) {
            // lightweight-charts needs { time, value }
            seriesRef.current.update({
                time: data.time || Math.floor(Date.now() / 1000),
                value: data.value
            });
        }
    }, [data]);

    // Handle Trade Markers (Entry, SL, Target)
    useEffect(() => {
        if (!seriesRef.current || !markers || markers.length === 0) {
            // Cleanup existing lines if no markers provided
            Object.values(lineRefs.current).forEach(line => {
                if (line) seriesRef.current.removePriceLine(line);
            });
            return;
        }

        const currentMarker = markers[0]; // Primary position

        // 1. Entry Line (Cyan)
        if (!lineRefs.current.entry) {
            lineRefs.current.entry = seriesRef.current.createPriceLine({
                price: currentMarker.entry,
                color: '#0ea5e9',
                lineWidth: 2,
                lineStyle: 2, // Dashed
                axisLabelVisible: true,
                title: 'ENTRY',
            });
        }

        // 2. Target Line (Emerald)
        if (!lineRefs.current.target && currentMarker.target > 0) {
            lineRefs.current.target = seriesRef.current.createPriceLine({
                price: currentMarker.target,
                color: '#10b981',
                lineWidth: 2,
                lineStyle: 2,
                axisLabelVisible: true,
                title: 'TARGET',
            });
        }

        // 3. Stop Loss Line (Rose) - This one updates frequently (TRAILING)
        if (!lineRefs.current.sl) {
            lineRefs.current.sl = seriesRef.current.createPriceLine({
                price: currentMarker.sl,
                color: '#f43f5e',
                lineWidth: 2,
                lineStyle: 0, // Solid
                axisLabelVisible: true,
                title: 'STOP LOSS',
            });
        } else {
            // MOVE THE LINE if SL has changed
            lineRefs.current.sl.applyOptions({ price: currentMarker.sl });
        }

    }, [markers]);

    return (
        <div className="tw-relative tw-w-full">
            <div ref={chartContainerRef} style={{ height: `${height}px` }} />
        </div>
    );
};

export default TradingViewChart;
