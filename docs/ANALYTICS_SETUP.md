# Financial Analytics Setup (No-Docker Guide)

This guide explains how to set up professional financial analytics for the TradingApp using standalone Grafana on Windows.

## 1. Installation
1. Download the **Grafana Standalone Windows Binary** (.zip) from [grafana.com](https://grafana.com/grafana/download?platform=windows).
2. Extract the contents to `C:\grafana`.

## 2. Configuration
To automatically load the TradingApp dashboards and data sources, you must point Grafana to this project's provisioning folder.

1. Navigate to `C:\grafana\conf`.
2. Copy `sample.ini` and rename it to `custom.ini`.
3. Open `custom.ini` and find the `[paths]` section.
4. Update the `provisioning` path (replace with your actual project path):
   ```ini
   [paths]
   provisioning = C:\Work\P\app	radingapp-main	radingapp-main\monitoring\grafana\provisioning
   ```

## 3. Database Connection
The system is pre-configured to connect to:
- **Host:** `localhost:5432`
- **Database:** `trading_db`
- **User:** `postgres`

If your password is not `password`, you will need to update it in `monitoring/grafana/provisioning/datasources/datasource.yml` or manually in the Grafana UI.

## 4. Running the Dashboard
1. Open a terminal (PowerShell or CMD).
2. Run the server:
   ```powershell
   cd C:\grafana\bin
   ./grafana-server.exe
   ```
3. Open [http://localhost:3000](http://localhost:3000) in your browser.
4. Login with:
   - **User:** `admin`
   - **Password:** `admin` (you will be asked to change this on first login).

## 5. Available Metrics
The **"Trading Bot Financial Analytics"** dashboard includes:
- **Daily Net PnL:** Real-time profit/loss for the current day.
- **Strategy Win Rate:** Percentage of profitable vs. losing trades.
- **Equity Curve:** Cumulative growth of your account.
- **Profit by Symbol:** Identification of your best-performing stocks.
- **Trade Ledger:** Detailed history of recent entries and exits.
