// components/dashboard/SectorHeatmapWidget.jsx
import React, { useMemo } from "react";
import { motion } from "framer-motion";
import { 
  Zap, 
  Activity, 
  TrendingUp, 
  TrendingDown, 
  Cpu, 
  Pill, 
  Car, 
  ShoppingCart, 
  Hammer, 
  Home, 
  Signal, 
  Tv, 
  Landmark, 
  Banknote,
  Droplets
} from "lucide-react";

const SectorHeatmapWidget = ({ data, isLoading, height = "tw-h-[350px]" }) => {
  // Process sector data - MUST be before any early returns
  const sectorData = useMemo(() => {
    if (!data || !data.sectors) return [];

    return Object.entries(data.sectors).map(([sectorName, sectorInfo]) => ({
      name: sectorName,
      change: sectorInfo.change_percent || 0,
      value: sectorInfo.market_cap || sectorInfo.volume || 100,
      stocks_count: sectorInfo.stocks_count || 0,
      top_performer: sectorInfo.top_performer || null,
      worst_performer: sectorInfo.worst_performer || null,
      avg_volume_ratio: sectorInfo.avg_volume_ratio || 1,
    }));
  }, [data]);

  // Fallback data if no real data is available
  const fallbackSectors = [
    { name: "BANKING", change: 2.35, value: 850, stocks_count: 45, avg_volume_ratio: 1.2 },
    { name: "IT", change: -1.25, value: 720, stocks_count: 32, avg_volume_ratio: 0.9 },
    { name: "PHARMA", change: 3.45, value: 340, stocks_count: 28, avg_volume_ratio: 1.4 },
    { name: "AUTO", change: -2.15, value: 280, stocks_count: 22, avg_volume_ratio: 1.1 },
    { name: "FMCG", change: 0.85, value: 420, stocks_count: 18, avg_volume_ratio: 0.8 },
    { name: "METALS", change: 4.25, value: 190, stocks_count: 25, avg_volume_ratio: 1.8 },
    { name: "ENERGY", change: -0.95, value: 380, stocks_count: 15, avg_volume_ratio: 1.3 },
    { name: "REALTY", change: 1.75, value: 120, stocks_count: 35, avg_volume_ratio: 2.1 },
    { name: "TELECOM", change: -1.85, value: 95, stocks_count: 8, avg_volume_ratio: 0.7 },
    { name: "MEDIA", change: 2.95, value: 65, stocks_count: 12, avg_volume_ratio: 1.5 },
    { name: "PSU", change: 1.45, value: 240, stocks_count: 28, avg_volume_ratio: 1.6 },
    { name: "FINANCE", change: -0.65, value: 520, stocks_count: 38, avg_volume_ratio: 1.0 },
  ];

  const sectors = sectorData.length > 0 ? sectorData : fallbackSectors;
  const sortedSectors = [...sectors].sort((a, b) => b.change - a.change);

  // Get sector icon
  const getSectorIcon = (sectorName) => {
    const name = sectorName.toUpperCase();
    const props = { className: "tw-w-5 tw-h-5 tw-mb-1" };
    
    const iconMap = {
      BANKING: <Landmark {...props} />,
      IT: <Cpu {...props} />,
      PHARMA: <Pill {...props} />,
      AUTO: <Car {...props} />,
      FMCG: <ShoppingCart {...props} />,
      METALS: <Hammer {...props} />,
      ENERGY: <Zap {...props} />,
      REALTY: <Home {...props} />,
      TELECOM: <Signal {...props} />,
      MEDIA: <Tv {...props} />,
      PSU: <Landmark {...props} />,
      FINANCE: <Banknote {...props} />,
      CHEMICALS: <Droplets {...props} />,
    };
    return iconMap[name] || <Activity {...props} />;
  };

  const getPerformanceColor = (change) => {
    if (change > 2) return "tw-text-emerald-400 tw-bg-emerald-500/10 tw-border-emerald-500/30";
    if (change > 0) return "tw-text-emerald-300 tw-bg-emerald-500/5 tw-border-emerald-500/20";
    if (change < -2) return "tw-text-rose-400 tw-bg-rose-500/10 tw-border-rose-500/30";
    if (change < 0) return "tw-text-rose-300 tw-bg-rose-500/5 tw-border-rose-500/20";
    return "tw-text-slate-300 tw-bg-slate-500/5 tw-border-slate-500/20";
  };

  if (isLoading) {
    return (
      <div className={`tw-bg-slate-900/50 tw-backdrop-blur-xl tw-border tw-border-slate-700/50 tw-rounded-2xl tw-p-6 ${height} tw-flex tw-items-center tw-justify-center`}>
        <div className="tw-flex tw-flex-col tw-items-center tw-gap-3">
          <div className="tw-animate-spin tw-rounded-full tw-h-8 tw-w-8 tw-border-b-2 tw-border-cyan-500"></div>
          <span className="tw-text-slate-400 tw-text-sm">Loading sector heatmap...</span>
        </div>
      </div>
    );
  }

  const advancing = sectors.filter((s) => s.change > 0).length;
  const declining = sectors.filter((s) => s.change < 0).length;
  const isBullish = advancing > declining;

  return (
    <div className={`tw-bg-slate-900/50 tw-backdrop-blur-xl tw-border tw-border-slate-700/50 tw-rounded-2xl tw-p-6 tw-flex tw-flex-col ${height} tw-overflow-hidden`}>
      {/* Header */}
      <div className="tw-flex tw-items-center tw-justify-between tw-mb-4">
        <h3 className="tw-text-lg tw-font-bold tw-text-white tw-flex tw-items-center tw-gap-2">
          <span className="tw-p-1.5 tw-bg-amber-500/10 tw-rounded-lg tw-border tw-border-amber-500/20">
            <Activity className="tw-w-4 tw-h-4 tw-text-amber-400" />
          </span>
          Sector Heatmap
        </h3>
        
        <div className="tw-flex tw-items-center tw-gap-3 tw-text-xs">
          <div className="tw-flex tw-items-center tw-gap-1.5">
            <span className="tw-w-2 tw-h-2 tw-rounded-full tw-bg-emerald-500"></span>
            <span className="tw-text-slate-400">{advancing} Adv</span>
          </div>
          <div className="tw-flex tw-items-center tw-gap-1.5">
            <span className="tw-w-2 tw-h-2 tw-rounded-full tw-bg-rose-500"></span>
            <span className="tw-text-slate-400">{declining} Dec</span>
          </div>
        </div>
      </div>

      {/* Grid Content */}
      <div className="tw-flex-1 tw-overflow-y-auto tw-pr-2 tw-scrollbar-thin tw-scrollbar-thumb-slate-700 tw-scrollbar-track-transparent">
        <div className="tw-grid tw-grid-cols-2 sm:tw-grid-cols-3 lg:tw-grid-cols-4 tw-gap-3">
          {sortedSectors.map((sector, index) => (
            <motion.div
              key={sector.name}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              whileHover={{ scale: 1.02, y: -2 }}
              className={`tw-relative tw-p-3 tw-rounded-xl tw-border tw-transition-all tw-cursor-default tw-group ${getPerformanceColor(sector.change)}`}
            >
              {/* Hot Indicator */}
              {sector.avg_volume_ratio > 1.5 && (
                <div className="tw-absolute tw-top-2 tw-right-2 tw-animate-pulse">
                  <Zap className="tw-w-3 tw-h-3 tw-text-amber-400" fill="currentColor" />
                </div>
              )}

              <div className="tw-flex tw-flex-col tw-items-center tw-text-center">
                <div className="tw-opacity-80 group-hover:tw-opacity-100 tw-transition-opacity">
                  {getSectorIcon(sector.name)}
                </div>
                
                <h4 className="tw-text-[10px] tw-font-bold tw-uppercase tw-tracking-wider tw-opacity-70 tw-mb-1">
                  {sector.name}
                </h4>
                
                <div className="tw-text-lg tw-font-bold tw-flex tw-items-center tw-gap-1">
                  {sector.change > 0 ? (
                    <TrendingUp className="tw-w-3 tw-h-3" />
                  ) : (
                    <TrendingDown className="tw-w-3 tw-h-3" />
                  )}
                  {Math.abs(sector.change).toFixed(2)}%
                </div>
                
                <div className="tw-mt-2 tw-w-full tw-flex tw-justify-between tw-text-[10px] tw-opacity-60 tw-border-t tw-border-current/10 tw-pt-2">
                  <span>{sector.stocks_count} Stocks</span>
                  <span>{sector.avg_volume_ratio.toFixed(1)}x Vol</span>
                </div>
              </div>

              {/* Hover Details */}
              <div className="tw-absolute tw-inset-0 tw-bg-slate-900/95 tw-backdrop-blur-sm tw-opacity-0 group-hover:tw-opacity-100 tw-transition-opacity tw-flex tw-flex-col tw-items-center tw-justify-center tw-p-2 tw-text-center tw-z-10 tw-rounded-xl">
                {sector.top_performer && (
                  <div className="tw-mb-2">
                    <div className="tw-text-[9px] tw-text-emerald-400 tw-uppercase">Top Pick</div>
                    <div className="tw-text-xs tw-font-bold tw-text-white">{sector.top_performer}</div>
                  </div>
                )}
                {sector.worst_performer && (
                  <div>
                    <div className="tw-text-[9px] tw-text-rose-400 tw-uppercase">Lagging</div>
                    <div className="tw-text-xs tw-font-bold tw-text-white">{sector.worst_performer}</div>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="tw-mt-4 tw-pt-3 tw-border-t tw-border-slate-700/50 tw-flex tw-items-center tw-justify-between tw-text-[10px] tw-text-slate-500">
        <span>Updated: {new Date().toLocaleTimeString()}</span>
        <div className="tw-flex tw-items-center tw-gap-1">
          <span>Market Breadth:</span>
          <span className={`tw-font-bold ${isBullish ? 'tw-text-emerald-400' : 'tw-text-rose-400'}`}>
            {isBullish ? 'BULLISH' : 'BEARISH'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default SectorHeatmapWidget;