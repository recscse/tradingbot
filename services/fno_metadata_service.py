"""
F&O Metadata Service - Phase 2 Implementation

Manages F&O stock metadata including:
- Fibonacci strategy scores and technical analysis
- Option liquidity validation and scoring  
- Index membership and sector classification
- Historical selection performance tracking
- Quality grading (A+, A, B+, B, C) based on suitability

This service works with auto_stock_selection_service to provide
enhanced F&O stock selection with database persistence.
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

# Database imports
from database.connection import SessionLocal
from database.models import FNOStockMetadata, FNOSelectionHistory, User

# Service imports
from services.auto_stock_selection_service import auto_stock_selection_service
from services.enhanced_market_analytics import enhanced_analytics

logger = logging.getLogger(__name__)

class FNOMetadataService:
    """
    F&O Metadata Management Service
    
    Handles database operations for F&O stock metadata including:
    - Technical score calculations and caching
    - Option liquidity monitoring
    - Quality grading and ranking
    - Selection history tracking
    - Performance analytics
    """
    
    def __init__(self):
        self.selection_service = auto_stock_selection_service
        self.analytics = enhanced_analytics
        
        # Quality grade thresholds
        self.quality_thresholds = {
            'A+': {'fibonacci_score': 0.8, 'liquidity_score': 0.8, 'volume_min': 1000000},
            'A':  {'fibonacci_score': 0.7, 'liquidity_score': 0.7, 'volume_min': 500000},
            'B+': {'fibonacci_score': 0.6, 'liquidity_score': 0.6, 'volume_min': 200000},
            'B':  {'fibonacci_score': 0.5, 'liquidity_score': 0.5, 'volume_min': 100000},
            'C':  {'fibonacci_score': 0.0, 'liquidity_score': 0.0, 'volume_min': 0}
        }
        
        logger.info("✅ FNOMetadataService initialized")
    
    async def update_all_fno_metadata(self) -> Dict[str, Any]:
        """
        Update metadata for all F&O stocks (scheduled daily at 9 PM)
        
        Returns:
            Dict with update statistics
        """
        logger.info("🔄 Starting comprehensive F&O metadata update...")
        
        start_time = datetime.now()
        stats = {
            'total_stocks': 0,
            'updated_stocks': 0,
            'new_stocks': 0,
            'failed_updates': 0,
            'fibonacci_friendly': 0,
            'quality_grades': {'A+': 0, 'A': 0, 'B+': 0, 'B': 0, 'C': 0},
            'processing_time_seconds': 0
        }
        
        try:
            # Get all F&O stocks from indices
            fno_stocks = await self.selection_service.get_fno_stocks_from_indices()
            stats['total_stocks'] = len(fno_stocks)
            
            logger.info(f"📊 Found {len(fno_stocks)} F&O stocks to update")
            
            db = SessionLocal()
            try:
                for stock_data in fno_stocks:
                    try:
                        symbol = stock_data['symbol']
                        
                        # Check if metadata already exists
                        existing = db.query(FNOStockMetadata).filter(
                            FNOStockMetadata.symbol == symbol
                        ).first()
                        
                        if existing:
                            # Update existing metadata
                            updated = await self._update_stock_metadata(db, existing, stock_data)
                            if updated:
                                stats['updated_stocks'] += 1
                        else:
                            # Create new metadata
                            created = await self._create_stock_metadata(db, stock_data)
                            if created:
                                stats['new_stocks'] += 1
                        
                        # Update quality grade statistics
                        current_stock = db.query(FNOStockMetadata).filter(
                            FNOStockMetadata.symbol == symbol
                        ).first()
                        
                        if current_stock:
                            if current_stock.is_fibonacci_friendly:
                                stats['fibonacci_friendly'] += 1
                            
                            grade = current_stock.quality_grade or 'C'
                            stats['quality_grades'][grade] += 1
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to update metadata for {stock_data.get('symbol', 'Unknown')}: {e}")
                        stats['failed_updates'] += 1
                
                db.commit()
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Database transaction failed: {e}")
            finally:
                db.close()
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            stats['processing_time_seconds'] = round(processing_time, 2)
            
            logger.info(f"✅ F&O metadata update completed in {processing_time:.2f}s")
            logger.info(f"📈 Results: {stats['updated_stocks']} updated, {stats['new_stocks']} new, "
                       f"{stats['fibonacci_friendly']} Fibonacci-friendly")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ F&O metadata update failed: {e}")
            return stats
    
    async def _update_stock_metadata(self, db: Session, metadata: FNOStockMetadata, 
                                   stock_data: Dict[str, Any]) -> bool:
        """Update existing stock metadata"""
        try:
            symbol = stock_data['symbol']
            
            # Update basic market data
            metadata.current_price = stock_data.get('current_price', 0)
            metadata.price_change_percent = stock_data.get('change_percent', 0)
            metadata.avg_daily_volume = stock_data.get('avg_volume_30d', 0)
            metadata.market_cap = stock_data.get('market_cap', 0)
            metadata.sector = stock_data.get('sector', 'Unknown')
            
            # Update index membership
            metadata.index_membership = stock_data.get('index_membership', [])
            metadata.primary_index = stock_data['index_membership'][0] if stock_data.get('index_membership') else None
            
            # Calculate and update technical scores
            scores = await self._calculate_comprehensive_scores(symbol)
            
            metadata.fibonacci_respect_score = scores.get('fibonacci_respect', 0.5)
            metadata.swing_clarity_score = scores.get('swing_clarity', 0.5)
            metadata.ema_alignment_score = scores.get('ema_alignment', 0.5)
            metadata.overall_fibonacci_score = scores.get('overall_fibonacci', 0.5)
            
            # Update option liquidity scores
            liquidity_data = await self.selection_service.validate_option_liquidity(symbol)
            metadata.option_liquidity_score = 1.0 if liquidity_data['is_liquid'] else 0.0
            metadata.ce_liquidity_score = liquidity_data.get('liquid_ce_strikes', 0) / 10.0  # Normalize
            metadata.pe_liquidity_score = liquidity_data.get('liquid_pe_strikes', 0) / 10.0  # Normalize
            metadata.liquid_strikes_count = liquidity_data.get('liquid_ce_strikes', 0) + liquidity_data.get('liquid_pe_strikes', 0)
            metadata.total_option_oi = liquidity_data.get('total_ce_oi', 0) + liquidity_data.get('total_pe_oi', 0)
            metadata.last_liquidity_check = datetime.now()
            
            # Calculate quality grade
            metadata.quality_grade = self._calculate_quality_grade(metadata)
            metadata.is_fibonacci_friendly = self._is_fibonacci_friendly(metadata)
            
            # Update timestamps
            metadata.updated_at = datetime.now()
            metadata.last_analysis_date = date.today()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update metadata for {stock_data.get('symbol')}: {e}")
            return False
    
    async def _create_stock_metadata(self, db: Session, stock_data: Dict[str, Any]) -> bool:
        """Create new stock metadata"""
        try:
            symbol = stock_data['symbol']
            
            # Calculate comprehensive scores
            scores = await self._calculate_comprehensive_scores(symbol)
            
            # Get option liquidity data
            liquidity_data = await self.selection_service.validate_option_liquidity(symbol)
            
            # Create new metadata record
            metadata = FNOStockMetadata(
                # Basic identification
                symbol=symbol,
                company_name=stock_data.get('company_name', symbol),
                sector=stock_data.get('sector', 'Unknown'),
                industry=stock_data.get('industry', 'Unknown'),
                
                # Index membership
                index_membership=stock_data.get('index_membership', []),
                primary_index=stock_data['index_membership'][0] if stock_data.get('index_membership') else None,
                
                # F&O contract details (placeholder values - should be updated from broker data)
                lot_size=stock_data.get('lot_size', 1),
                tick_size=0.05,
                instrument_type='EQ',
                
                # Market data
                avg_daily_volume=stock_data.get('avg_volume_30d', 0),
                market_cap=stock_data.get('market_cap', 0),
                current_price=stock_data.get('current_price', 0),
                price_change_percent=stock_data.get('change_percent', 0),
                
                # Option liquidity scores
                option_liquidity_score=1.0 if liquidity_data['is_liquid'] else 0.0,
                ce_liquidity_score=min(liquidity_data.get('liquid_ce_strikes', 0) / 10.0, 1.0),
                pe_liquidity_score=min(liquidity_data.get('liquid_pe_strikes', 0) / 10.0, 1.0),
                liquid_strikes_count=liquidity_data.get('liquid_ce_strikes', 0) + liquidity_data.get('liquid_pe_strikes', 0),
                total_option_oi=liquidity_data.get('total_ce_oi', 0) + liquidity_data.get('total_pe_oi', 0),
                last_liquidity_check=datetime.now(),
                
                # Fibonacci strategy scores
                fibonacci_respect_score=scores.get('fibonacci_respect', 0.5),
                swing_clarity_score=scores.get('swing_clarity', 0.5),
                ema_alignment_score=scores.get('ema_alignment', 0.5),
                overall_fibonacci_score=scores.get('overall_fibonacci', 0.5),
                
                # Technical metrics (placeholder - should be calculated)
                volatility_30d=0.25,  # Default 25% volatility
                avg_true_range=0.0,
                beta_vs_nifty=1.0,
                correlation_nifty=0.7,
                
                # Initialize tracking fields
                times_selected=0,
                selection_success_rate=0.0,
                avg_holding_period_hours=0.0,
                
                # Status flags
                is_active_fno=True,
                is_fibonacci_friendly=False,  # Will be calculated
                last_analysis_date=date.today()
            )
            
            # Calculate quality grade and Fibonacci friendliness
            metadata.quality_grade = self._calculate_quality_grade(metadata)
            metadata.is_fibonacci_friendly = self._is_fibonacci_friendly(metadata)
            
            db.add(metadata)
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create metadata for {stock_data.get('symbol')}: {e}")
            return False
    
    async def _calculate_comprehensive_scores(self, symbol: str) -> Dict[str, float]:
        """Calculate comprehensive technical scores for a symbol"""
        try:
            # Use existing methods from auto_stock_selection_service
            swing_clarity = await self.selection_service._calculate_swing_clarity(symbol)
            ema_alignment = await self.selection_service._check_ema_alignment(symbol)
            fibonacci_respect = await self.selection_service._historical_fibonacci_respect(symbol)
            
            # Calculate overall Fibonacci score
            overall_fibonacci = (swing_clarity + ema_alignment + fibonacci_respect) / 3
            
            return {
                'swing_clarity': swing_clarity,
                'ema_alignment': ema_alignment,
                'fibonacci_respect': fibonacci_respect,
                'overall_fibonacci': overall_fibonacci
            }
            
        except Exception as e:
            logger.error(f"❌ Score calculation failed for {symbol}: {e}")
            return {
                'swing_clarity': 0.5,
                'ema_alignment': 0.5,
                'fibonacci_respect': 0.5,
                'overall_fibonacci': 0.5
            }
    
    def _calculate_quality_grade(self, metadata: FNOStockMetadata) -> str:
        """Calculate quality grade based on multiple factors"""
        try:
            fibonacci_score = float(metadata.overall_fibonacci_score or 0)
            liquidity_score = float(metadata.option_liquidity_score or 0)
            volume = int(metadata.avg_daily_volume or 0)
            
            # Check against thresholds (highest grade first)
            for grade, thresholds in self.quality_thresholds.items():
                if (fibonacci_score >= thresholds['fibonacci_score'] and
                    liquidity_score >= thresholds['liquidity_score'] and
                    volume >= thresholds['volume_min']):
                    return grade
            
            return 'C'  # Default grade
            
        except Exception:
            return 'C'
    
    def _is_fibonacci_friendly(self, metadata: FNOStockMetadata) -> bool:
        """Determine if stock is Fibonacci-friendly"""
        try:
            config = self.selection_service.fno_selection_config['fibonacci_criteria']
            
            swing_clarity = float(metadata.swing_clarity_score or 0)
            ema_alignment = float(metadata.ema_alignment_score or 0)
            fibonacci_respect = float(metadata.fibonacci_respect_score or 0)
            
            return (swing_clarity >= config['min_swing_clarity'] and
                   ema_alignment >= config['min_ema_alignment'] and
                   fibonacci_respect >= config['min_fib_respect'])
            
        except Exception:
            return False
    
    async def get_fibonacci_friendly_stocks(self, min_quality_grade: str = 'B', 
                                          limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get Fibonacci-friendly stocks with specified minimum quality grade
        
        Args:
            min_quality_grade: Minimum quality grade (A+, A, B+, B, C)
            limit: Maximum number of stocks to return
            
        Returns:
            List of stock metadata dicts
        """
        try:
            # Grade hierarchy for filtering
            grade_hierarchy = ['A+', 'A', 'B+', 'B', 'C']
            min_grade_index = grade_hierarchy.index(min_quality_grade)
            allowed_grades = grade_hierarchy[:min_grade_index + 1]
            
            db = SessionLocal()
            try:
                stocks = db.query(FNOStockMetadata).filter(
                    and_(
                        FNOStockMetadata.is_fibonacci_friendly == True,
                        FNOStockMetadata.is_active_fno == True,
                        FNOStockMetadata.quality_grade.in_(allowed_grades)
                    )
                ).order_by(
                    desc(FNOStockMetadata.overall_fibonacci_score),
                    desc(FNOStockMetadata.option_liquidity_score)
                ).limit(limit).all()
                
                result = []
                for stock in stocks:
                    result.append({
                        'symbol': stock.symbol,
                        'sector': stock.sector,
                        'quality_grade': stock.quality_grade,
                        'fibonacci_score': float(stock.overall_fibonacci_score or 0),
                        'liquidity_score': float(stock.option_liquidity_score or 0),
                        'swing_clarity': float(stock.swing_clarity_score or 0),
                        'ema_alignment': float(stock.ema_alignment_score or 0),
                        'fibonacci_respect': float(stock.fibonacci_respect_score or 0),
                        'current_price': float(stock.current_price or 0),
                        'avg_volume': int(stock.avg_daily_volume or 0),
                        'index_membership': stock.index_membership or [],
                        'times_selected': stock.times_selected or 0,
                        'success_rate': float(stock.selection_success_rate or 0),
                        'last_updated': stock.updated_at.isoformat() if stock.updated_at else None
                    })
                
                logger.info(f"✅ Retrieved {len(result)} Fibonacci-friendly stocks with grade >= {min_quality_grade}")
                return result
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Failed to get Fibonacci-friendly stocks: {e}")
            return []
    
    async def log_selection_result(self, selection_data: Dict[str, Any]) -> bool:
        """
        Log stock selection result to history table
        
        Args:
            selection_data: Selection result data including scores and context
            
        Returns:
            bool: True if logged successfully
        """
        try:
            db = SessionLocal()
            try:
                history = FNOSelectionHistory(
                    selection_date=selection_data.get('selection_date', date.today()),
                    user_id=selection_data.get('user_id', 1),
                    session_type=selection_data.get('session_type', 'PREMARKET'),
                    
                    # Stock information
                    symbol=selection_data['symbol'],
                    selection_score=selection_data.get('selection_score', 0.0),
                    selection_rank=selection_data.get('selection_rank', 1),
                    
                    # Market context
                    market_sentiment=selection_data.get('market_sentiment', 'NEUTRAL'),
                    nifty_change_percent=selection_data.get('nifty_change_percent', 0.0),
                    sector_momentum=selection_data.get('sector_momentum', 0.0),
                    
                    # Strategy metrics
                    fibonacci_levels_at_selection=selection_data.get('fibonacci_levels', {}),
                    ema_values_at_selection=selection_data.get('ema_values', {}),
                    price_at_selection=selection_data.get('price_at_selection', 0.0),
                    
                    # Scores
                    technical_score=selection_data.get('technical_score', 0.0),
                    liquidity_score=selection_data.get('liquidity_score', 0.0),
                    market_score=selection_data.get('market_score', 0.0),
                    
                    # Option details
                    option_type_selected=selection_data.get('option_type', 'CE'),
                    atm_strike=selection_data.get('atm_strike', 0.0),
                    option_premium=selection_data.get('option_premium', 0.0),
                    option_liquidity=selection_data.get('option_liquidity', {})
                )
                
                db.add(history)
                db.commit()
                
                logger.info(f"✅ Logged selection result for {selection_data['symbol']}")
                return True
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Failed to log selection result: {e}")
                return False
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Selection logging failed: {e}")
            return False
    
    async def get_stock_performance_stats(self, symbol: str) -> Dict[str, Any]:
        """Get historical performance statistics for a stock"""
        try:
            db = SessionLocal()
            try:
                # Get stock metadata
                metadata = db.query(FNOStockMetadata).filter(
                    FNOStockMetadata.symbol == symbol
                ).first()
                
                if not metadata:
                    return {'error': f'No metadata found for {symbol}'}
                
                # Get selection history
                history = db.query(FNOSelectionHistory).filter(
                    FNOSelectionHistory.symbol == symbol
                ).order_by(desc(FNOSelectionHistory.selection_date)).all()
                
                # Calculate performance statistics
                total_selections = len(history)
                traded_selections = len([h for h in history if h.was_traded])
                profitable_trades = len([h for h in history if h.trade_outcome == 'PROFIT'])
                
                win_rate = (profitable_trades / traded_selections * 100) if traded_selections > 0 else 0
                
                avg_pnl = np.mean([float(h.profit_loss_percent or 0) for h in history if h.profit_loss_percent])
                if np.isnan(avg_pnl):
                    avg_pnl = 0.0
                
                return {
                    'symbol': symbol,
                    'quality_grade': metadata.quality_grade,
                    'fibonacci_score': float(metadata.overall_fibonacci_score or 0),
                    'liquidity_score': float(metadata.option_liquidity_score or 0),
                    'is_fibonacci_friendly': metadata.is_fibonacci_friendly,
                    
                    # Performance stats
                    'total_selections': total_selections,
                    'times_traded': traded_selections,
                    'win_rate_percent': round(win_rate, 2),
                    'avg_pnl_percent': round(avg_pnl, 2),
                    'last_selected': history[0].selection_date.isoformat() if history else None,
                    
                    # Recent performance (last 5 selections)
                    'recent_selections': [
                        {
                            'date': h.selection_date.isoformat(),
                            'score': float(h.selection_score),
                            'was_traded': h.was_traded,
                            'outcome': h.trade_outcome,
                            'pnl_percent': float(h.profit_loss_percent or 0)
                        } for h in history[:5]
                    ]
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Failed to get performance stats for {symbol}: {e}")
            return {'error': str(e)}
    
    async def get_quality_grade_distribution(self) -> Dict[str, Any]:
        """Get distribution of quality grades across all F&O stocks"""
        try:
            db = SessionLocal()
            try:
                # Count by quality grade
                grade_counts = db.query(
                    FNOStockMetadata.quality_grade,
                    func.count(FNOStockMetadata.id)
                ).filter(
                    FNOStockMetadata.is_active_fno == True
                ).group_by(FNOStockMetadata.quality_grade).all()
                
                # Count Fibonacci-friendly stocks
                fibonacci_count = db.query(func.count(FNOStockMetadata.id)).filter(
                    and_(
                        FNOStockMetadata.is_fibonacci_friendly == True,
                        FNOStockMetadata.is_active_fno == True
                    )
                ).scalar() or 0
                
                # Total active F&O stocks
                total_count = db.query(func.count(FNOStockMetadata.id)).filter(
                    FNOStockMetadata.is_active_fno == True
                ).scalar() or 0
                
                distribution = {}
                for grade, count in grade_counts:
                    distribution[grade or 'Unknown'] = count
                
                return {
                    'total_active_fno_stocks': total_count,
                    'fibonacci_friendly_count': fibonacci_count,
                    'fibonacci_friendly_percent': round((fibonacci_count / total_count * 100), 2) if total_count > 0 else 0,
                    'quality_grade_distribution': distribution,
                    'last_updated': datetime.now().isoformat()
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Failed to get quality grade distribution: {e}")
            return {'error': str(e)}

# Global service instance
fno_metadata_service = FNOMetadataService()