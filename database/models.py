from datetime import datetime
from sqlalchemy import (
    CheckConstraint,
    Column,
    Index,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
    Date,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =======================
# User & Authentication
# =======================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    role = Column(String, default="trader")  # Options: Admin, Trader, Analyst
    isVerified = Column(Boolean, default=False)
    country_code = Column(String, nullable=True)
    phone_number = Column(String, nullable=True, index=True, unique=True)
    phone_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    failed_login_attempts = Column(Integer, default=0)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    google_id = Column(String, nullable=True, unique=True)
    avatar_url = Column(String, nullable=True)
    auth_provider = Column(String, default="email")  # email, google
    email_verified = Column(Boolean, default=False)
    profile_picture = Column(String, nullable=True)

    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete")
    broker_configs = relationship(
        "BrokerConfig", back_populates="user", cascade="all, delete"
    )
    trading_sessions = relationship(
        "TradingSession", back_populates="user", cascade="all, delete"
    )
    trades = relationship("Trade", back_populates="user", cascade="all, delete")
    orders = relationship("Order", back_populates="user", cascade="all, delete")
    ai_models = relationship("AIModel", back_populates="user", cascade="all, delete")
    strategies = relationship("Strategy", back_populates="user", cascade="all, delete")
    trading_performance = relationship(
        "TradingPerformance", back_populates="user", cascade="all, delete"
    )
    trade_performance = relationship(
        "TradePerformance", back_populates="user", cascade="all, delete"
    )
    trading_config = relationship(
        "UserTradingConfig", back_populates="user", cascade="all, delete", uselist=False
    )
    trading_reports = relationship(
        "TradingReport", back_populates="user", cascade="all, delete"
    )
    historical_data = relationship(
        "HistoricalData", back_populates="user", cascade="all, delete"
    )
    user_capital = relationship(
        "UserCapital", back_populates="user", cascade="all, delete"
    )
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete"
    )
    social_auths = relationship(
        "SocialAuth", back_populates="user", cascade="all, delete"
    )

    auto_trading_sessions = relationship(
        "AutoTradingSession", back_populates="user", cascade="all, delete"
    )
    daily_trading_reports = relationship(
        "DailyTradingReport", back_populates="user", cascade="all, delete"
    )

    # Password Management
    def set_password(self, password):
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters long")
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)


# =======================
# Broker & Configuration
# =======================
class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    broker_name = Column(String, nullable=False)
    account_number = Column(String, unique=True, nullable=False)
    balance = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="accounts")
    trades = relationship("Trade", back_populates="account", cascade="all, delete")
    orders = relationship("Order", back_populates="account", cascade="all, delete")


class BrokerConfig(Base):
    __tablename__ = "broker_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    client_id = Column(String, nullable=True)
    broker_name = Column(String, index=True)
    api_key = Column(String, nullable=True)
    api_secret = Column(String, nullable=True)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    feed_token = Column(String, nullable=True)
    additional_params = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=False)
    access_token_expiry = Column(DateTime, nullable=True)
    last_error_message = Column(String, nullable=True)
    config = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="broker_configs")


# =======================
# AI Model & Prediction Logs
# =======================
class AIModel(Base):
    __tablename__ = "ai_models"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    model_type = Column(String, nullable=True)
    parameters = Column(JSON)
    accuracy = Column(Float, nullable=True)
    training_data_size = Column(Integer, nullable=True)
    last_trained_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="ai_models")
    predictions = relationship(
        "AIPredictionLog", back_populates="ai_model", cascade="all, delete"
    )
    strategies = relationship("Strategy", back_populates="ai_model")


class AIPredictionLog(Base):
    __tablename__ = "ai_prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(
        Integer, ForeignKey("ai_models.id", ondelete="CASCADE"), index=True
    )
    symbol = Column(String, nullable=False)
    predicted_price = Column(Float, nullable=False)
    actual_price = Column(Float, nullable=True)
    prediction_time = Column(DateTime, default=func.now())
    accuracy = Column(Float, nullable=True)

    # Relationships
    ai_model = relationship("AIModel", back_populates="predictions")


