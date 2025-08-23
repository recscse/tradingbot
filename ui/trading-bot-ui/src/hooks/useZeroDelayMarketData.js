// hooks/useZeroDelayMarketData.js
/**
 * 🚀 ZERO-DELAY Market Data Hook
 * 
 * This hook connects directly to the real-time streaming service,
 * bypassing all processing layers to provide ultra-fast market data updates.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const WEBSOCKET_URL = process.env.REACT_APP_API_URL 
    ? `${process.env.REACT_APP_API_URL.replace('http', 'ws')}/api/v1/realtime/stream`
    : 'ws://localhost:8000/api/v1/realtime/stream';

export const useZeroDelayMarketData = (options = {}) => {
    const [marketData, setMarketData] = useState({});
    const [connectionStatus, setConnectionStatus] = useState('disconnected');
    const [streamingStats, setStreamingStats] = useState({});
    const [latency, setLatency] = useState(null);
    const [error, setError] = useState(null);
    
    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const reconnectAttemptsRef = useRef(0);
    const lastPingRef = useRef(null);
    
    const { 
        autoReconnect = true, 
        maxReconnectAttempts = 5,
        reconnectInterval = 3000,
        enableStats = false,
        onDataReceived = null,
        onConnectionChange = null
    } = options;

    const calculateLatency = useCallback((timestamp) => {
        if (timestamp) {
            const now = new Date().toISOString();
            const serverTime = new Date(timestamp);
            const currentTime = new Date(now);
            const latencyMs = currentTime.getTime() - serverTime.getTime();
            setLatency(latencyMs);
            return latencyMs;
        }
        return null;
    }, []);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return; // Already connected
        }

        try {
            setConnectionStatus('connecting');
            setError(null);
            
            console.log('🚀 Connecting to ZERO-DELAY streaming:', WEBSOCKET_URL);
            wsRef.current = new WebSocket(WEBSOCKET_URL);

            wsRef.current.onopen = () => {
                console.log('✅ ZERO-DELAY WebSocket connected');
                setConnectionStatus('connected');
                reconnectAttemptsRef.current = 0;
                
                // Send initial ping to measure latency
                if (wsRef.current.readyState === WebSocket.OPEN) {
                    lastPingRef.current = Date.now();
                    wsRef.current.send(JSON.stringify({ 
                        type: 'ping', 
                        timestamp: new Date().toISOString() 
                    }));
                }
                
                if (onConnectionChange) {
                    onConnectionChange('connected');
                }
            };

            wsRef.current.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    const messageType = data.type;
                    const timestamp = data.timestamp;

                    switch (messageType) {
                        case 'connection_established':
                            console.log('🚀 ZERO-DELAY streaming established:', data.message);
                            setStreamingStats(data.streaming_stats || {});
                            break;

                        case 'live_price_update':
                            // 🚀 CRITICAL: This is the raw market data - process immediately
                            const priceData = data.data || {};
                            const latencyMs = calculateLatency(timestamp);
                            
                            // Update market data state
                            setMarketData(prevData => ({
                                ...prevData,
                                ...priceData,
                                _lastUpdate: timestamp,
                                _latency: latencyMs,
                                _source: 'zero_delay'
                            }));
                            
                            // Callback for custom processing
                            if (onDataReceived) {
                                onDataReceived({
                                    data: priceData,
                                    timestamp,
                                    latency: latencyMs,
                                    source: 'zero_delay'
                                });
                            }
                            
                            console.debug(`⚡ ZERO-DELAY update: ${Object.keys(priceData).length} instruments (${latencyMs}ms)`);
                            break;

                        case 'pong':
                            if (lastPingRef.current) {
                                const roundTripLatency = Date.now() - lastPingRef.current;
                                setLatency(roundTripLatency);
                                console.debug(`🏓 WebSocket latency: ${roundTripLatency}ms`);
                            }
                            break;

                        case 'streaming_stats':
                            setStreamingStats(data.data || {});
                            break;

                        case 'heartbeat':
                            console.debug('💓 Heartbeat received');
                            break;

                        case 'subscription_confirmed':
                            console.log('✅ Subscription confirmed:', data.message);
                            break;

                        default:
                            console.debug('📨 Unknown message type:', messageType, data);
                    }
                } catch (error) {
                    console.error('❌ Error parsing WebSocket message:', error, event.data);
                }
            };

            wsRef.current.onclose = (event) => {
                console.log('🔗 ZERO-DELAY WebSocket closed:', event.code, event.reason);
                setConnectionStatus('disconnected');
                
                if (onConnectionChange) {
                    onConnectionChange('disconnected');
                }

                // Auto-reconnect logic
                if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
                    reconnectAttemptsRef.current += 1;
                    console.log(`🔄 Reconnecting attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts} in ${reconnectInterval}ms`);
                    
                    reconnectTimeoutRef.current = setTimeout(() => {
                        connect();
                    }, reconnectInterval);
                } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
                    setError('Maximum reconnection attempts reached');
                    console.error('❌ Maximum reconnection attempts reached');
                }
            };

            wsRef.current.onerror = (error) => {
                console.error('❌ ZERO-DELAY WebSocket error:', error);
                setError('WebSocket connection error');
                setConnectionStatus('error');
            };

        } catch (error) {
            console.error('❌ Failed to create ZERO-DELAY WebSocket:', error);
            setError(error.message);
            setConnectionStatus('error');
        }
    }, [autoReconnect, maxReconnectAttempts, reconnectInterval, onConnectionChange, onDataReceived, calculateLatency]);

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
        
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        
        setConnectionStatus('disconnected');
        console.log('🔌 ZERO-DELAY WebSocket disconnected');
    }, []);

    const sendMessage = useCallback((message) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(message));
            return true;
        }
        console.warn('⚠️ Cannot send message: WebSocket not connected');
        return false;
    }, []);

    const requestStats = useCallback(() => {
        return sendMessage({ type: 'get_stats' });
    }, [sendMessage]);

    const ping = useCallback(() => {
        lastPingRef.current = Date.now();
        return sendMessage({ type: 'ping', timestamp: new Date().toISOString() });
    }, [sendMessage]);

    // Auto-connect on mount
    useEffect(() => {
        connect();
        
        // Cleanup on unmount
        return () => {
            disconnect();
        };
    }, [connect, disconnect]);

    // Periodic stats requests
    useEffect(() => {
        if (!enableStats || connectionStatus !== 'connected') return;
        
        const statsInterval = setInterval(() => {
            requestStats();
        }, 10000); // Every 10 seconds
        
        return () => clearInterval(statsInterval);
    }, [enableStats, connectionStatus, requestStats]);

    // Periodic ping for latency measurement
    useEffect(() => {
        if (connectionStatus !== 'connected') return;
        
        const pingInterval = setInterval(() => {
            ping();
        }, 5000); // Every 5 seconds
        
        return () => clearInterval(pingInterval);
    }, [connectionStatus, ping]);

    return {
        // Data
        marketData,
        connectionStatus,
        streamingStats,
        latency,
        error,
        
        // Methods
        connect,
        disconnect,
        sendMessage,
        requestStats,
        ping,
        
        // Status checks
        isConnected: connectionStatus === 'connected',
        isConnecting: connectionStatus === 'connecting',
        hasError: !!error,
        
        // Performance metrics
        totalInstruments: Object.keys(marketData).length,
        lastUpdate: marketData._lastUpdate,
        dataSource: 'zero_delay'
    };
};