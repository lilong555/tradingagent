# TradingAgents: Multi-Agent Financial Analysis Framework

Welcome to TradingAgents, a powerful and extensible framework that leverages a team of specialized AI agents to perform comprehensive financial analysis. This framework automates the process of gathering and analyzing market data, social media sentiment, news, and company fundamentals to produce actionable trading insights.

![Schema](assets/schema.png)

## 🌟 Features

- **Multi-Agent System**: Utilizes a collaborative team of agents, each with a specific role (e.g., Market Analyst, News Analyst, Trader, Risk Manager).
- **Comprehensive Analysis**: Gathers data from various sources, including Yahoo Finance, Reddit, Finnhub, and Google News.
- **Configurable LLM Support**: Easily switch between different LLM providers like OpenAI, Google, Anthropic, and any OpenAI-compatible endpoints (e.g., Ollama).
- **Debate and Reflection**: Incorporates debate mechanisms between agents (e.g., Bull vs. Bear Researchers) to form a robust investment thesis.
- **Memory and Learning**: Agents reflect on past decisions to improve future performance.
- **Interactive CLI**: A rich, interactive command-line interface to configure and run the analysis pipeline.

## ⚙️ How It Works

The framework operates as a pipeline orchestrated by a graph-based system:

1.  **Analyst Team**: Gathers raw data.
    *   `Market Analyst`: Fetches price history and technical indicators.
    *   `Social Analyst`: Scans Reddit for public sentiment.
    *   `News Analyst`: Gathers the latest news.
    *   `Fundamentals Analyst`: Analyzes financial statements and insider trading.
2.  **Research Team**: Debates the findings.
    *   `Bull Researcher` and `Bear Researcher` argue their cases.
    *   `Research Manager` evaluates the debate and formulates a detailed investment plan, including entry, target, and stop-loss prices.
3.  **Trading Team**:
    *   `Trader`: Takes the investment plan and formulates a concrete trading strategy.
4.  **Risk Management Team**:
    *   A team of debators (`Risky`, `Neutral`, `Safe`) discusses the proposed trade.
    *   `Portfolio Manager` makes the final decision.

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.8+
- A Conda or other virtual environment manager.

### 2. Installation

Clone the repository and install the required dependencies:

```bash
git clone <your-repository-url>
cd TradingAgents
pip install -r requirements.txt
pip install -e .
```

### 3. Configuration (Crucial Step!)

The framework requires API keys and credentials to be set as environment variables.

#### **LLM Provider**

The interactive CLI will prompt you to choose your LLM provider and backend URL. No environment variables are needed for this part.

#### **Reddit API (for Social Analyst)**

To enable the `Social Analyst`, you must have a Reddit account and create a script-type application.

1.  **Create a Reddit App**:
    *   Go to [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
    *   Click "are you a developer? create an app...".
    *   Fill out the form:
        *   **name**: `TradingAgents`
        *   **type**: `script`
        *   **description**: `Trading agents script`
        *   **about url**: (leave blank)
        *   **redirect uri**: `http://localhost:8080`
    *   Click "create app". You will get a **client ID** (under the app name) and a **client secret**.

2.  **Set Environment Variables**:
    Create the following environment variables with your Reddit credentials.

    **For PowerShell (Windows):**
    ```powershell
    [System.Environment]::SetEnvironmentVariable("PRAW_CLIENT_ID", "YOUR_CLIENT_ID", "User")
    [System.Environment]::SetEnvironmentVariable("PRAW_CLIENT_SECRET", "YOUR_CLIENT_SECRET", "User")
    [System.Environment]::SetEnvironmentVariable("PRAW_USER_AGENT", "TradingAgents v0.1 by u/YourUsername", "User")
    [System.Environment]::SetEnvironmentVariable("PRAW_USERNAME", "YourRedditUsername", "User")
    [System.Environment]::SetEnvironmentVariable("PRAW_PASSWORD", "YourRedditPassword", "User")
    ```

    **For Bash/Zsh (Linux/macOS):**
    ```bash
    echo 'export PRAW_CLIENT_ID="YOUR_CLIENT_ID"' >> ~/.bashrc
    echo 'export PRAW_CLIENT_SECRET="YOUR_CLIENT_SECRET"' >> ~/.bashrc
    echo 'export PRAW_USER_AGENT="TradingAgents v0.1 by u/YourUsername"' >> ~/.bashrc
    echo 'export PRAW_USERNAME="YourRedditUsername"' >> ~/.bashrc
    echo 'export PRAW_PASSWORD="YourRedditPassword"' >> ~/.bashrc
    source ~/.bashrc
    ```
    > **Note:** Remember to restart your terminal or IDE after setting the variables for them to take effect.

### 4. Running the Analysis

Simply run the main CLI application:

```bash
python cli/main.py analyze
```

The application will guide you through an interactive setup process to select the ticker, date, analysts, and LLM provider for the analysis.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.
