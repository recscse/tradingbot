import { useState, useEffect, useCallback } from "react";
import { tradingApiService } from "../services/tradingApiService";

export const useMarketAnalytics = () => {
  const [topMovers, setTopMovers] = useState({ gainers: [], losers: [] });
  const [volumeAnalysis, setVolumeAnalysis] = useState({
    volume_leaders: [],
    unusual_volume: [],
  });
  const [marketSentiment, setMarketSentiment] = useState({});
  const [intradayStocks, setIntradayStocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchTopMovers = useCallback(async (limit = 20) => {
    try {
      const data = await tradingApiService.getTopMovers(limit);
      setTopMovers({
        gainers: data.gainers || [],
        losers: data.losers || [],
      });
      setLastUpdate(new Date());
    } catch (err) {
      setError("Failed to fetch top movers");
      console.error("Error fetching top movers:", err);
    }
  }, []);

  const fetchVolumeAnalysis = useCallback(async (limit = 50) => {
    try {
      const data = await tradingApiService.getVolumeAnalysis(limit);
      setVolumeAnalysis(data);
      setLastUpdate(new Date());
    } catch (err) {
      setError("Failed to fetch volume analysis");
      console.error("Error fetching volume analysis:", err);
    }
  }, []);

  const fetchMarketSentiment = useCallback(async () => {
    try {
      const data = await tradingApiService.getMarketSentiment();
      setMarketSentiment(data);
      setLastUpdate(new Date());
    } catch (err) {
      setError("Failed to fetch market sentiment");
      console.error("Error fetching market sentiment:", err);
    }
  }, []);

  const fetchIntradayStocks = useCallback(
    async (minChange = 2.0, minVolume = 100000) => {
      try {
        const data = await tradingApiService.getIntradayStocks(
          minChange,
          minVolume
        );
        setIntradayStocks(data.intraday_stocks || []);
        setLastUpdate(new Date());
      } catch (err) {
        setError("Failed to fetch intraday stocks");
        console.error("Error fetching intraday stocks:", err);
      }
    },
    []
  );

  const fetchAllData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      await Promise.all([
        fetchTopMovers(),
        fetchVolumeAnalysis(),
        fetchMarketSentiment(),
        fetchIntradayStocks(),
      ]);
    } catch (err) {
      setError("Failed to fetch analytics data");
    } finally {
      setLoading(false);
    }
  }, [
    fetchTopMovers,
    fetchVolumeAnalysis,
    fetchMarketSentiment,
    fetchIntradayStocks,
  ]);

  useEffect(() => {
    fetchAllData();

    // Setup real-time updates
    tradingApiService.subscribeToAnalytics((data) => {
      if (data.type === "analytics_update" && data.data) {
        if (data.data.top_movers) {
          setTopMovers(data.data.top_movers);
        }
        if (data.data.market_sentiment) {
          setMarketSentiment(data.data.market_sentiment);
        }
        setLastUpdate(new Date());
      }
    });

    return () => {
      tradingApiService.disconnectWebSocket();
    };
  }, [fetchAllData]);

  return {
    topMovers,
    volumeAnalysis,
    marketSentiment,
    intradayStocks,
    loading,
    error,
    lastUpdate,
    refetch: fetchAllData,
    fetchTopMovers,
    fetchVolumeAnalysis,
    fetchMarketSentiment,
    fetchIntradayStocks,
  };
};

export const useHeatmapData = (
  viewType = "sector",
  sizeMetric = "market_cap",
  colorMetric = "change_percent"
) => {
  const [heatmapData, setHeatmapData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHeatmapData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await tradingApiService.getLiveHeatmapData(
        viewType,
        sizeMetric,
        colorMetric
      );
      setHeatmapData(data.heatmap_data);
    } catch (err) {
      setError("Failed to fetch heatmap data");
      console.error("Error fetching heatmap data:", err);
    } finally {
      setLoading(false);
    }
  }, [viewType, sizeMetric, colorMetric]);

  useEffect(() => {
    fetchHeatmapData();
  }, [fetchHeatmapData]);

  return {
    heatmapData,
    loading,
    error,
    refetch: fetchHeatmapData,
  };
};
