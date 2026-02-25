import asyncio
import os
import sys
import argparse
import pandas as pd
from datetime import datetime, timedelta
from github import Github

# Add project root to sys.path for internal imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import SessionLocal
from database.models import BrokerConfig, User
from services.backtester.runner import BacktestRunner

def get_admin_upstox_token():
    """Fetch the Upstox access token for the admin user from the database."""
    db = SessionLocal()
    try:
        # 1. Find the admin user
        admin_user = db.query(User).filter(User.role == "admin").first()
        if not admin_user:
            # Fallback: check for the first user if no explicit admin role found
            admin_user = db.query(User).first()
            
        if not admin_user:
            return None
            
        # 2. Get the active Upstox config for this user
        config = db.query(BrokerConfig).filter(
            BrokerConfig.user_id == admin_user.id,
            BrokerConfig.broker_name == "Upstox",
            BrokerConfig.is_active == True
        ).first()
        
        return config.access_token if config else None
    finally:
        db.close()

async def run_automated_backtest(repo_name, pr_number, github_token, upstox_token):
    """
    Automated Backtesting Agent for Pull Requests.
    Runs a backtest on changed strategies and posts results to GitHub.
    """
    # 1. Setup Token (Priority: Arg > Env > DB)
    token = upstox_token or os.getenv("UPSTOX_ACCESS_TOKEN") or get_admin_upstox_token()
    
    if not token:
        print("❌ Error: No Upstox Access Token found in arguments, environment, or database.")
        return

    # 2. Setup GitHub
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))
    
    # 2. Identify Changed Strategies
    changed_files = [f.filename for f in pr.get_files()]
    strategies_to_test = [f for f in changed_files if f.startswith("strategies/") and f.endswith(".py")]
    
    if not strategies_to_test:
        print("✅ No strategy changes detected. Skipping backtest.")
        return

    print(f"🚀 Detected strategy changes: {strategies_to_test}")
    
    # 3. Initialize Backtester
    # We'll use a standard test period: Last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Standard benchmark: NIFTY 50 (NSE_EQ|INE090A01021)
    instrument_key = "NSE_INDEX|Nifty 50" 
    
    results_summary = []
    
    async with BacktestRunner(upstox_token, initial_capital=100000) as runner:
        for strategy_file in strategies_to_test:
            print(f"📊 Running backtest for {strategy_file}...")
            
            try:
                # In a real scenario, we'd dynamically load the strategy class from the file
                # For this MVP, we run the runner's backtest_strategy which uses the internal logic
                result = await runner.backtest_strategy(
                    instrument_key=instrument_key,
                    start_date=start_date,
                    end_date=end_date,
                    strategy_name=strategy_file.split("/")[-1]
                )
                
                summary = result.get("summary", {})
                results_summary.append({
                    "Strategy": strategy_file.split("/")[-1],
                    "Total Trades": summary.get("total_trades", 0),
                    "Win Rate": f"{summary.get('win_rate', 0):.2f}%",
                    "Net PnL": f"₹{summary.get('net_pnl', 0):,.2f}",
                    "Max Drawdown": f"{summary.get('max_drawdown', 0):.2f}%"
                })
            except Exception as e:
                print(f"❌ Backtest failed for {strategy_file}: {e}")
                results_summary.append({
                    "Strategy": strategy_file,
                    "Error": str(e)
                })

    # 4. Post Results to GitHub
    if results_summary:
        table_header = "| Strategy | Total Trades | Win Rate | Net PnL | Max Drawdown |
| :--- | :--- | :--- | :--- | :--- |"
        table_rows = "
".join([
            f"| {r.get('Strategy')} | {r.get('Total Trades')} | {r.get('Win Rate')} | {r.get('Net PnL')} | {r.get('Max Drawdown')} |"
            if "Error" not in r else f"| {r.get('Strategy')} | ERROR | ERROR | {r.get('Error')} | ERROR |"
            for r in results_summary
        ])
        
        comment = f"## 📈 Automated Backtest Results (Last 30 Days)

{table_header}
{table_rows}

*Note: Backtest performed on NIFTY 50 benchmark.*"
        pr.create_issue_comment(comment)
        print("✅ Backtest results posted to GitHub.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True)
    parser.add_argument("--github-token", required=True)
    parser.add_argument("--upstox-token", required=True)
    
    args = parser.parse_args()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_automated_backtest(
        args.repo, args.pr, args.github_token, args.upstox_token
    ))
