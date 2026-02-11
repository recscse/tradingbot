from typing import Dict, List, Optional
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

class OptionsAnalyzer:
    def __init__(self):
        self.min_confidence = 0.7
        self.min_volume = 100
        self.max_iv_percentile = 80

    async def analyze_sector_options(self, sector: str, symbols: List[str]) -> Dict:
        """Analyze options for all stocks in a sector"""
        recommendations = []

        for symbol in symbols:
            try:
                # Get stock data
                stock = yf.Ticker(symbol)
                
                # Get options chain
                expiries = stock.options
                if not expiries:
                    continue

                # Analyze nearest expiry
                nearest_expiry = expiries[0]
                chain = stock.option_chain(nearest_expiry)
                
                # Analyze calls and puts
                call_opportunities = self._analyze_options_chain(
                    chain.calls, 'CALL', symbol, nearest_expiry
                )
                put_opportunities = self._analyze_options_chain(
                    chain.puts, 'PUT', symbol, nearest_expiry
                )
                
                recommendations.extend(call_opportunities + put_opportunities)

            except Exception as e:
                print(f"Error analyzing options for {symbol}: {str(e)}")
                continue

        return {
            "analysis_time": datetime.now().isoformat(),
            "recommendations": sorted(
                recommendations,
                key=lambda x: float(x['confidence'].rstrip('%')),
                reverse=True
            )
        }

    def _analyze_options_chain(
        self,
        chain: pd.DataFrame,
        option_type: str,
        symbol: str,
        expiry: str
    ) -> List[Dict]:
        """Analyze options chain and find trading opportunities"""
        opportunities = []

        for _, option in chain.iterrows():
            try:
                # Basic filters
                if option['volume'] < self.min_volume:
                    continue

                # Calculate metrics
                iv_percentile = self._calculate_iv_percentile(option['impliedVolatility'])
                if iv_percentile > self.max_iv_percentile:
                    continue

                probability = self._calculate_probability(option)
                if probability < self.min_confidence:
                    continue

                risk_reward = self._calculate_risk_reward(option)
                
                opportunities.append({
                    "symbol": symbol,
                    "strike": option['strike'],
                    "type": option_type,
                    "expiry": expiry,
                    "iv": f"{option['impliedVolatility']*100:.2f}%",
                    "confidence": f"{probability*100:.2f}%",
                    "action": "BUY" if probability > 0.8 else "SELL",
                    "risk_reward": f"{risk_reward:.2f}",
                    "volume": option['volume'],
                    "open_interest": option['openInterest']
                })

            except Exception as e:
                print(f"Error analyzing option {symbol} {option_type} {option['strike']}: {str(e)}")
                continue

        return opportunities

    def _calculate_iv_percentile(self, current_iv: float) -> float:
        """Calculate IV percentile - implement your IV ranking logic"""
        # Implement your IV percentile calculation
        return current_iv * 100

    def _calculate_probability(self, option: pd.Series) -> float:
        """Calculate probability of profit"""
        # Implement your probability calculation based on
        # delta, theta, and other Greeks
        return 0.75  # Placeholder

        def _calculate_risk_reward(self, option: pd.Series) -> float:

            """Calculate risk-reward ratio"""

            # Implement your risk-reward calculation

            return 2.0  # Placeholder

    

        def calculate_hedged_position(

            self, 

            primary_option: Dict, 

            chain: pd.DataFrame, 

            strategy_type: str = "SPREAD"

        ) -> Optional[Dict]:

            """

            Identify a hedging leg to create a Delta-Neutral or Risk-Defined position.

            Example: If buying CE (Delta 0.6), sell OTM CE (Delta 0.3) to reduce cost/theta.

            """

            try:

                primary_strike = primary_option['strike']

                option_type = primary_option['type']

                

                # Filter chain for OTM options (Hedge candidates)

                if option_type == 'CALL':

                    hedge_candidates = chain[chain['strike'] > primary_strike].copy()

                else:

                    hedge_candidates = chain[chain['strike'] < primary_strike].copy()

                    

                if hedge_candidates.empty:

                    return None

                    

                # Sort by strike to find nearest appropriate hedge

                # Ideal hedge: 2-3 strikes away for reasonable credit

                if option_type == 'CALL':

                    hedge_candidates.sort_values('strike', ascending=True, inplace=True)

                else:

                    hedge_candidates.sort_values('strike', ascending=False, inplace=True)

                    

                # Select the 2nd or 3rd OTM strike as hedge

                hedge_index = min(2, len(hedge_candidates) - 1)

                hedge_leg = hedge_candidates.iloc[hedge_index]

                

                # Logic: Hedge should reduce Theta decay and Delta exposure

                # Delta Neutral approximation: Combine +0.6 Delta Long with -0.3 Delta Short -> Net +0.3

                

                return {

                    "action": "SELL",

                    "symbol": primary_option['symbol'],

                    "strike": hedge_leg['strike'],

                    "type": option_type,

                    "expiry": primary_option['expiry'],

                    "delta": hedge_leg.get('delta', 0.3), # Placeholder if greek not avail

                    "price": hedge_leg.get('lastPrice', 0),

                    "reason": "Delta/Theta Hedge"

                }

                

            except Exception as e:

                print(f"Error calculating hedge: {e}")

                return None

    