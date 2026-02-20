# Contributing to Trading App

Welcome! This guide will help you set up your development environment and understand our workflows.

## 🚀 Quick Start

### Backend Setup
1.  **Python 3.10+** is required.
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Run migrations:
    ```bash
    alembic upgrade head
    ```
5.  Start the server:
    ```bash
    uvicorn app:app --reload
    ```

### Frontend Setup
1.  **Node.js 18+** is required.
2.  Navigate to the UI directory:
    ```bash
    cd ui/trading-bot-ui
    ```
3.  Install dependencies:
    ```bash
    npm install
    ```
4.  Start the development server:
    ```bash
    npm start
    ```

## 🐳 Docker Support

We support Docker for easy deployment.

-   **Production:** `docker-compose -f docker-compose.prod.yml up --build`
-   **Frontend:** The UI now has its own `Dockerfile` in `ui/trading-bot-ui/` for independent building.

## 🛠️ Code Quality

We use **pre-commit** hooks to ensure code quality.

1.  Install pre-commit:
    ```bash
    pip install pre-commit
    pre-commit install
    ```
2.  This will automatically run:
    -   **Black** (Formatting)
    -   **Isort** (Import sorting)
    -   **Flake8** (Linting)
    -   **Bandit** (Security)

## 🧪 Testing

Run backend tests using:
```bash
pytest
```
Or use the Makefile: `make test`

## 📁 Project Structure

-   `app.py`: Backend entry point.
-   `services/`: Business logic and core services.
-   `router/`: API route definitions.
-   `database/`: Database models and connection logic.
-   `ui/trading-bot-ui/`: React frontend.
-   `scripts/`: Utility scripts for backups and maintenance.
-   `docs/`: Detailed architectural documentation.
