#!/usr/bin/env python3
"""
Gap Detection Service - Executes at 9:08 AM IST

Simple gap detection: Calculate if stocks opened with gap up or gap down.
Store results in database. Keep last 7 days of data.

Gap Detection Logic:
- Gap % = ((Open - Previous Close) / Previous Close) * 100
- GAP_UP: Gap > +0.5%
- GAP_DOWN: Gap < -0.5%
- NO_GAP: Gap between -0.5% and +0.5% (not stored)

Architecture:
- Gets snapshot of all instruments at 9:08 AM from market engine
- Calculates gaps for each instrument
- Stores only GAP_UP and GAP_DOWN in database
- Deletes entries older than 7 days
- Runs once per day, sleeps until next day
"""

import asyncio
import logging
from datetime import datetime, date, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from database.connection import get_db
from database.models import PremarketCandle

logger = logging.getLogger(__name__)

GAP_ANALYSIS_TIME = time(9, 8, 0)
RETENTION_DAYS = 7


@dataclass
class GapAnalysisResult:
    """Result of gap analysis for a single instrument"""
    instrument_key: str
    symbol: str
    exchange: str
    open_price: Decimal
    prev_close: Decimal
    gap_percent: Decimal
    gap_type: str
    volume: int
    sector: str
    market_cap: int


