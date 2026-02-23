# 🚀 Rust HFT Core Architecture Blueprint

This document serves as the master guide for rebuilding the trading core in Rust to achieve ultra-low latency (<50µs), pinpoint AI accuracy, and institutional-grade reliability.

---

## 1. Deep-Dive: High-Speed Data Ingestion (WebSocket)

To achieve ultra-low latency, the Rust Ingestor must avoid the "JSON Dictionary" trap used in Python.

### Implementation Logic:
*   **Zero-Allocation Parsing:** Use `serde-json` with `#[derive(Deserialize)]` on strictly typed Structs. This parses the WebSocket string directly into stack-allocated memory.
*   **The Ingestion Pipeline:**
    1.  **Thread A (IO):** Uses `tokio-tungstenite`. Its only job is to read raw bytes from the socket and push them into a `flume::bounded` channel.
    2.  **Thread B (Parser):** Pops bytes, deserializes into a `Tick` struct, and calculates the "Price Delta" from the previous tick.
*   **Upstox Protocol:** Implement both JSON and **Protobuf** (if available) decoding. Protobuf is significantly faster for HFT.

---

## 2. Dynamic Instrument & Option Key Management

Instead of searching large JSON files, Rust will **calculate** keys mathematically.

### Spot to Option Mapping:
1.  **Registry:** Maintain a `DashMap<String, InstrumentData>` where the key is the trading symbol (e.g., "RELIANCE").
2.  **Mathematical Key Generation:** When a Spot signal is detected, the engine constructs the Option Key string instantly:
    *   Format: `{SYMBOL}{YY}{MMM}{STRIKE}{TYPE}`
    *   Logic: `let key = format!("{}{}{}{}{}", symbol, year, month, atm_strike, "CE");`
3.  **Token Lookup:** Rust performs a `O(1)` hash lookup to find the numeric `instrument_token` required by the Upstox API. This takes ~100 nanoseconds.

---

## 3. Real-Time Feature Engine (The Rule Engine)

Before the AI makes a decision, the **Rule Engine** filters the data. These are your "HFT Guards."

### The Multi-Step Decision Matrix:
| Level | Rule Name | Logic |
| :--- | :--- | :--- |
| **Level 1** | **Market Regime** | Is `NIFTY_LTP` > `NIFTY_EMA_200`? (Avoid trading against the macro trend). |
| **Level 2** | **Sector Sync** | If buying `HDFC`, is the `BANKING_SECTOR` atomic counter positive? |
| **Level 3** | **Volatility Filter** | Check `ATR` (Average True Range). If too low, skip (not enough movement to cover brokerage). |
| **Level 4** | **AI Inference** | Pass the `CircularBuffer` of the last 50 ticks to the ONNX model. |

---

## 4. AI Model Integration & Training

### The Feature Vector (Inputs):
The model is trained on a 1D array of floats:
`[LTP_Change, Volume_Imbalance, Bid_Ask_Spread, Sector_Momentum, Time_To_Expiry]`

### Inference Workflow:
1.  **Input Preparation:** Rust pulls the last $N$ values from the `CircularBuffer`.
2.  **Normalization:** Scale values to be between 0 and 1 (must match Python training logic).
3.  **Execution:** `let output = session.run(vec![input_tensor])?;`
4.  **Thresholding:**
    *   `output > 0.90`: Execute Market Order (Pinpoint Accuracy).
    *   `0.70 < output < 0.90`: Place Limit Order at `Best Bid`.
    *   `output < 0.70`: Do nothing.

---

## 5. Automated Execution & Profit Booking

Once a trade is active, Rust spawns a **Position Actor** (a dedicated async task).

### Execution Rules:
*   **The Sniper Entry:** Use "IOC" (Immediate or Cancel) orders. If the price slips even 0.05% during transmission, the order cancels, preventing bad entries.
*   **Shadow Trailing SL:**
    *   Rust monitors every tick. If `LTP` drops below `Shadow_SL`, fire a Market Exit.
    *   **Logic:** `if ltp < entry_price + (max_profit * 0.8) { exit_now(); }` (Locks in 80% of peak profit).
*   **Target Updating:**
    *   If the AI model's "Confidence" increases while in a trade, the Position Actor **increases the Target Price** automatically to capture the full run.

---

## 6. Detailed Implementation Step-by-Step

### Step 1: `src/types.rs`
Define your data models. Use `FixedPoint` math instead of `Floats` for price to avoid rounding errors.

### Step 2: `src/rx_socket.rs`
Implement the WebSocket client. Use **TLS with native-certs** for the fastest handshake.

### Step 3: `src/engine/analytics.rs`
Implement the `SectorAccumulator`. Use `std::sync::atomic::AtomicU64` to store prices (shifted by 100 to handle decimals).

### Step 4: `src/strategy/ai_bridge.rs`
The wrapper for the `ort` crate. Handle model loading and tensor transformation here.

### Step 5: `src/tx_broker.rs`
The Order Execution module. Implement a **Rate Limiter** to ensure you don't exceed the broker's API limits (e.g., 10 orders/sec).


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
