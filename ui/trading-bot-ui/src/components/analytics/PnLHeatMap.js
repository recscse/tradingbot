import React, { useMemo } from 'react';
import { Tooltip } from 'react-tooltip';
import 'react-tooltip/dist/react-tooltip.css';

const PnLHeatMap = ({ dailyData, startDate }) => {
  // Generate calendar grid
  const calendarData = useMemo(() => {
    if (!dailyData || dailyData.length === 0) return [];

    // Sort data by date
    const sortedData = [...dailyData].sort((a, b) => new Date(a.date) - new Date(b.date));
    
    // Map dates to PnL
    const pnlMap = {};
    sortedData.forEach(day => {
      pnlMap[day.date] = day.pnl;
    });

    // Create 6-month or 1-year view depending on data
    // For now, let's just show the range present in the data plus padding
    const firstDate = new Date(sortedData[0].date);
    const lastDate = new Date(sortedData[sortedData.length - 1].date);
    
    // Start from the beginning of the week of the first date
    const start = new Date(firstDate);
    start.setDate(start.getDate() - start.getDay()); // Sunday start

    // End at the end of the week of the last date
    const end = new Date(lastDate);
    end.setDate(end.getDate() + (6 - end.getDay())); // Saturday end

    const weeks = [];
    let current = new Date(start);
    let currentWeek = [];

    while (current <= end) {
      const dateStr = current.toISOString().split('T')[0];
      const pnl = pnlMap[dateStr] !== undefined ? pnlMap[dateStr] : null;
      
      currentWeek.push({
        date: dateStr,
        pnl: pnl,
        day: current.getDay(), // 0 = Sunday
        month: current.toLocaleString('default', { month: 'short' })
      });

      if (current.getDay() === 6) {
        weeks.push(currentWeek);
        currentWeek = [];
      }

      current.setDate(current.getDate() + 1);
    }

    return weeks;
  }, [dailyData]);

  const getColor = (pnl) => {
    if (pnl === null) return 'tw-bg-slate-800/50';
    if (pnl === 0) return 'tw-bg-slate-700';
    
    // Green shades for profit
    if (pnl > 0) {
      if (pnl > 5000) return 'tw-bg-emerald-400';
      if (pnl > 2000) return 'tw-bg-emerald-500';
      if (pnl > 1000) return 'tw-bg-emerald-600';
      return 'tw-bg-emerald-700';
    }
    
    // Red shades for loss
    if (pnl < -5000) return 'tw-bg-rose-400';
    if (pnl < -2000) return 'tw-bg-rose-500';
    if (pnl < -1000) return 'tw-bg-rose-600';
    return 'tw-bg-rose-700';
  };

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val || 0);
  };

  if (!dailyData || dailyData.length === 0) {
    return (
      <div className="tw-bg-slate-900/30 tw-backdrop-blur-xl tw-border tw-border-slate-800/50 tw-rounded-2xl tw-p-6 tw-flex tw-items-center tw-justify-center tw-h-48">
        <p className="tw-text-slate-500">No trading data available for heat map</p>
      </div>
    );
  }

  return (
    <div className="tw-bg-slate-900/30 tw-backdrop-blur-xl tw-border tw-border-slate-800/50 tw-rounded-2xl tw-p-6 tw-shadow-xl tw-overflow-x-auto">
      <h2 className="tw-text-xl tw-font-bold tw-text-white tw-mb-4">Net Realised P&L</h2>
      
      <div className="tw-flex tw-gap-1 tw-min-w-max">
        {/* Day labels column */}
        <div className="tw-flex tw-flex-col tw-gap-1 tw-mt-0 tw-mr-2">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, i) => (
            <span key={day} className={`tw-text-[10px] tw-h-3 tw-leading-3 ${i % 2 === 0 ? 'tw-text-slate-500' : 'tw-text-transparent'}`}>
              {day}
            </span>
          ))}
        </div>

        {/* Weeks columns */}
        {calendarData.map((week, weekIdx) => (
          <div key={weekIdx} className="tw-flex tw-flex-col tw-gap-1">
            {/* Days cells */}
            {week.map((day) => (
              <div
                key={day.date}
                data-tooltip-id="heatmap-tooltip"
                data-tooltip-content={`${day.date}: ${day.pnl !== null ? formatCurrency(day.pnl) : 'No trades'}`}
                className={`tw-w-3 tw-h-3 tw-rounded-sm tw-transition-all hover:tw-ring-2 hover:tw-ring-offset-1 hover:tw-ring-offset-slate-900 hover:tw-ring-slate-500 ${getColor(day.pnl)}`}
              />
            ))}
            
            {/* Month Label (at bottom) */}
            <div className="tw-h-4 tw-mt-1">
              {week[0].day === 0 && week[0].date.endsWith('01') || (weekIdx === 0) || (week[0].month !== calendarData[weekIdx-1]?.[0]?.month) ? (
                <span className="tw-text-[10px] tw-text-slate-400 tw-font-medium tw-uppercase">{week[0].month}</span>
              ) : null}
            </div>
          </div>
        ))}
      </div>

      <Tooltip 
        id="heatmap-tooltip" 
        className="tw-z-50 !tw-bg-slate-800 !tw-text-white !tw-px-3 !tw-py-2 !tw-rounded-lg !tw-text-xs !tw-border !tw-border-slate-700 !tw-shadow-xl"
        render={({ content }) => {
          if (!content) return null;
          const [date, val] = content.split(': ');
          return (
            <div className="tw-text-center">
              <div className="tw-text-slate-400 tw-mb-1">{date}</div>
              <div className={`tw-font-bold ${val.includes('-') ? 'tw-text-rose-400' : val === 'No trades' ? 'tw-text-slate-300' : 'tw-text-emerald-400'}`}>
                {val === 'No trades' ? val : `Realised P&L: ${val}`}
              </div>
            </div>
          );
        }}
      />
      
      <div className="tw-mt-2 tw-flex tw-items-center tw-gap-4 tw-text-xs tw-text-slate-400">
        <span>Less</span>
        <div className="tw-flex tw-gap-1">
          <div className="tw-w-3 tw-h-3 tw-rounded-sm tw-bg-rose-700"></div>
          <div className="tw-w-3 tw-h-3 tw-rounded-sm tw-bg-rose-500"></div>
          <div className="tw-w-3 tw-h-3 tw-rounded-sm tw-bg-slate-800/50"></div>
          <div className="tw-w-3 tw-h-3 tw-rounded-sm tw-bg-emerald-500"></div>
          <div className="tw-w-3 tw-h-3 tw-rounded-sm tw-bg-emerald-700"></div>
        </div>
        <span>More</span>
      </div>
    </div>
  );
};

export default PnLHeatMap;