class GapDetectionService:
    """
    Service for detecting market gaps at 9:08 AM IST

    Simple workflow:
    1. Get all instruments from market engine
    2. Calculate gaps
    3. Store gap-up and gap-down stocks
    4. Delete old data (>7 days)
    5. Sleep until next day
    """

    def __init__(self):
        self.analysis_time = GAP_ANALYSIS_TIME
        self.last_analysis_date: Optional[date] = None
        self.analysis_completed_today = False
        self.is_running = False

        logger.info("Gap Detection Service initialized")

    def calculate_gap_percentage(
        self,
        open_price: Decimal,
        prev_close: Decimal
    ) -> Decimal:
        """
        Calculate gap percentage

        Args:
            open_price: Opening price
            prev_close: Previous close price

        Returns:
            Gap percentage

        Raises:
            ValueError: If prev_close is invalid
        """
        if not prev_close or prev_close <= 0:
            raise ValueError(f"Invalid previous close: {prev_close}")

        gap_pct = ((open_price - prev_close) / prev_close) * 100
        return gap_pct.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def determine_gap_type(self, gap_percent: Decimal) -> str:
        """
        Determine gap type

        Args:
            gap_percent: Gap percentage

        Returns:
            "GAP_UP", "GAP_DOWN", or "NO_GAP"
        """
        if gap_percent > Decimal('0.5'):
            return "GAP_UP"
        elif gap_percent < Decimal('-0.5'):
            return "GAP_DOWN"
        else:
            return "NO_GAP"

    def determine_gap_strength(self, gap_percent: Decimal) -> str:
        """
        Determine gap strength

        Args:
            gap_percent: Gap percentage

        Returns:
            "WEAK", "MODERATE", "STRONG", or "VERY_STRONG"
        """
        abs_gap = abs(gap_percent)

        if abs_gap >= Decimal('8.0'):
            return "VERY_STRONG"
        elif abs_gap >= Decimal('5.0'):
            return "STRONG"
        elif abs_gap >= Decimal('2.5'):
            return "MODERATE"
        else:
            return "WEAK"

    def get_market_cap_category(self, market_cap: int) -> str:
        """
        Get market cap category

        Args:
            market_cap: Market cap value

        Returns:
            "LARGE_CAP", "MID_CAP", or "SMALL_CAP"
        """
        if market_cap >= 20000_00_00_000:
            return "LARGE_CAP"
        elif market_cap >= 5000_00_00_000:
            return "MID_CAP"
        else:
            return "SMALL_CAP"

    async def check_if_analysis_completed_today(self) -> bool:
        """
        Check if gap analysis already done today

        Returns:
            True if already completed, False otherwise
        """
        db: Optional[Session] = None

        try:
            db = next(get_db())
            today = date.today()

            count = db.query(func.count(PremarketCandle.id)).filter(
                PremarketCandle.candle_date == today
            ).scalar()

            if count > 0:
                logger.info(f"Gap analysis already done for {today} ({count} records)")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking if analysis completed: {e}")
            return False
        finally:
            if db:
                db.close()

    async def delete_old_entries(self, db: Session) -> int:
        """
        Delete gap entries older than 7 days

        Args:
            db: Database session

        Returns:
            Number of deleted entries
        """
        try:
            cutoff_date = date.today() - timedelta(days=RETENTION_DAYS)

            deleted_count = db.query(PremarketCandle).filter(
                PremarketCandle.candle_date < cutoff_date
            ).delete()

            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old gap entries (before {cutoff_date})")

            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting old entries: {e}")
            return 0

    async def run_gap_analysis(self) -> Dict[str, Any]:
        """
        Execute gap analysis at 9:08 AM

        Returns:
            Analysis statistics
        """
        if await self.check_if_analysis_completed_today():
            return {
                "status": "skipped",
                "reason": "already_completed_today",
                "date": date.today().isoformat()
            }

        try:
            from services.realtime_market_engine import get_market_engine
        except ImportError as e:
            raise RuntimeError(f"Market engine not available: {e}")

        logger.info("Starting gap analysis at 9:08 AM")
        start_time = datetime.now()

        try:
            self.is_running = True
            gap_up_stocks: List[GapAnalysisResult] = []
            gap_down_stocks: List[GapAnalysisResult] = []

            market_engine = get_market_engine()
            all_instruments = market_engine.get_all_instruments()

            logger.info(f"Analyzing {len(all_instruments)} instruments for gaps")

            for inst_key, instrument in all_instruments.items():
                try:
                    result = await self._analyze_instrument(instrument)
                    if result:
                        if result.gap_type == "GAP_UP":
                            gap_up_stocks.append(result)
                        elif result.gap_type == "GAP_DOWN":
                            gap_down_stocks.append(result)

                except Exception as e:
                    logger.debug(f"Error analyzing {inst_key}: {e}")
                    continue

            gap_up_stocks.sort(key=lambda x: x.gap_percent, reverse=True)
            gap_down_stocks.sort(key=lambda x: x.gap_percent)

            saved_count = await self._save_gaps_to_db(gap_up_stocks, gap_down_stocks)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            self.analysis_completed_today = True
            self.last_analysis_date = start_time.date()

            statistics = {
                "status": "completed",
                "analysis_date": start_time.date().isoformat(),
                "gap_up_count": len(gap_up_stocks),
                "gap_down_count": len(gap_down_stocks),
                "total_gaps_stored": saved_count,
                "duration_seconds": round(duration, 2)
            }

            logger.info(
                f"Gap analysis complete: {saved_count} gaps stored "
                f"({len(gap_up_stocks)} up, {len(gap_down_stocks)} down) "
                f"in {duration:.2f}s"
            )

            return statistics

        except Exception as e:
            logger.error(f"Error during gap analysis: {e}", exc_info=True)
            raise
        finally:
            self.is_running = False

    async def _analyze_instrument(self, instrument) -> Optional[GapAnalysisResult]:
        """
        Analyze single instrument for gap

        Args:
            instrument: Instrument from market engine

        Returns:
            GapAnalysisResult or None
        """
        try:
            open_price = instrument.open_price
            prev_close = instrument.close_price
            current_price = instrument.current_price

            if not all([open_price, prev_close, current_price]):
                return None

            if prev_close <= 0 or open_price <= 0:
                return None

            open_price_decimal = Decimal(str(open_price))
            prev_close_decimal = Decimal(str(prev_close))

            gap_percent = self.calculate_gap_percentage(
                open_price_decimal,
                prev_close_decimal
            )
            gap_type = self.determine_gap_type(gap_percent)

            if gap_type == "NO_GAP":
                return None

            result = GapAnalysisResult(
                instrument_key=instrument.instrument_key,
                symbol=instrument.symbol,
                exchange=instrument.exchange,
                open_price=open_price_decimal,
                prev_close=prev_close_decimal,
                gap_percent=gap_percent,
                gap_type=gap_type,
                volume=int(instrument.volume) if instrument.volume else 0,
                sector=instrument.sector,
                market_cap=instrument.market_cap
            )

            return result

        except Exception as e:
            logger.debug(f"Error analyzing {instrument.instrument_key}: {e}")
            return None

    async def _save_gaps_to_db(
        self,
        gap_up_stocks: List[GapAnalysisResult],
        gap_down_stocks: List[GapAnalysisResult]
    ) -> int:
        """
        Save all gaps to database and delete old entries

        Args:
            gap_up_stocks: List of gap-up stocks
            gap_down_stocks: List of gap-down stocks

        Returns:
            Number of records saved
        """
        db: Optional[Session] = None

        try:
            db = next(get_db())
            analysis_time = datetime.now()
            saved_count = 0

            await self.delete_old_entries(db)

            all_gaps = gap_up_stocks + gap_down_stocks

            for result in all_gaps:
                try:
                    gap_strength = self.determine_gap_strength(result.gap_percent)
                    market_cap_category = self.get_market_cap_category(result.market_cap)

                    record = PremarketCandle(
                        symbol=result.symbol,
                        instrument_key=result.instrument_key,
                        exchange=result.exchange,
                        candle_date=analysis_time.date(),
                        candle_start_time=analysis_time,
                        candle_end_time=analysis_time,
                        open_price=result.open_price,
                        high_price=result.open_price,
                        low_price=result.open_price,
                        close_price=result.open_price,
                        total_volume=result.volume,
                        total_trades=0,
                        avg_price=result.open_price,
                        previous_close=result.prev_close,
                        gap_percentage=result.gap_percent,
                        gap_type=result.gap_type,
                        gap_strength=gap_strength,
                        volume_ratio=Decimal('1.0'),
                        volume_confirmation=False,
                        ticks_received=0,
                        data_quality_score=Decimal('1.0'),
                        sector=result.sector,
                        market_cap_category=market_cap_category,
                        is_significant_gap=abs(result.gap_percent) >= Decimal('1.0')
                    )

                    db.add(record)
                    saved_count += 1

                except Exception as e:
                    logger.debug(f"Skipped {result.symbol}: {e}")
                    continue

            db.commit()
            logger.info(f"Saved {saved_count} gap records to database")

            return saved_count

        except Exception as e:
            if db:
                db.rollback()
            logger.error(f"Error saving gaps to database: {e}")
            raise
        finally:
            if db:
                db.close()

    async def schedule_gap_analysis(self) -> None:
        """
        Schedule gap analysis at 9:08 AM IST daily

        Waits until 9:08 AM, executes once, then sleeps until next day.
        """
        logger.info(f"Gap detection scheduler started - runs at {self.analysis_time}")

        while True:
            try:
                now = datetime.now()
                current_date = now.date()
                current_time = now.time()

                if self.last_analysis_date != current_date:
                    self.analysis_completed_today = False

                if current_date.weekday() >= 5:
                    tomorrow = current_date + timedelta(days=1)
                    next_run_time = datetime.combine(tomorrow, self.analysis_time)
                    wait_seconds = (next_run_time - now).total_seconds()
                    logger.info(f"Weekend - sleeping until {next_run_time}")
                    await asyncio.sleep(wait_seconds)
                    continue

                if current_time < self.analysis_time:
                    next_run_time = datetime.combine(current_date, self.analysis_time)
                    wait_seconds = (next_run_time - now).total_seconds()
                    logger.info(f"Waiting {wait_seconds:.0f}s until gap analysis at {next_run_time}")
                    await asyncio.sleep(wait_seconds)
                    continue

                if not self.analysis_completed_today:
                    logger.info("Executing gap analysis NOW")
                    await self.run_gap_analysis()
                    self.last_analysis_date = current_date

                tomorrow = current_date + timedelta(days=1)
                next_run_time = datetime.combine(tomorrow, self.analysis_time)
                wait_seconds = (next_run_time - datetime.now()).total_seconds()
                logger.info(f"Done. Sleeping until {next_run_time} ({wait_seconds/3600:.1f}h)")
                await asyncio.sleep(wait_seconds)

            except Exception as e:
                logger.error(f"Error in scheduler: {e}", exc_info=True)
                await asyncio.sleep(300)

    def get_analysis_status(self) -> Dict[str, Any]:
        """Get current status"""
        return {
            "is_running": self.is_running,
            "last_analysis_date": self.last_analysis_date.isoformat() if self.last_analysis_date else None,
            "analysis_completed_today": self.analysis_completed_today,
            "scheduled_time": self.analysis_time.isoformat()
        }


