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

GAP_ANALYSIS_TIME = time(9, 15, 0)  # Market opens at 9:15 AM IST
GAP_ANALYSIS_RETRY_TIME = time(9, 20, 0)  # Retry at 9:20 AM if initial run had insufficient data
GAP_ANALYSIS_FINAL_TIME = time(9, 30, 0)  # Final attempt at 9:30 AM
RETENTION_DAYS = 7
MIN_INSTRUMENTS_THRESHOLD = 100  # Minimum instruments with valid data to consider analysis complete


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
    Service for detecting market gaps at market open (9:15 AM IST)

    Workflow:
    1. First attempt at 9:15 AM (market open)
    2. Retry at 9:20 AM if insufficient data (<100 instruments)
    3. Final attempt at 9:30 AM
    4. Calculate gaps based on actual opening prices
    5. Store gap-up and gap-down stocks
    6. Delete old data (>7 days)
    7. Sleep until next day
    """

    def __init__(self):
        self.analysis_time = GAP_ANALYSIS_TIME
        self.retry_time = GAP_ANALYSIS_RETRY_TIME
        self.final_time = GAP_ANALYSIS_FINAL_TIME
        self.last_analysis_date: Optional[date] = None
        self.analysis_completed_today = False
        self.analysis_attempt_count = 0
        self.is_running = False

        logger.info("Gap Detection Service initialized - runs at 9:15 AM IST with retries at 9:20 AM and 9:30 AM")

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

    async def run_gap_analysis(self, force: bool = False) -> Dict[str, Any]:
        """
        Execute gap analysis at market open

        Args:
            force: Force analysis even if already completed today

        Returns:
            Analysis statistics including data quality metrics
        """
        if not force and await self.check_if_analysis_completed_today():
            return {
                "status": "skipped",
                "reason": "already_completed_today",
                "date": date.today().isoformat()
            }

        try:
            from services.realtime_market_engine import get_market_engine
        except ImportError as e:
            raise RuntimeError(f"Market engine not available: {e}")

        self.analysis_attempt_count += 1
        logger.info(f"Starting gap analysis (attempt #{self.analysis_attempt_count})")
        start_time = datetime.now()

        try:
            self.is_running = True
            gap_up_stocks: List[GapAnalysisResult] = []
            gap_down_stocks: List[GapAnalysisResult] = []

            market_engine = get_market_engine()
            all_instruments = market_engine.get_all_instruments()

            total_instruments = len(all_instruments)
            instruments_with_data = 0
            instruments_analyzed = 0

            logger.info(f"Analyzing {total_instruments} instruments for gaps")

            for inst_key, instrument in all_instruments.items():
                try:
                    # Count instruments that have any price data
                    if instrument.current_price > 0 or instrument.open_price > 0:
                        instruments_with_data += 1

                    result = await self._analyze_instrument(instrument)
                    if result:
                        instruments_analyzed += 1
                        if result.gap_type == "GAP_UP":
                            gap_up_stocks.append(result)
                        elif result.gap_type == "GAP_DOWN":
                            gap_down_stocks.append(result)

                except Exception as e:
                    logger.debug(f"Error analyzing {inst_key}: {e}")
                    continue

            gap_up_stocks.sort(key=lambda x: x.gap_percent, reverse=True)
            gap_down_stocks.sort(key=lambda x: x.gap_percent)

            total_gaps_found = len(gap_up_stocks) + len(gap_down_stocks)
            data_quality = (instruments_analyzed / total_instruments * 100) if total_instruments > 0 else 0

            # Only save if we have meaningful data OR it's the final attempt
            should_save = (
                instruments_analyzed >= MIN_INSTRUMENTS_THRESHOLD or
                self.analysis_attempt_count >= 3 or
                force
            )

            saved_count = 0
            if should_save:
                saved_count = await self._save_gaps_to_db(gap_up_stocks, gap_down_stocks)
                self.analysis_completed_today = True
                self.last_analysis_date = start_time.date()
            else:
                logger.warning(
                    f"Insufficient data quality ({instruments_analyzed} instruments analyzed, "
                    f"threshold: {MIN_INSTRUMENTS_THRESHOLD}). Will retry later."
                )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            statistics = {
                "status": "completed" if should_save else "insufficient_data",
                "analysis_date": start_time.date().isoformat(),
                "analysis_time": start_time.time().isoformat(),
                "attempt_number": self.analysis_attempt_count,
                "gap_up_count": len(gap_up_stocks),
                "gap_down_count": len(gap_down_stocks),
                "total_gaps_found": total_gaps_found,
                "total_gaps_stored": saved_count,
                "total_instruments": total_instruments,
                "instruments_with_data": instruments_with_data,
                "instruments_analyzed": instruments_analyzed,
                "data_quality_percent": round(data_quality, 2),
                "duration_seconds": round(duration, 2),
                "will_retry": not should_save
            }

            logger.info(
                f"Gap analysis attempt #{self.analysis_attempt_count}: "
                f"{total_gaps_found} gaps found ({len(gap_up_stocks)} up, {len(gap_down_stocks)} down), "
                f"{instruments_analyzed}/{total_instruments} instruments analyzed ({data_quality:.1f}%), "
                f"{saved_count} stored, duration: {duration:.2f}s"
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

        Uses opening price from actual market data. If open_price is not set,
        uses current_price as fallback (first traded price).

        Args:
            instrument: Instrument from market engine

        Returns:
            GapAnalysisResult or None
        """
        try:
            prev_close = instrument.close_price
            current_price = instrument.current_price

            # Use open_price if available, otherwise use current_price as opening
            # This handles cases where instrument started trading but open_price not set
            open_price = instrument.open_price if instrument.open_price > 0 else current_price

            # Validate required data
            if not prev_close or prev_close <= 0:
                return None

            if not open_price or open_price <= 0:
                return None

            # Skip if current_price is missing (instrument hasn't traded yet)
            if not current_price or current_price <= 0:
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
        Schedule gap analysis at 9:15 AM IST daily with retry logic

        Execution strategy:
        - 9:15 AM: First attempt (market open)
        - 9:20 AM: Retry if insufficient data in first attempt
        - 9:30 AM: Final attempt regardless of data quality
        """
        logger.info(
            f"Gap detection scheduler started - primary: {self.analysis_time}, "
            f"retry: {self.retry_time}, final: {self.final_time}"
        )

        while True:
            try:
                now = datetime.now()
                current_date = now.date()
                current_time = now.time()

                # Reset daily flags on new day
                if self.last_analysis_date != current_date:
                    self.analysis_completed_today = False
                    self.analysis_attempt_count = 0
                    logger.info(f"New trading day: {current_date}")

                # Skip weekends
                if current_date.weekday() >= 5:
                    tomorrow = current_date + timedelta(days=1)
                    next_run_time = datetime.combine(tomorrow, self.analysis_time)
                    wait_seconds = (next_run_time - now).total_seconds()
                    logger.info(f"Weekend - sleeping until {next_run_time}")
                    await asyncio.sleep(wait_seconds)
                    continue

                # Determine next execution time based on current time and completion status
                next_execution_time = None

                if current_time < self.analysis_time:
                    # Before 9:15 AM - wait for first attempt
                    next_execution_time = self.analysis_time
                    logger.info(f"Before market open - waiting for {next_execution_time}")

                elif current_time < self.retry_time:
                    # Between 9:15 and 9:20 - execute if not done
                    if not self.analysis_completed_today:
                        logger.info("Market open time - executing gap analysis (attempt #1)")
                        result = await self.run_gap_analysis()

                        if result.get("status") == "insufficient_data":
                            next_execution_time = self.retry_time
                            logger.info(f"Insufficient data - will retry at {next_execution_time}")
                        else:
                            logger.info("Gap analysis completed successfully")
                            self.last_analysis_date = current_date
                    else:
                        next_execution_time = self.retry_time

                elif current_time < self.final_time:
                    # Between 9:20 and 9:30 - execute retry if not completed
                    if not self.analysis_completed_today:
                        logger.info("Retry time - executing gap analysis (attempt #2)")
                        result = await self.run_gap_analysis()

                        if result.get("status") == "insufficient_data":
                            next_execution_time = self.final_time
                            logger.info(f"Still insufficient data - final attempt at {next_execution_time}")
                        else:
                            logger.info("Gap analysis completed successfully on retry")
                            self.last_analysis_date = current_date
                    else:
                        next_execution_time = self.final_time

                elif current_time >= self.final_time and not self.analysis_completed_today:
                    # After 9:30 - final attempt
                    logger.info("Final attempt time - executing gap analysis (attempt #3)")
                    await self.run_gap_analysis(force=True)  # Force save regardless of quality
                    self.last_analysis_date = current_date
                    logger.info("Gap analysis completed (final attempt)")

                # If analysis is done for today, sleep until tomorrow
                if self.analysis_completed_today or current_time >= self.final_time:
                    tomorrow = current_date + timedelta(days=1)
                    next_run_time = datetime.combine(tomorrow, self.analysis_time)
                    wait_seconds = (next_run_time - datetime.now()).total_seconds()
                    logger.info(f"Analysis complete for today. Sleeping until {next_run_time} ({wait_seconds/3600:.1f}h)")
                    await asyncio.sleep(wait_seconds)
                elif next_execution_time:
                    # Wait until next execution time
                    next_run_time = datetime.combine(current_date, next_execution_time)
                    wait_seconds = (next_run_time - datetime.now()).total_seconds()
                    if wait_seconds > 0:
                        logger.info(f"Waiting {wait_seconds:.0f}s until next attempt at {next_run_time}")
                        await asyncio.sleep(wait_seconds)
                    else:
                        await asyncio.sleep(10)  # Small delay before retry
                else:
                    # Fallback - wait 1 minute
                    await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"Error in scheduler: {e}", exc_info=True)
                await asyncio.sleep(300)  # Wait 5 minutes on error

    def get_analysis_status(self) -> Dict[str, Any]:
        """Get current status including retry information"""
        return {
            "is_running": self.is_running,
            "last_analysis_date": self.last_analysis_date.isoformat() if self.last_analysis_date else None,
            "analysis_completed_today": self.analysis_completed_today,
            "attempt_count": self.analysis_attempt_count,
            "scheduled_times": {
                "primary": self.analysis_time.isoformat(),
                "retry": self.retry_time.isoformat(),
                "final": self.final_time.isoformat()
            },
            "min_instruments_threshold": MIN_INSTRUMENTS_THRESHOLD
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