# =======================
# Strategies
# =======================
class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    ai_model_id = Column(
        Integer, ForeignKey("ai_models.id", ondelete="SET NULL"), index=True
    )
    parameters = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="strategies")
    ai_model = relationship("AIModel", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy", cascade="all, delete")
    backtests = relationship(
        "Backtest", back_populates="strategy", cascade="all, delete"
    )
    paper_trades = relationship(
        "PaperTrade", back_populates="strategy", cascade="all, delete"
    )


# =======================
# Trading Sessions
# =======================
class TradingSession(Base):
    __tablename__ = "trading_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    ai_model_id = Column(
        Integer, ForeignKey("ai_models.id", ondelete="SET NULL"), index=True
    )
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=True)
    total_pnl = Column(Float, default=0.0)

    # Relationships
    user = relationship("User", back_populates="trading_sessions")
    ai_model = relationship("AIModel")
    trades = relationship("Trade", back_populates="session", cascade="all, delete")
    trading_performance = relationship(
        "TradingPerformance", back_populates="session", cascade="all, delete"
    )
    trading_reports = relationship(
        "TradingReport", back_populates="session", cascade="all, delete"
    )


# =======================
# Trades
# =======================
class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id = Column(
        Integer, ForeignKey("trading_sessions.id", ondelete="CASCADE"), index=True
    )
    strategy_id = Column(
        Integer, ForeignKey("strategies.id", ondelete="CASCADE"), index=True
    )
    account_id = Column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    symbol = Column(String, nullable=False)
    trade_type = Column(String, nullable=False)  # BUY/SELL
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    status = Column(String, default="OPEN", nullable=False)  # OPEN, FILLED, CANCELED
    profit_loss = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="trades")
    session = relationship("TradingSession", back_populates="trades")
    account = relationship("Account", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")


# =======================
# Orders
# =======================
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id = Column(
        Integer, ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    symbol = Column(String, nullable=False)
    order_type = Column(String, nullable=False)  # LIMIT, MARKET, STOP-LOSS
    price = Column(Float)
    quantity = Column(Integer)
    status = Column(String, default="PENDING")  # PENDING, FILLED, CANCELED
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="orders")
    account = relationship("Account", back_populates="orders")


# =======================
# Backtesting
# =======================
class Backtest(Base):
    __tablename__ = "backtests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    strategy_id = Column(
        Integer, ForeignKey("strategies.id", ondelete="CASCADE"), index=True
    )
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    total_pnl = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User")
    strategy = relationship("Strategy", back_populates="backtests")


# =======================
# Paper Trading
# =======================
class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    strategy_id = Column(
        Integer, ForeignKey("strategies.id", ondelete="CASCADE"), index=True
    )
    symbol = Column(String, nullable=False)
    trade_type = Column(String, nullable=False)  # BUY/SELL
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False)
    status = Column(String, default="OPEN", nullable=False)
    profit_loss = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User")
    strategy = relationship("Strategy", back_populates="paper_trades")


# =======================
# Trading Performance
# =======================
class TradingPerformance(Base):
    __tablename__ = "trading_performance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id = Column(
        Integer, ForeignKey("trading_sessions.id", ondelete="CASCADE"), index=True
    )
    total_trades = Column(Integer, nullable=False)
    win_rate = Column(Float, nullable=False)
    total_profit_loss = Column(Float, nullable=False)
    max_drawdown = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    performance_type = Column(String, nullable=False)  # LIVE, PAPER, BACKTEST
    generated_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="trading_performance")
    session = relationship("TradingSession")


# =======================
# Trading Reports
# =======================
class TradingReport(Base):
    __tablename__ = "trading_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_id = Column(
        Integer, ForeignKey("trading_sessions.id", ondelete="CASCADE"), index=True
    )
    total_trades = Column(Integer, nullable=False)
    total_profit = Column(Float, nullable=False)
    win_rate = Column(Float, nullable=False)
    report_type = Column(String, nullable=False)  # LIVE, PAPER, BACKTEST
    generated_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="trading_reports")
    session = relationship("TradingSession")