gap_detection_service = GapDetectionService()


def get_gap_detection_service() -> GapDetectionService:
    """Get singleton instance"""
    return gap_detection_service


async def start_gap_detection_scheduler() -> None:
    """Start scheduler as background task"""
    await gap_detection_service.schedule_gap_analysis()


async def get_todays_gap_analysis(
    gap_type: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get today's gap analysis from database

    Args:
        gap_type: Filter by "GAP_UP" or "GAP_DOWN"
        limit: Max results (None for all)

    Returns:
        List of gap results
    """
    db: Optional[Session] = None

    try:
        db = next(get_db())

        query = db.query(PremarketCandle).filter(
            PremarketCandle.candle_date == date.today()
        )

        if gap_type:
            query = query.filter(PremarketCandle.gap_type == gap_type)

        query = query.order_by(desc(func.abs(PremarketCandle.gap_percentage)))

        if limit:
            query = query.limit(limit)

        candles = query.all()

        results = []
        for candle in candles:
            results.append({
                "symbol": candle.symbol,
                "instrument_key": candle.instrument_key,
                "gap_type": candle.gap_type,
                "gap_percentage": float(candle.gap_percentage or 0),
                "gap_strength": candle.gap_strength,
                "open_price": float(candle.open_price),
                "previous_close": float(candle.previous_close or 0),
                "volume": candle.total_volume,
                "sector": candle.sector,
                "market_cap": candle.market_cap_category,
                "timestamp": candle.created_at.isoformat() if candle.created_at else None
            })

        return results

    except Exception as e:
        logger.error(f"Error getting gap analysis: {e}")
        return []
    finally:
        if db:
            db.close()