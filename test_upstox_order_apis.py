"""
Upstox Order Management API Testing Script
Comprehensive tests for all V3 order APIs
"""

import asyncio
import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UpstoxOrderAPITester:
    """
    Comprehensive test suite for Upstox Order APIs

    Features:
    - Tests all order management endpoints
    - Sandbox environment support
    - Detailed logging
    - Error handling
    """

    def __init__(self, access_token: str, use_sandbox: bool = True):
        """
        Initialize tester

        Args:
            access_token: Upstox access token
            use_sandbox: Use sandbox environment (recommended for testing)
        """
        self.access_token = access_token
        self.use_sandbox = use_sandbox

        from services.upstox.upstox_order_service import get_upstox_order_service

        self.service = get_upstox_order_service(
            access_token=access_token,
            use_sandbox=use_sandbox
        )

        logger.info(f"Initialized Upstox Order API Tester (Sandbox: {use_sandbox})")

    def test_place_order(self) -> Dict[str, Any]:
        """
        Test: Place single order

        Returns:
            Test result dict
        """
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Place Single Order (MARKET)")
        logger.info("="*60)

        try:
            result = self.service.place_order_v3(
                quantity=1,
                instrument_token="NSE_EQ|INE848E01016",  # HDFC Bank
                order_type="MARKET",
                transaction_type="BUY",
                product="D",
                validity="DAY",
                price=0.0,
                trigger_price=0.0,
                disclosed_quantity=0,
                is_amo=False,
                tag="test_order",
                slice=False
            )

            logger.info(f"✅ Result: {result}")
            return {"success": True, "test": "place_order", "result": result}

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return {"success": False, "test": "place_order", "error": str(e)}

    def test_place_order_with_slicing(self) -> Dict[str, Any]:
        """
        Test: Place order with auto-slicing

        Returns:
            Test result dict
        """
        logger.info("\n" + "="*60)
        logger.info("TEST 2: Place Order with Auto-Slicing")
        logger.info("="*60)

        try:
            result = self.service.place_order_v3(
                quantity=4000,  # Large quantity to trigger slicing
                instrument_token="NSE_FO|43919",
                order_type="MARKET",
                transaction_type="BUY",
                product="D",
                validity="DAY",
                price=0.0,
                trigger_price=0.0,
                disclosed_quantity=0,
                is_amo=False,
                tag="test_slicing",
                slice=True  # Enable auto-slicing
            )

            logger.info(f"✅ Result: {result}")
            logger.info(f"   Orders created: {len(result.get('data', {}).get('order_ids', []))}")
            return {"success": True, "test": "place_order_slicing", "result": result}

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return {"success": False, "test": "place_order_slicing", "error": str(e)}

    def test_place_multi_order(self) -> Dict[str, Any]:
        """
        Test: Place multiple orders in single call

        Returns:
            Test result dict
        """
        logger.info("\n" + "="*60)
        logger.info("TEST 3: Place Multi Order (Batch)")
        logger.info("="*60)

        try:
            orders = [
                {
                    "correlation_id": "test_1",
                    "quantity": 1,
                    "instrument_token": "NSE_EQ|INE848E01016",
                    "order_type": "MARKET",
                    "transaction_type": "BUY",
                    "product": "D",
                    "validity": "DAY",
                    "price": 0,
                    "trigger_price": 0,
                    "disclosed_quantity": 0,
                    "is_amo": False,
                    "slice": False
                },
                {
                    "correlation_id": "test_2",
                    "quantity": 1,
                    "instrument_token": "NSE_EQ|INE062A01020",  # SBI
                    "order_type": "MARKET",
                    "transaction_type": "BUY",
                    "product": "D",
                    "validity": "DAY",
                    "price": 0,
                    "trigger_price": 0,
                    "disclosed_quantity": 0,
                    "is_amo": False,
                    "slice": False
                }
            ]

            result = self.service.place_multi_order(orders)

            logger.info(f"✅ Result: {result}")
            logger.info(f"   Summary: {result.get('summary')}")
            return {"success": True, "test": "place_multi_order", "result": result}

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return {"success": False, "test": "place_multi_order", "error": str(e)}

    def test_modify_order(self, order_id: str) -> Dict[str, Any]:
        """
        Test: Modify existing order

        Args:
            order_id: Order ID to modify

        Returns:
            Test result dict
        """
        logger.info("\n" + "="*60)
        logger.info("TEST 4: Modify Order")
        logger.info("="*60)

        try:
            result = self.service.modify_order_v3(
                order_id=order_id,
                quantity=2,
                order_type="LIMIT",
                validity="DAY",
                price=1600.0,
                trigger_price=0.0,
                disclosed_quantity=0
            )

            logger.info(f"✅ Result: {result}")
            return {"success": True, "test": "modify_order", "result": result}

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return {"success": False, "test": "modify_order", "error": str(e)}

    def test_cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Test: Cancel single order

        Args:
            order_id: Order ID to cancel

        Returns:
            Test result dict
        """
        logger.info("\n" + "="*60)
        logger.info("TEST 5: Cancel Single Order")
        logger.info("="*60)

        try:
            result = self.service.cancel_order_v3(order_id)

            logger.info(f"✅ Result: {result}")
            return {"success": True, "test": "cancel_order", "result": result}

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return {"success": False, "test": "cancel_order", "error": str(e)}

    def test_cancel_multi_order(self, segment: str = None, tag: str = None) -> Dict[str, Any]:
        """
        Test: Cancel multiple orders

        Args:
            segment: Market segment filter (optional)
            tag: Order tag filter (optional)

        Returns:
            Test result dict
        """
        logger.info("\n" + "="*60)
        logger.info("TEST 6: Cancel Multi Order")
        logger.info(f"   Filters - Segment: {segment}, Tag: {tag}")
        logger.info("="*60)

        try:
            result = self.service.cancel_multi_order(segment=segment, tag=tag)

            logger.info(f"✅ Result: {result}")
            logger.info(f"   Summary: {result.get('summary')}")
            return {"success": True, "test": "cancel_multi_order", "result": result}

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return {"success": False, "test": "cancel_multi_order", "error": str(e)}

    def test_exit_positions(self, segment: str = None, tag: str = None) -> Dict[str, Any]:
        """
        Test: Exit all positions

        Args:
            segment: Market segment filter (optional)
            tag: Position tag filter (optional)

        Returns:
            Test result dict
        """
        logger.info("\n" + "="*60)
        logger.info("TEST 7: Exit All Positions")
        logger.info(f"   Filters - Segment: {segment}, Tag: {tag}")
        logger.info("="*60)

        try:
            result = self.service.exit_all_positions(segment=segment, tag=tag)

            logger.info(f"✅ Result: {result}")
            logger.info(f"   Summary: {result.get('summary')}")
            return {"success": True, "test": "exit_positions", "result": result}

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return {"success": False, "test": "exit_positions", "error": str(e)}

    def test_get_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        Test: Get order details

        Args:
            order_id: Order ID to fetch

        Returns:
            Test result dict
        """
        logger.info("\n" + "="*60)
        logger.info("TEST 8: Get Order Details")
        logger.info(f"   Order ID: {order_id}")
        logger.info("="*60)

        try:
            result = self.service.get_order_details(order_id)

            logger.info(f"✅ Result: {result}")
            order_data = result.get('data', {})
            logger.info(f"   Status: {order_data.get('status')}")
            logger.info(f"   Quantity: {order_data.get('quantity')}")
            logger.info(f"   Filled: {order_data.get('filled_quantity')}")
            return {"success": True, "test": "get_order_details", "result": result}

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return {"success": False, "test": "get_order_details", "error": str(e)}

    def test_get_order_history(self, order_id: str = None, tag: str = None) -> Dict[str, Any]:
        """
        Test: Get order history

        Args:
            order_id: Specific order ID (optional)
            tag: Order tag filter (optional)

        Returns:
            Test result dict
        """
        logger.info("\n" + "="*60)
        logger.info("TEST 9: Get Order History")
        logger.info(f"   Order ID: {order_id}, Tag: {tag}")
        logger.info("="*60)

        try:
            result = self.service.get_order_history(order_id=order_id, tag=tag)

            logger.info(f"✅ Result: {result}")
            logger.info(f"   History entries: {result.get('total_entries')}")
            return {"success": True, "test": "get_order_history", "result": result}

        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            return {"success": False, "test": "get_order_history", "error": str(e)}

    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run complete test suite

        Returns:
            Comprehensive test results
        """
        logger.info("\n" + "="*80)
        logger.info("UPSTOX ORDER MANAGEMENT API - COMPREHENSIVE TEST SUITE")
        logger.info("="*80)

        results = []

        # Test 1: Place single order
        test1 = self.test_place_order()
        results.append(test1)

        # Test 2: Place order with slicing
        test2 = self.test_place_order_with_slicing()
        results.append(test2)

        # Test 3: Place multi order
        test3 = self.test_place_multi_order()
        results.append(test3)

        # Test 4-9: Only run if we have order IDs from previous tests
        if test1.get("success") and test1.get("result", {}).get("success"):
            order_ids = test1["result"]["data"]["order_ids"]
            if order_ids:
                test_order_id = order_ids[0]

                # Test 4: Modify order
                test4 = self.test_modify_order(test_order_id)
                results.append(test4)

                # Test 5: Cancel order
                test5 = self.test_cancel_order(test_order_id)
                results.append(test5)

                # Test 8: Get order details
                test8 = self.test_get_order_details(test_order_id)
                results.append(test8)

                # Test 9: Get order history
                test9 = self.test_get_order_history(order_id=test_order_id)
                results.append(test9)

        # Test 6: Cancel multi order (by tag)
        test6 = self.test_cancel_multi_order(tag="test_order")
        results.append(test6)

        # Print summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUITE SUMMARY")
        logger.info("="*80)

        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.get("success"))
        failed_tests = total_tests - passed_tests

        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        # List failed tests
        if failed_tests > 0:
            logger.warning("\nFailed Tests:")
            for r in results:
                if not r.get("success"):
                    logger.warning(f"  - {r.get('test')}: {r.get('error')}")

        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "results": results
        }


async def main():
    """Main test execution"""

    # Get access token from environment
    access_token = os.getenv("UPSTOX_ACCESS_TOKEN")

    if not access_token:
        logger.error("❌ UPSTOX_ACCESS_TOKEN not found in environment variables")
        logger.info("Please set UPSTOX_ACCESS_TOKEN in your .env file")
        return

    logger.info("Starting Upstox Order API Tests...")
    logger.info(f"Access Token: {access_token[:10]}...{access_token[-10:]}")

    # Initialize tester with sandbox mode
    tester = UpstoxOrderAPITester(
        access_token=access_token,
        use_sandbox=True  # Use sandbox for safety
    )

    # Run all tests
    results = tester.run_all_tests()

    logger.info("\n✅ Test suite completed!")
    return results


if __name__ == "__main__":
    asyncio.run(main())
