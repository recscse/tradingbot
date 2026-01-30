import React from "react";
import { 
  Activity, 
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Lightbulb
} from "lucide-react";
import { motion } from "framer-motion";

const PortfolioHealthIndicator = ({ portfolioData, tradingStats }) => {
  // Calculate portfolio health metrics
  const calculateHealthScore = () => {
    let score = 0;
    let factors = [];

    // Diversification score (30%)
    const brokerCount = portfolioData?.brokerAccounts?.length || 0;
    const diversificationScore = Math.min(brokerCount * 20, 30);
    score += diversificationScore;
    factors.push({
      name: "Broker Mix",
      score: diversificationScore,
      max: 30,
      status: diversificationScore >= 20 ? "good" : "warning"
    });

    // Performance consistency (25%)
    const winRate = tradingStats?.win_rate || 0;
    const consistencyScore = Math.min(winRate * 0.25, 25);
    score += consistencyScore;
    factors.push({
      name: "Win Consistency",
      score: consistencyScore,
      max: 25,
      status: consistencyScore >= 15 ? "good" : "warning"
    });

    // Risk management (25%)
    const avgTradeSize = tradingStats?.avg_trade_value || 0;
    const totalPortfolio = tradingStats?.total_portfolio_value || 1;
    const riskRatio = avgTradeSize / totalPortfolio;
    const riskScore = riskRatio < 0.05 ? 25 : riskRatio < 0.1 ? 20 : 15;
    score += riskScore;
    factors.push({
      name: "Risk Control",
      score: riskScore,
      max: 25,
      status: riskScore >= 20 ? "good" : "warning"
    });

    // Activity level (20%)
    const totalTrades = tradingStats?.total_trades || 0;
    const activityScore = Math.min(totalTrades * 0.2, 20);
    score += activityScore;
    factors.push({
      name: "Execution",
      score: activityScore,
      max: 20,
      status: activityScore >= 15 ? "good" : "warning"
    });

    return { score: Math.round(score), factors };
  };

  const { score, factors } = calculateHealthScore();

  const getHealthMeta = (score) => {
    if (score >= 80) return { label: "EXCELLENT", color: "tw-text-emerald-600", bg: "tw-bg-emerald-50", icon: CheckCircle2 };
    if (score >= 60) return { label: "STABLE", color: "tw-text-blue-600", bg: "tw-bg-blue-50", icon: Activity };
    if (score >= 40) return { label: "AVERAGE", color: "tw-text-amber-600", bg: "tw-bg-amber-50", icon: AlertTriangle };
    return { label: "CRITICAL", color: "tw-text-rose-600", bg: "tw-bg-rose-50", icon: XCircle };
  };

  const meta = getHealthMeta(score);
  const Icon = meta.icon;

  return (
    <div className="tw-space-y-6">
      <div className="tw-flex tw-items-center tw-justify-between">
        <div className="tw-flex tw-items-center tw-gap-4">
          <div className={`tw-p-3 tw-rounded-2xl ${meta.bg} ${meta.color} tw-shadow-sm`}>
            <Icon className="tw-w-6 tw-h-6" />
          </div>
          <div>
            <div className="tw-text-3xl tw-font-black tw-text-slate-900 tw-dark:text-white tw-tracking-tighter">
              {score}<span className="tw-text-sm tw-text-slate-400 tw-ml-1">/100</span>
            </div>
            <div className={`tw-text-[10px] tw-font-black tw-uppercase tw-tracking-widest ${meta.color}`}>
              {meta.label}
            </div>
          </div>
        </div>
      </div>

      <div className="tw-space-y-4">
        {factors.map((factor, idx) => (
          <div key={idx} className="tw-space-y-1.5">
            <div className="tw-flex tw-justify-between tw-text-[10px] tw-font-bold tw-uppercase tw-tracking-tighter">
              <span className="tw-text-slate-500">{factor.name}</span>
              <span className={factor.status === 'good' ? 'tw-text-emerald-600' : 'tw-text-amber-600'}>
                {factor.score}/{factor.max}
              </span>
            </div>
            <div className="tw-h-1 tw-w-full tw-bg-slate-100 tw-dark:bg-slate-800 tw-rounded-full tw-overflow-hidden">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${(factor.score / factor.max) * 100}%` }}
                className={`tw-h-full ${factor.status === 'good' ? 'tw-bg-emerald-500' : 'tw-bg-amber-500'}`}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="tw-mt-6 tw-p-4 tw-rounded-2xl tw-bg-indigo-50/50 tw-dark:tw-bg-indigo-950/20 tw-border tw-border-indigo-100 tw-dark:tw-border-indigo-900/30">
        <div className="tw-flex tw-items-center tw-gap-2 tw-mb-2">
          <Lightbulb className="tw-w-4 tw-h-4 tw-text-indigo-600" />
          <span className="tw-text-xs tw-font-black tw-text-indigo-900 tw-dark:text-indigo-300 tw-uppercase tw-tracking-tight">Strategy Tip</span>
        </div>
        <p className="tw-text-[11px] tw-font-medium tw-text-indigo-700 tw-dark:text-indigo-400 tw-leading-relaxed">
          {score < 80 ? "Diversifying your broker accounts can reduce platform-specific risk and improve overall capital efficiency." : "Your portfolio health is in the top tier. Maintain current risk parameters for long-term consistency."}
        </p>
      </div>
    </div>
  );
};

export default PortfolioHealthIndicator;
