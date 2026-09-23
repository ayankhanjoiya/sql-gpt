# 🤖 SQL Assistant

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=chainlink&logoColor=white)](https://langchain.com/)
[![Groq](https://img.shields.io/badge/Groq-FF6B35?style=for-the-badge&logoColor=white)](https://groq.com/)

> **Chat with your databases in plain English**

An intelligent SQL interface powered by Groq's AI models and LangChain that converts natural language questions into SQL queries and visualizations.

---

## ✨ Features

- **🧠 AI-Powered**: Multiple Groq models with automatic fallback
- **💬 Natural Language**: Ask questions in plain English
- **📊 Smart Visualizations**: Auto-generated charts and graphs
- **🔒 Secure**: Read-only operations with SQL injection protection
- **🗄️ Database Support**: SQLite with more databases coming soon

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Groq API key ([Get free here](https://console.groq.com/))

### Installation

```bash
# Clone & install
git clone https://github.com/YuvvrajSingh/sql-gpt.git
cd sql-gpt
pip install -r requirements.txt

# Set up environment
echo "GROQ_API_KEY=your_api_key_here" > .env

# Run the app
streamlit run streamlit_app.py
```

Your SQL Assistant will be available at `http://localhost:8501`

---

## 📖 Usage

1. **Enter your Groq API key** in the sidebar
2. **Choose a database** (sample included or upload your own SQLite file)
3. **Ask questions** like:
   - "Show me the top 5 customers by sales"
   - "Create a bar chart of monthly revenue"
   - "Which products haven't been ordered recently?"

### Example Queries

```
💬 "What tables are available?"
💬 "Show me customer demographics"
💬 "Plot sales trends over time"
💬 "Find high-value customers"
```

---

## 🗄️ Database Support

- **✅ SQLite**: Full support (.db, .sqlite, .sqlite3)
- **🔄 MySQL**: Coming soon
- **🔄 PostgreSQL**: Planned
- **🔄 SQL Server**: Planned

The app includes a sample database with customers, products, orders, and employees data.

---

## 🎨 Visualizations

Request charts by mentioning keywords like:

- "show me a chart"
- "create a graph"
- "plot the data"

**Available chart types**: Bar, Pie, Line, Scatter, Histogram

---

## ⚙️ Configuration

### Environment Variables

```env
GROQ_API_KEY=your_groq_api_key_here
STREAMLIT_SERVER_PORT=8501
```

### AI Models Used

1. **Llama 3.1 70B Versatile** (primary)
2. **Llama 3.1 8B Instant** (fallback)
3. **Gemma 2 9B IT** (backup)

---

## 📊 Project Stats

![GitHub stars](https://img.shields.io/github/stars/YuvvrajSingh/sql-gpt?style=social)
![GitHub forks](https://img.shields.io/github/forks/YuvvrajSingh/sql-gpt?style=social)
![GitHub issues](https://img.shields.io/github/issues/YuvvrajSingh/sql-gpt)

---

<div align="center">

### 🚀 Ready to chat with your databases?

[![Deploy to Streamlit Cloud](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)

**[⭐ Star this repo](https://github.com/YuvvrajSingh/sql-gpt)** • **[🍴 Fork it](https://github.com/YuvvrajSingh/sql-gpt/fork)** • **[📝 Report issues](https://github.com/YuvvrajSingh/sql-gpt/issues)**



</div>
