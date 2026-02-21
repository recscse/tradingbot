# 🚀 Rust HFT Core Architecture Blueprint

This document serves as the master guide for rebuilding the trading core in Rust to achieve ultra-low latency (<50µs), pinpoint AI accuracy, and institutional-grade reliability.

---

## 1. System Architecture

The system is designed as a **Hybrid Engine**:
*   **The Muscle (Rust):** Handles data ingestion, strategy execution, and risk management.
*   **The Brain (AI/ONNX):** Trained models running inside the Rust process for decision making.
*   **The Face (React/Python):** Your existing UI monitors the Rust core via a local WebSocket.

```mermaid
[Market Data (Upstox WS)] 
       ⬇ (Binary/JSON Stream)
[RUST CORE ENGINE]
   ├── 1. Data Ingestor (Tokio): Zero-copy parsing
   ├── 2. Feature Builder: Real-time indicators (RSI, OrderFlow)
   ├── 3. Global State (DashMap): Thread-safe market snapshot
   ├── 4. Strategy Factory: Runs multiple strategies in "Shadow Mode"
   ├── 5. AI Inference (ORT): ONNX Runtime for probability
   └── 6. Execution Actor: Spawns independent tasks for active trades
       ⬇ (HTTP/Socket)
[Broker API (Order Placement)]
```

---

## 2. Technology Stack (Rust Crates)

| Component | Crate (Library) | Purpose |
| :--- | :--- | :--- |
| **Async Runtime** | `tokio` | The foundation for high-performance I/O. |
| **WebSockets** | `tokio-tungstenite` | Ultra-fast, non-blocking WebSocket client. |
| **Serialization** | `serde`, `serde_json` | Parsing market data into Structs (Zero-copy). |
| **Shared State** | `dashmap` | High-concurrency HashMap for the "Market Registry". |
| **Parallelism** | `rayon` | Running math calculations across all CPU cores. |
| **AI/ML** | `ort` (ONNX Runtime) | Running trained AI models at native speed. |
| **Dataframes** | `polars` | Fast data manipulation for strategy backtesting. |
| **Technical Analysis** | `ta` | Standard indicators (RSI, EMA, MACD). |
| **Logging** | `tracing`, `tracing-appender` | High-speed, async logging to files/console. |

---

## 3. Implementation Roadmap (Step-by-Step)

### Phase 1: The Data Highway (Latency < 500µs)
**Goal:** Receive, parse, and store market data without GC pauses.

1.  **Define Structs:** Create rigorous Rust structs for `Tick`, `OrderBook`, and `OptionChain`.
2.  **WebSocket Client:** Implement a `tokio-tungstenite` client that auto-reconnects.
3.  **Broadcaster:** Use `tokio::sync::broadcast` to send ticks to the Strategy Engine.
4.  **Market Registry:** Use `DashMap` to store the *latest* price of every instrument (Spot + Options). This allows O(1) lookups.

### Phase 2: The Analytics Engine (Real-Time)
**Goal:** Know the "State of the Market" instantly.

1.  **Sector Tracking:** Use `AtomicF64` counters to track Sector Performance (e.g., BANKING +0.5%) in real-time.
2.  **Option Chain Manager:**
    *   Implement Black-Scholes in pure Rust functions.
    *   Calculate Greeks (Delta, Gamma) for 100+ strikes in parallel using `Rayon`.
3.  **Feature Buffer:** Maintain a Ring Buffer of the last 100 ticks for every stock to feed the AI.

### Phase 3: The AI & Strategy Factory
**Goal:** "Pinpoint Accuracy" using Ensemble Models.

1.  **Data Logger:** Create a Rust module that dumps raw ticks to **Parquet** files for training.
2.  **Training (Python Side):**
    *   Train **XGBoost** (Direction) and **LSTM** (Volatility) models on the captured data.
    *   Export models to `.onnx` format.
3.  **Inference (Rust Side):**
    *   Load `.onnx` models using `ort`.
    *   On every significant tick, pass the Feature Buffer to the model.
    *   **Filter Logic:** `If Probability > 0.85 THEN Execute`.

### Phase 4: Execution & Risk Management
**Goal:** Safety first.

1.  **Risk Gate:** Before *any* order is sent, check:
    *   `DailyLoss < Limit`
    *   `MarginAvailable > Required`
2.  **Shadow Mode:** Run strategies without sending orders. Log "Virtual PnL" to verify accuracy.
3.  **Execution Actor:**
    *   Spawn a unique Task for every active trade.
    *   It manages the **"Shadow Stop Loss"** (internal SL, not on broker).
    *   It handles **Dynamic Trailing** based on AI volatility prediction.

---

## 4. How to Start? (The "Hello World")

1.  **Initialize Project:**
    ```bash
    cargo new hft_core
    cd hft_core
    cargo add tokio --features full
    cargo add serde serde_json tokio-tungstenite
    ```

2.  **Build the Ingestor First:**
    *   Write `src/market_data.rs`.
    *   Connect to Upstox.
    *   Parse the binary/JSON message.
    *   Print the latency (Time Received - Time Sent).

3.  **Add the Strategy Trait:**
    *   Define `trait Strategy { fn on_tick(&self, tick: Tick) -> Signal; }`.
    *   Implement a simple `EmaCrossover` strategy.

4.  **Connect AI:**
    *   Once the data is flowing, plug in the ONNX runtime.

---

## 5. Deployment Strategy

*   **Production:** Run the Rust binary as a **Systemd Service** on a high-performance Linux server (or Railway).
*   **Monitoring:** The Rust app exposes a lightweight WebSocket at `ws://localhost:9000`.
*   **UI:** Your existing React app connects to this local WebSocket to display the dashboard.

This architecture removes Python's bottlenecks while keeping the ease of use for the UI and Training.
