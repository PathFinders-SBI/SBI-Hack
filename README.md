# 🏦 Banking Risk Assessment Web Application

A local, AI-powered risk intelligence platform designed for banking institutions. This system integrates machine learning, social media intelligence, and geolocation tracking to assess loan default risk across a customer base—supporting proactive decision-making in loan processing, portfolio reviews, and recovery operations.

---

## 🚀 Project Overview

This web-based application acts as an intelligent assistant to help banks:
- Predict potential loan defaulters using customer data
- Analyze social media behavior (LinkedIn/Twitter) for digital risk signals
- Track real-time location of high-risk individuals

The system operates entirely on a **local server** to maintain maximum data privacy and security.

---

## 🔍 Core Modules

### 1. 📊 Defaulter Prediction System
- **Input:** Bank’s customer dataset (e.g., transactions, loan history, demographics)
- **Process:** ML-based classification via a pre-trained model trained on banking data
- **Output:** `0` (Non-defaulter) or `1` (Potential defaulter)
- **Technology:** Python, custom ML model, FastAPI

---

### 2. 🌐 Social Media Digital Presence Analysis
A sentiment-driven risk scoring engine built on top of public LinkedIn (and optionally Twitter) data.

#### 📥 Inputs:
- Customer Name  
- Location  
- SerpAPI Key

#### ⚙️ Process:
- SerpAPI searches LinkedIn
- Selenium scrapes profile and recent posts
- Sentiment analysis via:
  - `FinBERT` (financial text classifier)
  - `VADER` (lexicon-based sentiment scorer)
- Aggregated risk score computed from employment stability, post tone, activity levels, and sentiment shifts

#### 🧠 Tech Stack:
- **FastAPI**: Backend API and frontend server
- **FinBERT**: Finance-tuned BERT model (HuggingFace Transformers)
- **VADER**: Social media sentiment analyzer (NLTK)
- **SerpAPI + Selenium**: Profile search + automated scraping
- **Chrome WebDriver** with persistent user profiles

---

### 3. 📍 Location Tracking System
Tracks geolocation of high-risk defaulters via link-based consent capture.

#### 👣 How It Works:
1. Generates a disguised SBI-branded tracking link
2. Redirects to an SBI landing page
3. User grants browser location permission
4. Backend captures:
   - GPS coordinates
   - IP address
   - Device info
   - Timestamp
5. Data sent in real-time to a **Discord channel** for monitoring

#### 🛠️ Tech Stack:
- **Frontend:** HTML + JavaScript (Geolocation API)
- **Backend:** Python + Flask (via `r4ven`)
- **Tunneling:** Serveo / Ngrok / Cloudflare Tunnel
- **Data Storage:** JSON (`location_log.json`)
- **Visualization:** Google Maps embed + Custom dashboard

---

## 📁 Technical Architecture

```mermaid
graph LR
A[Bank User Uploads Dataset] --> B[ML Prediction Engine]
B --> C[Defaulter List]
C --> D[LinkedIn Risk Analyzer]
C --> E[Geolocation Link Generator]
D --> F[Risk Scoring Dashboard]
E --> G[Discord Location Alerts]
