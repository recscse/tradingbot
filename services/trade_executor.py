# services/trade_executor.py
import logging
import json
from datetime import datetime
from typing import Dict, Any
from database.models import TradeLog
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TradeExecutor:
    def __init__(
        self, db_session_factory, broker_api=None, mode="paper", default_qty=50
    ):
        self.db_session_factory = db_session_factory
        self.broker_api = broker_api
        self.mode = mode
        self.default_qty = default_qty

    def _persist_trade(self, payload: Dict[str, Any]):
        db: Session = self.db_session_factory()
        try:
            row = TradeLog(
                symbol=payload.get("symbol"),
                option_contract=json.dumps(payload.get("option_contract", {})),
                side=payload.get("side"),
                qty=payload.get("qty"),
                price=payload.get("price"),
                status=payload.get("status"),
                meta=json.dumps(payload.get("meta", {})),
            )
            db.add(row)
            db.commit()
            return row.id
        except Exception:
            db.rollback()
            logger.exception("Error persisting trade")
            return None
        finally:
            db.close()

    def execute(
        self,
        option_contract: Dict[str, Any],
        side: str = "BUY",
        qty: int = None,
        rr: float = None,
    ):
        """
        Execute a single option contract. rr = risk_reward (e.g., 2.0 means target = risk * 2)
        """
        qty = qty or self.default_qty
        payload = {
            "symbol": option_contract.get("underlying"),
            "option_contract": option_contract,
            "side": side,
            "qty": qty,
            "price": None,
            "status": "simulated" if self.mode == "paper" else "pending",
            "meta": {"mode": self.mode, "rr": rr or 1.0},
        }

        if self.mode == "paper":
            payload["price"] = option_contract.get("ltp_underlying")
            payload["status"] = "simulated"
            trade_id = self._persist_trade(payload)
            logger.info(
                "[PAPER] Simulated %s %s %s qty=%s",
                side,
                option_contract,
                option_contract.get("strike"),
                qty,
            )
            return {"trade_id": trade_id, **payload}

        # Live mode
        try:
            order = self.broker_api.place_option_order(
                underlying=option_contract["underlying"],
                strike=option_contract["strike"],
                expiry=option_contract["expiry"],
                option_type=option_contract["option_type"],
                side=side,
                qty=qty,
            )
            payload["price"] = (
                order.get("avg_price")
                or order.get("filled_price")
                or order.get("price")
            )
            payload["status"] = "placed"
            payload["meta"].update({"broker_order_id": order.get("order_id")})
            trade_id = self._persist_trade(payload)
            logger.info(
                "[LIVE] Placed order %s -> trade_id=%s broker_id=%s",
                payload,
                trade_id,
                order.get("order_id"),
            )
            return {"trade_id": trade_id, "broker": order, **payload}
        except Exception as e:
            payload["status"] = "error"
            payload["meta"].update({"error": str(e)})
            trade_id = self._persist_trade(payload)
            logger.exception("Live execution failed")
            return {"trade_id": trade_id, **payload}

    # Placeholder for trailing stop and booking profit routines; in prod this will be driven by streaming LTP updates
    def handle_live_updates(
        self, trade_row_id: int, current_price: float, stop_loss: float, target: float
    ):
        # fetch trade, check if stop or target hit; if hit place exit order and update trade
        pass