# =======================
# Stocks
# =======================
class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    exchange = Column(String(10), nullable=False, default="NSE")

    # Relationships
    stock_trades = relationship("StockTrade", back_populates="stock")


# =======================
# Stock Trading History
# =======================
class StockTrade(Base):
    __tablename__ = "stock_trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), index=True)
    trade_id = Column(
        Integer, ForeignKey("trades.id", ondelete="CASCADE"), index=True, nullable=True
    )
    symbol = Column(String, nullable=False)
    exchange = Column(String, nullable=False)
    trade_date = Column(DateTime, default=func.now())
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False)
    profit_loss = Column(Float, nullable=True)
    status = Column(String, default="OPEN")

    # Relationships
    user = relationship("User")
    stock = relationship("Stock", back_populates="stock_trades")


class OTP(Base):
    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, nullable=True)
    email = Column(String, nullable=True)
    otp_code = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    verification_method = Column(String, default="sms")
    is_verified = Column(Boolean, default=False)
    otp_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (CheckConstraint("phone_number IS NOT NULL OR email IS NOT NULL"),)


class HistoricalData(Base):
    __tablename__ = "historical_data"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    exchange = Column(String, nullable=False, default="NSE")
    date = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)

    user = relationship("User", back_populates="historical_data")


class UserCapital(Base):
    __tablename__ = "user_capital"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_capital = Column(Float, nullable=False)
    risk_percentage = Column(Float, nullable=False, default=1)

    user = relationship("User", back_populates="user_capital")


class UserTradingConfig(Base):
    """User-specific trading configuration and preferences"""

    __tablename__ = "user_trading_config"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)

    # Trading Mode and Basic Settings
    trade_mode = Column(String(20), default="PAPER")  # LIVE, PAPER, SIMULATION
    default_qty = Column(Integer, default=1)  # Default quantity for trades

    # Risk Management Settings
    stop_loss_percent = Column(Float, default=2.0)  # Default stop loss percentage
    target_percent = Column(Float, default=4.0)  # Default target percentage
    max_positions = Column(Integer, default=3)  # Maximum concurrent positions
    risk_per_trade_percent = Column(Float, default=1.0)  # Risk per trade percentage

    # Trading Strategy Settings
    default_strategy = Column(
        String(50), default="MOMENTUM"
    )  # Default trading strategy
    default_timeframe = Column(String(10), default="5M")  # Default chart timeframe

    # Option Trading Settings
    option_strategy = Column(String(20), default="BUY")  # BUY, SELL, STRADDLE, STRANGLE
    option_expiry_preference = Column(
        String(20), default="NEAREST"
    )  # NEAREST, WEEKLY, MONTHLY
    enable_option_trading = Column(
        Boolean, default=True
    )  # Enable/disable option trading

    # Advanced Settings
    enable_auto_square_off = Column(
        Boolean, default=True
    )  # Auto square off at market close
    enable_bracket_orders = Column(Boolean, default=False)  # Enable bracket orders
    enable_trailing_stop = Column(Boolean, default=False)  # Enable trailing stop loss

    # Notification Settings
    enable_trade_notifications = Column(
        Boolean, default=True
    )  # Enable trade notifications
    enable_profit_loss_alerts = Column(Boolean, default=True)  # Enable P&L alerts

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="trading_config")

    # Indexes
    __table_args__ = (Index("idx_user_trading_config_user_id", "user_id"),)


class TradeSignal(Base):
    __tablename__ = "trade_signals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    trade_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    execution_status = Column(String, nullable=False, default="PENDING")
    signal_time = Column(DateTime(timezone=True), nullable=False, default=func.now())


class AITradeJournal(Base):
    __tablename__ = "ai_trade_journal"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    trade_type = Column(String, nullable=False)
    ai_confidence = Column(Float, nullable=False)
    execution_status = Column(String, nullable=False)
    profit_loss = Column(Float, nullable=True)
    trade_time = Column(DateTime(timezone=True), nullable=False, default=func.now())


