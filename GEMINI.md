# GEMINI.md

## Project Overview

This is a full-stack algorithmic trading platform designed for the Indian stock markets. It features a Python/FastAPI backend and a React/TypeScript frontend. The platform supports multiple brokers, real-time market data, AI-powered trading strategies, and advanced order management.

The architecture is highly modular and includes a sophisticated monitoring and CI/CD setup. The backend uses a combination of WebSockets and REST APIs to communicate with the frontend and other services. The frontend is a modern React application with a rich set of UI components and state management libraries.

## Building and Running

### Prerequisites

*   Python 3.10+
*   Node.js 18+
*   PostgreSQL 13+
*   Git

### Backend

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run database migrations:**
    ```bash
    alembic upgrade head
    ```
3.  **Start the backend server:**
    ```bash
    python app.py
    ```

### Frontend

1.  **Navigate to the frontend directory:**
    ```bash
    cd ui/trading-bot-ui
    ```
2.  **Install dependencies:**
    ```bash
    npm install
    ```
3.  **Start the frontend development server:**
    ```bash
    npm start
    ```

### Docker (Monitoring Stack)

To run the monitoring stack (Prometheus, Grafana, etc.), use the following command:

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

## Development Conventions

*   **Python:** The backend follows PEP 8 and uses Black for code formatting.
*   **JavaScript/TypeScript:** The frontend uses ESLint and Prettier for code linting and formatting.
*   **Commits:** The project uses the Conventional Commits specification for commit messages.
*   **Testing:** The project has a minimum test coverage requirement of 30%. Tests are written with `pytest`.
