# 🚀 Crypto Monitor Pro

A real-time cryptocurrency monitoring application with a configurable alert system, built with React and FastAPI.

## 📋 Description
This web application provides a comprehensive overview of the cryptocurrency market, allowing users to monitor key metrics in real time and set up custom alerts for various market conditions.

## 🛠️ Technologies
- **Frontend**: React, TypeScript, Vite
- **Backend**: Python, FastAPI
- **Data APIs**: CoinGecko, Binance
- **Package Management**: npm (frontend), pip (backend)

## 🚀 Installation and Execution

### Prerequisites
- Node.js and npm
- Python 3.8+ and pip

### Steps
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/PauloBennertz/MonitorCriptomoedas3.1.git
    cd MonitorCriptomoedas3.1
    ```

2.  **Install Backend dependencies:**
    It is recommended to use a virtual environment.
    ```bash
    pip install -r backend/requirements.txt
    ```

3.  **Install Frontend dependencies:**
    ```bash
    npm install
    ```

4.  **Run the API Server (Backend):**
    From the project root directory, run:
    ```bash
    uvicorn backend.api_server:app --reload --port 8000
    ```
    The API server will be available at `http://localhost:8000`.

5.  **Run the Application (Frontend):**
    In a new terminal, from the project root directory, run:
    ```bash
    npm run dev
    ```
    The web application will be accessible at `http://localhost:5173`.

## 🧪 Testing
This project does not yet have a dedicated test suite. However, you can test the backend API manually using the `teste_conexao.py` script:
```bash
python backend/teste_conexao.py
```

## 📁 Project Structure
```
/
├── backend/                # Python/FastAPI API code
│   ├── api_server.py       # API entry point and routes
│   ├── app_state.py        # Manages application state
│   ├── capital_flow.py     # Analyzes capital flow by category
│   ├── coin_manager.py     # Manages the list of all coins
│   ├── indicators.py       # Calculates technical indicators
│   ├── monitoring_service.py # Logic for fetching and analyzing data
│   ├── notification_service.py # Sends Telegram notifications
│   ├── prepare_dist.py     # Prepares the distribution folder
│   ├── robust_services.py  # Provides robust services like rate limiting and caching
│   ├── teste_conexao.py    # Tests the connection to the CoinGecko API
│   ├── token_movers.py     # Analyzes top gainers and losers
│   └── update_checker.py   # Checks for application updates
├── src/                    # React/TypeScript frontend code
│   ├── components/         # Reusable React components
│   │   ├── AlertHistoryPanel.tsx # A panel that displays the history of triggered alerts
│   │   ├── AlertsPanel.tsx     # A panel that displays recent alerts
│   │   ├── CryptoCard.tsx      # A card that displays data for a single cryptocurrency
│   │   ├── SettingsModal.tsx   # A modal for managing and configuring alerts
│   │   └── Tooltip.tsx         # A tooltip component
│   ├── App.tsx             # The main application component
│   ├── index.css           # Global styles
│   ├── index.tsx           # The React application entry point
│   ├── types.ts            # TypeScript type definitions
│   └── utils.ts            # Utility functions
├── package.json            # Frontend dependencies and scripts
└── README.md               # This file
```

## 🎯 Features
- **Real-time Monitoring**: Automatically updated prices, market capitalization, volume, and technical indicators.
- **Configurable Alerts**: Set up alerts for conditions like RSI, moving average crosses, MACD signals, and more.
- **Intuitive Interface**: A clear and easy-to-use dashboard for visualizing data.
- **Add/Remove Coins**: Customize your list of monitored coins.

## 🤝 Contribution
1.  Fork the project
2.  Create a branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your changes (`git commit -m 'Add AmazingFeature'`)
4.  Push to the branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request
