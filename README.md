```
docker compose up -d
```
expose port 5173


```
wm/
├── backend/
│   ├── auth/
│   │   ├── acled.py
│   │   └── telegram.py
│   │
│   ├── crawlers/
│   │   ├── __init__.py
│   │   ├── base_crawler.py
│   │   ├── crawl_oil_prices.py
│   │   ├── crawl_security.py
│   │   ├── gdelt_crawler.py
│   │   ├── iran_crawl_acled.py
│   │   ├── liveuamap_crawler.py
│   │   ├── opensky_crawler.py
│   │   ├── polymarket_crawler.py
│   │   └── telegram_crawler.py
│   │
│   ├── data/
│   │   ├── gdelt_iran_us_energy.json
│   │   ├── iran-events-latest.json
│   │   ├── iran_intel_opensky.json
│   │   ├── iran_protests_clean.json
│   │   ├── oil_prices.json
│   │   ├── polymarket-results.json
│   │   ├── security_advisories.json
│   │   ├── telegram-channels.json
│   │   └── telegram_results.json
│   │
│   ├── panels/
│   │   ├── __init__.py
│   │   ├── base_panel.py
│   │   ├── gdelt_panel.py
│   │   ├── liveuamap_panel.py
│   │   ├── map_panel.py
│   │   ├── opensky_panel.py
│   │   ├── polymarket_panel.py
│   │   ├── security_panel.py
│   │   ├── telegram_panel.py
│   │   └── webcam_panel.py
│   ├── insight_summarize.py
│   └── app.py
│
├── frontend/
│   ├── index.html
│   ├── main.js
│   └── style.css
|
├── .env
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── package-lock.json
├── package.json
└── README.md
```

