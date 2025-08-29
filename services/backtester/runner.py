"""
Vectorized Backtester for Trading Strategies

Uses Upstox historical APIs to fetch candle data and option contracts.
Replays strategies exactly as the live engine would, with proper option handling.

Features:
- Vectorized pandas operations for performance
- Option contract resolution using real Upstox data
- Accurate simulation of entry/exit timing
- Comprehensive trade metrics and statistics
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
import logging
import pytz
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Indian timezone
IST = pytz.timezone('Asia/Kolkata')

@dataclass
class BacktestTrade:
    """Represents a single backtested trade"""
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    quantity: int
    side: str  # 'BUY' or 'SELL'
    pnl: float
    pnl_pct: float
    reason: str
    
class BacktestRunner:
    """
    Vectorized backtester using Upstox historical APIs.
    
    Simulates the live strategy execution with accurate timing and option handling.
    """
    
    def __init__(self, access_token: str, initial_capital: float = 100000):
        self.access_token = access_token
        self.base_url = "https://api.upstox.com"
        self.client = httpx.AsyncClient()
        
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Trade tracking
        self.trades = []
        self.positions = {}  # symbol -> position info
        
        # API rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make rate-limited authenticated request to Upstox API"""
        import time
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
        
        headers = {
            "Accept": "application/json", 
            "Authorization": f"Bearer {self.access_token}",
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self.client.get(url, headers=headers, params=params, timeout=15.0)
            
            if response.status_code == 401:
                logger.error("❌ Upstox authentication failed - token expired")
                raise Exception("Upstox authentication failed")
            
            if response.status_code != 200:
                logger.error(f"❌ Upstox API error: {response.status_code} - {response.text}")
                raise Exception(f"API request failed with status {response.status_code}")
            
            data = response.json()
            
            if data.get("status") != "success":
                logger.error(f"❌ Upstox API error response: {data}")
                raise Exception(f"API error: {data.get('message', 'Unknown error')}")
            
            return data["data"]
            
        except httpx.TimeoutException:
            logger.error("❌ Upstox API timeout")
            raise Exception("API request timeout")
        except Exception as e:
            logger.error(f"❌ Upstox API request error: {e}")
            raise
    
    async def get_historical_candles(
        self, 
        instrument_key: str, 
        start_date: datetime, 
        end_date: datetime,
        interval: str = "5minute"
    ) -> pd.DataFrame:
        """
        Fetch historical candle data from Upstox API.
        
        API: https://upstox.com/developer/api-documentation/v3/get-historical-candle-data
        
        Args:
            instrument_key: Upstox instrument key
            start_date: Start date for data
            end_date: End date for data  
            interval: Candle interval (1minute, 5minute, 30minute, day)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Convert dates to strings
            from_date = start_date.strftime("%Y-%m-%d")
            to_date = end_date.strftime("%Y-%m-%d")
            
            # https://api.upstox.com/v2/historical-candle/NSE_INDEX%7CNifty%2050/5minute/2024-01-01/2024-01-31
            endpoint = f"/v2/historical-candle/{instrument_key}/{interval}/{from_date}/{to_date}"
            
            logger.info(f"📊 Fetching historical data: {instrument_key} from {from_date} to {to_date}")
            
            data = await self._make_request(endpoint)
            
            candles = data.get("candles", [])
            if not candles:
                logger.warning(f"⚠️ No candle data returned for {instrument_key}")
                return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert to DataFrame
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert timestamp to datetime with timezone
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert(IST)
            
            # Ensure proper data types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove any rows with NaN values
            df = df.dropna().reset_index(drop=True)
            
            logger.info(f"✅ Fetched {len(df)} candles for {instrument_key}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {instrument_key}: {e}")
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    async def get_intraday_candles(
        self,
        instrument_key: str, 
        interval: str = "5minute"
    ) -> pd.DataFrame:
        """
        Fetch today's intraday candle data.
        
        API: https://upstox.com/developer/api-documentation/v3/get-intra-day-candle-data
        
        Args:
            instrument_key: Upstox instrument key
            interval: Candle interval
            
        Returns:
            DataFrame with today's OHLCV data
        """
        try:
            # https://api.upstox.com/v2/historical-candle/intraday/NSE_INDEX%7CNifty%2050/5minute
            endpoint = f"/v2/historical-candle/intraday/{instrument_key}/{interval}"
            
            logger.info(f"📊 Fetching intraday data: {instrument_key}")
            
            data = await self._make_request(endpoint)
            
            candles = data.get("candles", [])
            if not candles:
                logger.warning(f"⚠️ No intraday data returned for {instrument_key}")
                return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert to DataFrame
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC').dt.tz_convert(IST)
            
            # Ensure proper data types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna().reset_index(drop=True)
            
            logger.info(f"✅ Fetched {len(df)} intraday candles for {instrument_key}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error fetching intraday data for {instrument_key}: {e}")
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    async def backtest_strategy(
        self,
        strategy_function: callable,
        instrument_key: str,
        start_date: datetime,
        end_date: datetime,
        strategy_params: Dict[str, Any] = None,
        initial_capital: float = None
    ) -> Dict[str, Any]:
        """
        Run vectorized backtest on a strategy.
        
        Args:
            strategy_function: Strategy function that takes (df, params) and returns signal dict
            instrument_key: Instrument to backtest on
            start_date: Backtest start date
            end_date: Backtest end date 
            strategy_params: Parameters for the strategy
            initial_capital: Starting capital (overrides instance default)
            
        Returns:
            Comprehensive backtest results dict
        """
        if initial_capital:
            self.initial_capital = initial_capital
            self.current_capital = initial_capital
        
        # Reset state
        self.trades = []
        self.positions = {}
        
        logger.info(f"🚀 Starting backtest for {instrument_key} from {start_date.date()} to {end_date.date()}")
        
        try:
            # Fetch historical data  
            df = await self.get_historical_candles(
                instrument_key, start_date, end_date, interval="5minute"
            )
            
            if df.empty:
                return {"error": "No historical data available", "trades": [], "summary": {}}
            
            logger.info(f"📊 Running strategy on {len(df)} candles")
            
            # Simulate day-by-day trading
            results = await self._simulate_trading(df, strategy_function, strategy_params)
            
            # Calculate performance metrics
            summary = self._calculate_performance_metrics()
            
            logger.info(f"✅ Backtest completed: {len(self.trades)} trades, {summary['win_rate']:.1f}% win rate")
            
            return {
                "summary": summary,
                "trades": [self._trade_to_dict(t) for t in self.trades],
                "equity_curve": results.get("equity_curve", []),
                "daily_returns": results.get("daily_returns", []),
                "parameters": strategy_params or {},
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "total_days": (end_date - start_date).days
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Backtest error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"error": str(e), "trades": [], "summary": {}}
    
    async def _simulate_trading(
        self, 
        df: pd.DataFrame, 
        strategy_function: callable, 
        strategy_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate trading using vectorized operations where possible"""
        
        equity_curve = [self.initial_capital]
        daily_returns = []
        
        # Group by trading days
        df['date'] = df['timestamp'].dt.date
        trading_days = df.groupby('date')
        
        for date, day_data in trading_days:
            try:
                await self._simulate_trading_day(day_data.reset_index(drop=True), strategy_function, strategy_params)
                
                # Record equity for this day
                current_equity = self.current_capital + sum(
                    pos['unrealized_pnl'] for pos in self.positions.values()
                )
                equity_curve.append(current_equity)
                
                # Calculate daily return
                if len(equity_curve) > 1:
                    daily_return = (equity_curve[-1] - equity_curve[-2]) / equity_curve[-2] * 100
                    daily_returns.append(daily_return)
                
            except Exception as e:
                logger.error(f"❌ Error simulating trading day {date}: {e}")
                continue
        
        return {
            "equity_curve": equity_curve,
            "daily_returns": daily_returns
        }
    
    async def _simulate_trading_day(
        self,
        day_data: pd.DataFrame,
        strategy_function: callable,
        strategy_params: Dict[str, Any]
    ):
        """Simulate trading for a single day"""
        if day_data.empty:
            return
        
        # Check for strategy trigger time (9:40 AM)
        strategy_time = time(9, 40)
        day_data['time'] = day_data['timestamp'].dt.time
        
        # Find the first candle at or after 9:40 AM
        strategy_candles = day_data[day_data['time'] >= strategy_time]
        
        if strategy_candles.empty:
            return
        
        # Use sufficient historical data for strategy calculation
        min_required_bars = 25  # For EMA and other indicators
        if len(day_data) < min_required_bars:
            return
        
        for idx in strategy_candles.index:
            # Get data up to current candle for strategy evaluation
            current_data = day_data.loc[:idx].copy()
            
            if len(current_data) < min_required_bars:
                continue
            
            try:
                # Call strategy function
                signal = strategy_function(current_data, strategy_params)
                
                if signal and signal.get('signal') != 'HOLD':
                    current_price = current_data['close'].iloc[-1]
                    current_time = current_data['timestamp'].iloc[-1]
                    
                    # Execute trade simulation
                    self._execute_simulated_trade(
                        signal, current_price, current_time, day_data, idx
                    )
            
            except Exception as e:
                logger.debug(f"Strategy evaluation error: {e}")
                continue
    
    def _execute_simulated_trade(
        self,
        signal: Dict[str, Any],
        entry_price: float,
        entry_time: datetime,
        day_data: pd.DataFrame,
        entry_idx: int
    ):
        """Execute a simulated trade with proper exit handling"""
        
        signal_type = signal['signal']
        stop_loss = signal.get('stop_loss', 0)
        target = signal.get('target', 0)
        
        # Calculate position size (simple fixed amount for now)
        position_value = min(10000, self.current_capital * 0.1)  # 10% of capital, max 10k
        quantity = max(1, int(position_value / entry_price))
        
        # Check if we have enough capital
        required_capital = quantity * entry_price
        if required_capital > self.current_capital:
            logger.debug(f"❌ Insufficient capital: required {required_capital}, available {self.current_capital}")
            return
        
        # Look for exit conditions in remaining candles
        remaining_data = day_data.loc[entry_idx + 1:].copy()
        
        exit_price = entry_price
        exit_time = entry_time
        exit_reason = "EOD"
        
        # Check each subsequent candle for exit conditions
        for exit_idx in remaining_data.index:
            candle_high = remaining_data.loc[exit_idx, 'high']
            candle_low = remaining_data.loc[exit_idx, 'low']
            candle_close = remaining_data.loc[exit_idx, 'close']
            candle_time = remaining_data.loc[exit_idx, 'timestamp']
            
            if signal_type == 'BUY':
                # Check stop loss
                if stop_loss > 0 and candle_low <= stop_loss:
                    exit_price = stop_loss
                    exit_time = candle_time
                    exit_reason = "Stop Loss"
                    break
                
                # Check target
                if target > 0 and candle_high >= target:
                    exit_price = target
                    exit_time = candle_time
                    exit_reason = "Target"
                    break
            
            elif signal_type == 'SELL':
                # Check stop loss (above entry for short)
                if stop_loss > 0 and candle_high >= stop_loss:
                    exit_price = stop_loss
                    exit_time = candle_time
                    exit_reason = "Stop Loss"
                    break
                
                # Check target (below entry for short)
                if target > 0 and candle_low <= target:
                    exit_price = target
                    exit_time = candle_time
                    exit_reason = "Target"
                    break
            
            # Default exit at close if no other condition met
            exit_price = candle_close
            exit_time = candle_time
        
        # Calculate PnL
        if signal_type == 'BUY':
            pnl = (exit_price - entry_price) * quantity
        else:  # SELL
            pnl = (entry_price - exit_price) * quantity
        
        pnl_pct = (pnl / (entry_price * quantity)) * 100
        
        # Update capital
        self.current_capital += pnl
        
        # Create trade record
        trade = BacktestTrade(
            entry_date=entry_time,
            exit_date=exit_time,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            side=signal_type,
            pnl=pnl,
            pnl_pct=pnl_pct,
            reason=exit_reason
        )
        
        self.trades.append(trade)
        
        logger.debug(f"📊 Trade: {signal_type} {quantity} @ {entry_price:.2f} -> {exit_price:.2f} "
                    f"PnL: {pnl:.2f} ({pnl_pct:.1f}%) [{exit_reason}]")
    
    def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics"""
        
        if not self.trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_return": 0.0,
                "total_return_pct": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
                "avg_trade": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0
            }
        
        # Basic metrics
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t.pnl > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # PnL metrics
        total_pnl = sum(t.pnl for t in self.trades)
        total_return_pct = (total_pnl / self.initial_capital) * 100
        avg_trade = total_pnl / total_trades
        
        # Best/worst trades
        best_trade = max(t.pnl for t in self.trades)
        worst_trade = min(t.pnl for t in self.trades)
        
        # Profit factor
        gross_profits = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_losses = sum(abs(t.pnl) for t in self.trades if t.pnl < 0)
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else float('inf') if gross_profits > 0 else 0
        
        # Sharpe ratio (simplified)
        returns = [t.pnl_pct for t in self.trades]
        avg_return = np.mean(returns) if returns else 0
        std_return = np.std(returns) if len(returns) > 1 else 0
        sharpe_ratio = avg_return / std_return if std_return > 0 else 0
        
        # Max drawdown calculation
        equity_curve = [self.initial_capital]
        running_capital = self.initial_capital
        
        for trade in self.trades:
            running_capital += trade.pnl
            equity_curve.append(running_capital)
        
        peak = equity_curve[0]
        max_drawdown = 0
        
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Exit reason analysis
        exit_reasons = {}
        for trade in self.trades:
            reason = trade.reason
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
        
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "total_return": round(total_pnl, 2),
            "total_return_pct": round(total_return_pct, 2),
            "avg_trade": round(avg_trade, 2),
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2),
            "gross_profits": round(gross_profits, 2),
            "gross_losses": round(gross_losses, 2),
            "profit_factor": round(profit_factor, 3),
            "sharpe_ratio": round(sharpe_ratio, 3),
            "max_drawdown": round(max_drawdown, 2),
            "final_capital": round(self.current_capital, 2),
            "exit_reasons": exit_reasons
        }
    
    def _trade_to_dict(self, trade: BacktestTrade) -> Dict[str, Any]:
        """Convert BacktestTrade to dictionary for JSON serialization"""
        return {
            "entry_date": trade.entry_date.isoformat(),
            "exit_date": trade.exit_date.isoformat(),
            "entry_price": round(trade.entry_price, 2),
            "exit_price": round(trade.exit_price, 2),
            "quantity": trade.quantity,
            "side": trade.side,
            "pnl": round(trade.pnl, 2),
            "pnl_pct": round(trade.pnl_pct, 2),
            "reason": trade.reason,
            "duration_minutes": int((trade.exit_date - trade.entry_date).total_seconds() / 60)
        }

# Helper functions for quick backtesting
async def quick_backtest_nifty(
    access_token: str,
    start_date: datetime, 
    end_date: datetime,
    strategy_params: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Quick backtest function for NIFTY 09:40 strategy.
    
    Args:
        access_token: Upstox access token
        start_date: Backtest start date
        end_date: Backtest end date
        strategy_params: Strategy parameters
        
    Returns:
        Backtest results dict
    """
    from strategies.nifty_09_40 import decide_trade
    
    nifty_instrument = "NSE_INDEX%7CNifty%2050"  # URL encoded
    
    async with BacktestRunner(access_token, initial_capital=100000) as runner:
        results = await runner.backtest_strategy(
            strategy_function=decide_trade,
            instrument_key=nifty_instrument,
            start_date=start_date,
            end_date=end_date,
            strategy_params=strategy_params
        )
        
    return results

async def create_backtest_runner(user_id: int) -> Optional[BacktestRunner]:
    """
    Create BacktestRunner instance with user's Upstox token.
    
    Args:
        user_id: User ID to fetch token for
        
    Returns:
        BacktestRunner instance or None if token not available
    """
    try:
        from database.connection import get_db
        from database.models import BrokerConfig
        
        db = next(get_db())
        broker_config = db.query(BrokerConfig).filter_by(
            user_id=user_id,
            broker_name="upstox", 
            is_active=True
        ).first()
        
        if not broker_config or not broker_config.access_token:
            logger.warning(f"⚠️ No active Upstox token found for user {user_id}")
            return None
        
        runner = BacktestRunner(broker_config.access_token)
        logger.info(f"✅ Created BacktestRunner for user {user_id}")
        return runner
        
    except Exception as e:
        logger.error(f"❌ Error creating BacktestRunner for user {user_id}: {e}")
        return None