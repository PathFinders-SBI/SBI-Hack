from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse
from transformers import BertTokenizer, BertForSequenceClassification, pipeline
from serpapi import GoogleSearch
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import torch
import nltk
import time
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware



nltk.download('vader_lexicon')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development. Replace with specific origin in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (CSS, JS) under /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve HTML at /
templates = Jinja2Templates(directory="static")

@app.get("/", response_class=HTMLResponse)
async def serve_frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Load VADER and FinBERT
print("Device set to use", "cuda" if torch.cuda.is_available() else "cpu")
vader_analyzer = SentimentIntensityAnalyzer()
tokenizer = BertTokenizer.from_pretrained('yiyanghkust/finbert-tone')
model = BertForSequenceClassification.from_pretrained('yiyanghkust/finbert-tone')
finbert = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)

# Fetch top LinkedIn results using SerpAPI
def fetch_linkedin_results(name, location, api_key):
    query = f"{name} {location} site:linkedin.com"
    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": 3
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    return results.get("organic_results", [])

# Scrape LinkedIn posts after manual login
def scrape_linkedin_posts(profile_link: str, login_wait: int = 60):
    options = Options()
    options.add_argument("--user-data-dir=C:/Users/agarw/LinkedInProfile")
    driver = webdriver.Chrome(options=options)

    try:
        print("Please log in to LinkedIn within 60 seconds...")
        driver.get("https://www.linkedin.com/login")
        time.sleep(login_wait)

        print("Navigating to profile:", profile_link)
        driver.get(profile_link)
        time.sleep(5)

        for _ in range(2):
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(2)

        posts_elements = driver.find_elements(By.CSS_SELECTOR, "div.update-components-text")
        posts = [post.text for post in posts_elements if post.text.strip()]

        if not posts:
            posts = [
                "Mock post: Excited to start a new role at ABC Corp!",
                "Mock post: Sharing insights on risk and default prediction."
            ]

        return posts

    except Exception as e:
        print("Error scraping:", e)
        return []
    finally:
        driver.quit()

def truncate_to_512_tokens(text):
    tokens = tokenizer.encode(text, truncation=True, max_length=512, return_tensors="pt")
    return tokenizer.decode(tokens[0], skip_special_tokens=True)

# Analyze posts using FinBERT and VADER

def analyze_post_sentiment(posts):
    results = []
    for post in posts:
        if not post:
            continue
        # Limit text to 512 tokens worth (~1024 characters as a conservative estimate)
        truncated_post = post[:1000]  # Optional: you can use tokenizer to count actual tokens

        try:
            finbert_score = finbert(truncated_post)[0]
            vader_score = vader_analyzer.polarity_scores(truncated_post)

            results.append({
                "text": truncated_post,
                "finbert_label": finbert_score['label'],
                "finbert_score": finbert_score['score'],
                "vader": vader_score
            })
        except Exception as e:
            print(f"Error analyzing post: {e}")
    return results

# Compute overall risk score

def compute_risk(sentiment_results):
    finbert_positive, finbert_negative, finbert_neutral = 0, 0, 0
    vader_compound_scores = []

    for result in sentiment_results:
        label = result.get("finbert_label", "").lower()
        if label == "positive":
            finbert_positive += 1
        elif label == "negative":
            finbert_negative += 1
        else:
            finbert_neutral += 1

        vader_compound_scores.append(result["vader"]["compound"])

    total = finbert_positive + finbert_negative + finbert_neutral
    if total == 0:
        return {"score": 0.5, "category": "Moderate", "recently_too_positive": False}

    weighted = (
        finbert_positive * 0.2 +
        finbert_neutral * 0.5 +
        finbert_negative * 0.8
    ) / total

    recent_scores = vader_compound_scores[-2:] if len(vader_compound_scores) >= 2 else vader_compound_scores
    recently_too_positive = any(score > 0.6 for score in recent_scores)

    category = (
        "Low" if weighted > 0.65 else
        "Moderate" if 0.45 <= weighted <= 0.65 else
        "High"
    )

    return {
        "score": round(weighted, 3),
        "category": category,
        "recently_too_positive": recently_too_positive
    }

# FastAPI endpoint
@app.post("/analyze")
async def analyze_person(
    name: str = Form(...),
    location: str = Form(...),
    api_key: str = Form(...)
):
    results = fetch_linkedin_results(name, location, api_key)
    structured = []
    for res in results:
        structured.append({
            "title": res.get("title"),
            "link": res.get("link"),
            "snippet": res.get("snippet", "N/A")
        })

    if structured:
        first_profile = structured[0]["link"]
        posts = scrape_linkedin_posts(first_profile)
        print("📝 Scraped posts:", posts)
    else:
        posts = [
        "Fallback post: No LinkedIn profile found.",
        "Fallback post: Using mock text for testing."
        ]
        print("⚠️ Using fallback posts.")

    sentiment_results = analyze_post_sentiment(posts)
    risk_result = compute_risk(sentiment_results)

    return JSONResponse({
        "profiles": structured,
        "scraped_posts": posts,
        "sentiment_analysis": sentiment_results,
        "final_risk": risk_result
    })