class TradePerformance(Base):
    __tablename__ = "trade_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    trade_type = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    trailing_stop_loss = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    profit_loss = Column(Float, nullable=True)
    trade_time = Column(DateTime(timezone=True), nullable=False, default=func.now())
    status = Column(String, nullable=False, default="OPEN")

    user = relationship("User", back_populates="trade_performance")


class BrokerInstrument(Base):
    __tablename__ = "broker_instruments"

    id = Column(Integer, primary_key=True)
    broker_name = Column(String, nullable=False, default="Upstox")
    symbol = Column(String, nullable=False)
    name = Column(String, nullable=False)
    exchange = Column(String, nullable=False, index=True)
    segment = Column(String, nullable=False)
    instrument_type = Column(String, nullable=False)
    isin = Column(String, nullable=True)
    lot_size = Column(Float, nullable=True)
    tick_size = Column(Float, nullable=True)
    instrument_key = Column(String, nullable=False, unique=True)
    security_type = Column(String, nullable=True)


class SocialAuth(Base):
    __tablename__ = "social_auth"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider = Column(String, nullable=False)
    provider_id = Column(String, nullable=False)
    provider_email = Column(String, nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    user = relationship("User", back_populates="social_auths")

    __table_args__ = (
        Index("ix_social_auth_provider_id", "provider", "provider_id", unique=True),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(
        String(50), nullable=False
    )  # trade_executed, price_alert, stop_loss, etc.
    priority = Column(String(20), default="normal")  # low, normal, high
    category = Column(String(50), nullable=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User")


class AutoTradingSession(Base):
    __tablename__ = "auto_trading_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_date = Column(Date, nullable=False)
    selected_stocks = Column(JSON, nullable=False)  # List of selected stocks
    screening_config = Column(JSON, nullable=True)  # Screening parameters used
    stocks_screened = Column(Integer, nullable=True)  # Total stocks screened
    session_type = Column(String, nullable=False)  # AUTO_PAPER_TRADING, MANUAL, etc.
    status = Column(String, default="ACTIVE")  # ACTIVE, COMPLETED, FAILED
    total_trades = Column(Integer, default=0)
    successful_trades = Column(Integer, default=0)
    failed_trades = Column(Integer, default=0)
    session_pnl = Column(Float, default=0.0)
    start_capital = Column(Float, nullable=True)
    end_capital = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="auto_trading_sessions")
    trading_reports = relationship("DailyTradingReport", back_populates="session")


class DailyTradingReport(Base):
    __tablename__ = "daily_trading_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id = Column(
        Integer,
        ForeignKey("auto_trading_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    report_date = Column(Date, nullable=False)
    stocks_selected = Column(JSON, nullable=False)
    trades_executed = Column(Integer, default=0)
    daily_pnl = Column(Float, default=0.0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    portfolio_value = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    best_trade_pnl = Column(Float, nullable=True)
    worst_trade_pnl = Column(Float, nullable=True)
    avg_trade_duration = Column(Float, nullable=True)  # in minutes
    total_commissions = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, nullable=True)
    auto_generated = Column(Boolean, default=True)
    report_data = Column(JSON, nullable=True)  # Additional metrics
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="daily_trading_reports")
    session = relationship("AutoTradingSession", back_populates="trading_reports")


class TradeExecution(Base):
    __tablename__ = "trade_executions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id = Column(
        Integer,
        ForeignKey("auto_trading_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    symbol = Column(String, nullable=False)
    trade_type = Column(String, nullable=False)  # BUY, SELL
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Integer, nullable=False)
    entry_time = Column(DateTime, default=func.now())
    exit_time = Column(DateTime, nullable=True)
    pnl = Column(Float, nullable=True)
    pnl_percentage = Column(Float, nullable=True)
    commission = Column(Float, default=0.0)
    status = Column(String, default="OPEN")  # OPEN, CLOSED, CANCELLED
    exit_reason = Column(String, nullable=True)  # STOP_LOSS, TARGET, MANUAL, TIME_BASED
    confidence_score = Column(Float, nullable=True)  # AI confidence
    technical_indicators = Column(JSON, nullable=True)
    execution_notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User")
    session = relationship("AutoTradingSession")


class SelectedStock(Base):
    """Daily selected stocks for trading - Optimized"""

    __tablename__ = "selected_stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    instrument_key = Column(String(100), nullable=False)
    selection_date = Column(Date, nullable=False, index=True)

    # Selection Criteria
    selection_score = Column(Float, nullable=False)
    selection_reason = Column(String(100), nullable=False)

    # Price Data at Selection
    price_at_selection = Column(Float, nullable=False)
    volume_at_selection = Column(Integer, default=0)
    change_percent_at_selection = Column(Float, default=0.0)

    # Classification
    sector = Column(String(50), default="OTHER")
    score_breakdown = Column(Text)  # JSON string with detailed scoring

    # Status
    is_active = Column(Boolean, default=True)

    option_type = Column(String)  # CE / PE / NEUTRAL
    option_contract = Column(Text)  # JSON string - Single ATM contract
    option_contracts_available = Column(
        Integer, default=0
    )  # Count of available contracts
    option_chain_data = Column(Text)  # JSON string - Complete option chain
    option_expiry_date = Column(String)  # Selected expiry date (YYYY-MM-DD)
    option_expiry_dates = Column(Text)  # JSON array - All available expiry dates

    # Performance Tracking (optional)
    max_price_achieved = Column(Float)
    min_price_achieved = Column(Float)
    exit_price = Column(Float)
    exit_reason = Column(String(100))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_symbol_selection_date", "symbol", "selection_date"),
        Index("idx_selection_date_active", "selection_date", "is_active"),
        Index("idx_selection_score", "selection_score"),
    )


class DailyStockSummary(Base):
    """Daily aggregated stock data - MUCH more efficient than individual ticks"""

    __tablename__ = "daily_stock_summaries"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    instrument_key = Column(String(100), nullable=False)
    trading_date = Column(Date, nullable=False, index=True)

    # OHLC Data
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)

    # Volume and Trading Data
    volume = Column(Integer, default=0)
    total_trades = Column(Integer, default=0)
    avg_price = Column(Float, nullable=False)

    # Performance Metrics
    change_percent = Column(Float, default=0.0)

    # Classification
    sector = Column(String(50), default="OTHER")
    exchange = Column(String(10), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for performance
    __table_args__ = (
        Index("idx_symbol_date", "symbol", "trading_date"),
        Index("idx_date_sector", "trading_date", "sector"),
        Index("idx_change_percent", "change_percent"),
    )


class MarketSnapshot(Base):
    """Market snapshots at key times (open, close, significant events)"""

    __tablename__ = "market_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    snapshot_time = Column(DateTime, nullable=False)

    # Summary Statistics
    total_instruments = Column(Integer, default=0)
    processed_ticks = Column(Integer, default=0)

    # Market Data (JSON)
    market_summary = Column(Text)  # JSON with market breadth, sentiment, etc.

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)


class HourlyMarketStats(Base):
    """Hourly aggregated market statistics"""

    __tablename__ = "hourly_market_stats"

    id = Column(Integer, primary_key=True, index=True)
    stats_date = Column(Date, nullable=False, index=True)
    stats_hour = Column(Integer, nullable=False)  # 0-23

    # Market Breadth
    total_stocks = Column(Integer, default=0)
    advancing_stocks = Column(Integer, default=0)
    declining_stocks = Column(Integer, default=0)
    unchanged_stocks = Column(Integer, default=0)

    # Volume Data
    total_volume = Column(Integer, default=0)
    avg_volume = Column(Float, default=0.0)

    # Price Movement
    avg_change_percent = Column(Float, default=0.0)
    volatility_index = Column(Float, default=0.0)

    # Sector Performance (JSON)
    sector_performance = Column(Text)  # JSON with sector-wise data

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Unique constraint
    __table_args__ = (
        UniqueConstraint("stats_date", "stats_hour", name="unique_date_hour"),
    )
