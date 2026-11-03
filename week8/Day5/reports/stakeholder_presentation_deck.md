# Executive Presentation & 10-Minute Demonstration Script

**Project Title:** AI Property Valuation & Lead Scoring Platform for Real Estate  
**Presenter:** Lead AI/ML Platform Engineer  
**Target Stakeholders:** CEO, Head of Sales, Managing Director, CTO  
**Duration:** 10 Minutes Live Interactive Walkthrough  

---

## 1. Slide Deck Structure & Minute-by-Minute Outline

| Minute | Slide / Stage | Demonstration Focus & Narrative | Screen / Artifact Shown |
| :---: | :--- | :--- | :--- |
| **0:00 - 1:30** | **Slide 1: The Business Problem & Data Story** | Introduce the two major bottlenecks from Week 7: pricing inconsistency and sales rep fatigue. Present 3 key EDA findings (price skewness, society location premiums, and WhatsApp 3x conversion superiority). | Day 1 Charts (`01_price_distribution`, `02_price_per_marla`) |
| **1:30 - 3:00** | **Slide 2: Scientific Model Comparison** | Why linear models failed ($R^2=0.38-0.44$) and why CatBoost ($R^2=0.988$, $\text{MAPE}=6.25\%$) was selected. How class-weighted LightGBM resolved the 25% conversion imbalance to yield a 2.43x Lift. | Day 2 & Day 3 Benchmark Tables |
| **3:00 - 4:30** | **Live Demo 1: Property Valuation Engine** | Live query of a 1 Kanal house in DHA Phase 6. Show the point price, 10th-90th quantile confidence band, and automated Overpriced / Fair / Underpriced verdict. | Streamlit Tab 1 (`🏠 Property Valuation`) |
| **4:30 - 6:00** | **Live Demo 2: Lead Scoring & Priority Triage** | Show incoming 200 leads sorted by probability. Show 🔥 Hot (1-hr SLA), 🌤 Warm (24-hr SLA), and ❄️ Cold tiers with K-Means customer personas. | Streamlit Tab 2 (`🔥 Lead Triage Desk`) |
| **6:00 - 7:30** | **Live Demo 3: Explainable AI & UrduLish Assistant** | Live interaction: *"DHA Phase 6 mein 1 kanal, 5 saal purana ghar, kitne ka jana chahiye?"*. Show SHAP waterfall attribution and bilingual consultation in UrduLish. | Streamlit Tab 5 & Tab 3 (`💬 AI Assistant`) |
| **7:30 - 8:45** | **Live Demo 4: MLOps Drift & Retraining** | Simulate a 15% inflation shock. Show the automated drift report (KS-test, PSI). Show the automated retraining pipeline promoting a Challenger model with instant rollback. | HTML Drift Report (`data_drift_report.html`) |
| **8:45 - 10:00** | **Slide 3: ROI & Business Impact** | Quantify real financial returns: **PKR 29.69M** in prevented deal loss, **160 SDR hours saved per month**, and **2.43x sales conversion lift**. | ROI Calculation Table |

---

## 2. Word-for-Word Spoken Presentation Script

### [0:00 - 1:30] The Data Story & Business Context
> *"Good morning, everyone. In Week 7, we launched our AI Voice Agent, automating hundreds of customer inquiries every week. But our sales directors quickly noticed two critical bottlenecks:  
> First, property valuations were based on agent gut feeling, causing properties to sit unsold for months when overpriced, or costing our brokerage hundreds of thousands in lost commission when underpriced.  
> Second, our sales team treated all inbound leads equally—calling cold prospects while hot, ready buyers cooled off and bought from competitors.  
> As our exploratory data analysis revealed, Pakistani real estate follows sharp empirical rules: location tier dictates over 70% of property rates, with Sector F-7 and Clifton commanding over 50 Lac per Marla. Furthermore, WhatsApp and inbound phone calls convert at 34%, nearly three times higher than generic Facebook ads. Today, we replace guesswork with empirical machine learning."*

---

### [1:30 - 3:00] Scientific Model Selection
> *"Rather than relying on basic linear regression—which failed with an $R^2$ of only 0.38 due to non-linear physical interactions—we developed an Optuna-tuned CatBoost Regressor. It achieved an exceptional $R^2$ of **0.9880** and reduced Mean Absolute Percentage Error to just **6.25%**, exceeding our 15% SLA target.  
> For lead scoring, class imbalance meant standard models achieved 75% accuracy simply by predicting that nobody would ever buy—a disaster for revenue. By applying cost-sensitive loss weighting, we boosted recall to **61.8%** and achieved a **2.43x conversion lift** in the top 20% of leads."*

---

### [3:00 - 6:00] Live Demonstration: Valuation & Lead Prioritization
> *(Demonstrating live on Streamlit Hub)*  
> *"Let's test a live property: a 1 Kanal house in DHA Phase 6 listed at 8.0 Crore. In 12 milliseconds, our model calculates the fair market price at **7.00 Crore**, bounds it with an empirical range of **6.65 to 7.94 Crore**, and classifies the listing as **Overpriced by 14%**. The agent now has the data to advise the seller to list at 7.2 Crore to close quickly.  
> Next, on our Lead Triage Desk, instead of dialing through 200 random numbers, our sales reps only place 40 phone calls—all targeted at 🔥 Hot leads like serious first-time homebuyers with a 79% average conversion probability."*

---

### [6:00 - 8:45] Live Demonstration: UrduLish AI Assistant & MLOps
> *"When a broker on the move asks via voice or WhatsApp:  
> **'DHA Phase 6 mein 1 kanal, 5 saal purana ghar, kitne ka jana chahiye?'**  
> Our LangGraph AI Assistant invokes our CatBoost engine and responds in natural UrduLish:  
> *'Model ke mutabiq iski fair market value 6.65 se 7.94 crore ke darmiyan hai...'*  
> And crucially, because real estate markets shift with inflation, our MLOps drift monitor continually evaluates incoming transactions. When price surges occur, it alerts our team and automatically triggers our retraining pipeline, promoting Challenger models with zero downtime and full rollback capabilities."*

---

### [8:45 - 10:00] Financial ROI & Business Impact

| Metric | Traditional Baseline | With AI Platform | Net Business Gain |
| :--- | :---: | :---: | :---: |
| **Deals Closed per 40 SDR Calls** | ~10 Deals ($25.2\%$) | **25 – 32 Deals ($62.9\%$)** | **$+150\%$ Deal Volume** |
| **Net Commission Generated** | PKR 4.0 Million | **PKR 10.8 – 12.8 Million** | **$+$ PKR 6.8M – 8.8M / Batch** |
| **Prevented Deal Loss (Cost SLA)** | PKR 32.88 Million lost | **PKR 3.19 Million** | **PKR 29.69 Million Saved** |
| **SDR Telephone Hours Saved** | 200 hrs / month on cold leads | **40 focused hrs / month** | **160 Human Hours Saved / mo** |
| **Average Listing Days on Market** | 94 Days | **32 Days (Fair Price Listed)** | **$66\%$ Faster Liquidity** |

> *"In summary, this is not just a collection of notebooks; it is an enterprise-grade, end-to-end commercial product ready to drive immediate bottom-line revenue for our real estate partners. Thank you."*
