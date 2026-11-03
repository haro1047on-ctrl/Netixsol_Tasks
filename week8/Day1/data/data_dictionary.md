# Data Dictionary: AI Property Valuation & Lead Scoring Platform

## Executive Summary
This document provides complete metadata documentation for both core datasets powering the Week 8 Capstone Platform:
- **Dataset A: Property Listings (`raw_properties.csv` / `cleaned_properties.csv`)**: 6,180 records representing real estate across major metropolitan centers in Pakistan (Lahore, Islamabad, Karachi, Rawalpindi, Faisalabad). Used for Regression (Property Valuation).
- **Dataset B: Inbound CRM Leads (`raw_leads.csv` / `cleaned_leads.csv`)**: 3,690 records representing omnichannel customer inquiries (Voice Calls, WhatsApp, Web, Facebook) and sales interactions. Used for Classification (Lead Conversion Scoring).

---

## 1. Dataset A: Property Listings (Regression Target: `price_pkr`)

| Column Name | Data Type | Description | Unit | Source | Known Issues & Cleaning Requirements |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `property_id` | String | Unique property identifier code | Categorical / ID | Portal Scraper / MLS | Synthetic duplicate IDs present due to multiple agent re-postings. Dropped before modeling. |
| `city` | Categorical / String | Metropolitan city in Pakistan | N/A | Portal Listing | Validated against top 5 markets: Lahore, Islamabad, Karachi, Rawalpindi, Faisalabad. |
| `area_society` | Categorical / String | Residential society, scheme, or sector | N/A | Agent Text Input | High cardinality with spelling variations (e.g. "DHA Ph 5" vs "DHA Phase 5", "Gulberg 3" vs "Gulberg III"). Requires fuzzy standardization. |
| `property_type` | Categorical / String | Architectural format (House, Flat, Portion, etc.) | N/A | Portal Listing | Contains 6 categories: House, Flat, Upper Portion, Lower Portion, Farmhouse, Penthouse. |
| `plot_size_raw` | String | Plot dimensions as entered by listing agent | Mixed (Marla, Kanal, Sq Yd, Sq Ft) | User Listing Input | Mixed units ("1 Kanal", "125 Sq. Yd.", "2250 Sq. Ft.", "5 Marla"). Must be normalized to standard `plot_size_marla`. |
| `covered_area_raw` | String / Float | Total constructed enclosed floor area | Mixed (Sq. Ft., Sq. Yd.) | User Listing Input | Missing in ~3.5% of rows. Must be parsed to numeric `covered_area_sqft` and imputed using median plot-to-covered ratio. |
| `bedrooms` | Integer | Total count of dedicated bedrooms | Count (Integer) | Portal Attribute | Integer range 1 to 8. |
| `bathrooms` | Float / Integer | Total count of attached and common washrooms | Count (Integer) | Portal Attribute | Missing in ~4.0% of records. Imputed using bedroom-to-bathroom median ratio by property type. |
| `age_years` | Float | Estimated structural age of the construction | Years | Agent Survey / Owner Declaration | Continuous range (0.0 brand new to 35.0+ years). Influences physical depreciation. |
| `floors` | Float / Integer | Number of vertical residential storeys | Count (Integer) | Architectural Inspection | Missing in ~5.0% of rows (especially for single portion / flat listings). Imputed via property type defaults. |
| `is_corner` | Categorical / String | Indicates corner plot position | Binary Flag ("Yes" / "No") | Property CAD / Map | Value premium ~8-10% for ventilation, extra boundary, and road frontage. |
| `is_park_facing` | Categorical / String | Indicates direct frontage on community park | Binary Flag ("Yes" / "No") | Property CAD / Map | Value premium ~6-8% for unobstructed view and green surroundings. |
| `amenities` | String / Text | Comma-separated list of premium amenities | List of Tokens | Listing Description | Multi-label textual representation. Requires parsing into individual binary flags and an aggregate `amenity_score`. |
| `distance_to_main_road_km` | Float | Driving distance to nearest arterial / commercial road | Kilometers (km) | GIS Mapping | Continuous metric (0.1 km to 5.0 km). Higher distance correlates with discount. |
| `distance_to_school_km` | Float | Proximity to reputable private / public school | Kilometers (km) | GIS Mapping | Continuous metric (0.2 km to 6.5 km). |
| `distance_to_hospital_km` | Float | Proximity to tertiary care medical hospital | Kilometers (km) | GIS Mapping | Missing in ~4.0% of rows. Imputed via median distance within the respective society. |
| `listing_date` | Date / String | Date on which listing was published | YYYY-MM-DD | Portal Timestamp | Used to compute listing age and seasonality. Kept out of core pricing regression to avoid temporal leakage. |
| `raw_price_str` | String | Asking price expressed in colloquial Pakistani financial units | Text ("Crore", "Lac", Numeric) | Agent Stated Price | Unstructured string ("1.25 Crore", "85 Lac", "55 Thousand", "999 Crore"). Must be parsed to numeric PKR. |
| `price_pkr` | Float | Target market price in Pakistani Rupee | PKR (Rs.) | Target Variable | Ground truth target for regression. Contains injected human typos (<1%) requiring IQR / Z-score outlier filtering. |

---

## 2. Dataset B: Inbound CRM Leads (Classification Target: `converted`)

| Column Name | Data Type | Description | Unit | Source | Known Issues & Cleaning Requirements |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `lead_id` | String | Unique CRM tracking identifier | Categorical / ID | CRM Database | Multi-channel duplicate inquiries present (~90 rows). Deduplicated on phone + preferred_city. |
| `client_name` | String | Name of prospective client | Text | Voice Agent / Form | PII; excluded from ML feature matrix to prevent overfitting. |
| `phone` | String | E.164 normalized mobile contact number | Phone Number | Telecom Carrier | PII; used strictly for entity resolution and deduplication, dropped from modeling. |
| `lead_source` | Categorical / String | Inbound acquisition channel | Categorical ("WhatsApp", "Call", "Website", "Facebook") | Attribution Engine | WhatsApp and Inbound Voice exhibit significantly higher conversion intent than Facebook Paid Ads. |
| `budget_raw` | String | Stated investment / buying capacity | Text ("Crore", "Lac", Numeric) | CRM Interaction Log | Colloquial string format; normalized to continuous numeric `budget_pkr`. |
| `budget_pkr` | Float | Stated budget in Pakistani Rupee | PKR (Rs.) | CRM Extracted Field | Extreme variance depending on whether purpose is "Rent" vs "Buy" / "Invest". Requires segment-aware scaling. |
| `preferred_city` | Categorical / String | Target city of interest for the lead | Categorical | CRM Preference Tag | Major urban hubs: Lahore, Islamabad, Karachi, Rawalpindi, Faisalabad. |
| `property_type` | Categorical / String | Preferred asset class (House, Flat, Plot, Commercial) | Categorical | CRM Preference Tag | Category alignment with inventory. |
| `purpose` | Categorical / String | Client motivation: Buy, Rent, or Invest | Categorical | CRM Classification | Primary intent segmentation. Buy/Invest leads have distinct lifecycles compared to quick-cycle Rent leads. |
| `number_of_calls` | Integer | Total completed telephony touchpoints | Count (Integer) | PBX / AI Agent Logs | High engagement indicator. Positively correlated with conversion probability. |
| `avg_call_duration_mins` | Float | Average duration of voice interaction | Minutes | PBX Telephony CDR | Longer conversations denote high engagement and detailed inventory inquiries. |
| `response_time_hours` | Float | Elapsed time before sales agent answered lead inquiry | Hours | CRM Inbound Queue | Missing in ~3.5% of rows. Imputed via channel median. Fast responses (<15 min) correlate strongly with conversion. |
| `visit_booked` | Categorical / String | Whether physical site tour was scheduled and completed | Binary Flag ("Yes" / "No") | CRM Calendar Hook | Dominant predictor of downstream conversion. |
| `days_since_first_contact` | Integer | Lead age in CRM system | Days | CRM System Timestamp | Continuous metric (1 to 90 days). Aging leads without progress suffer from lead decay. |
| `objection_raised` | Categorical / String | Primary friction point recorded by agent | Categorical ("None", "Price too high", "Location too far", etc.) | AI Conversation Summary | Missing in ~4.0% of records. Imputed as "None" or "Unspecified". High friction objections drastically suppress conversion. |
| `converted` | Categorical / Integer | Final conversion outcome: Did the lead purchase / lease? | Binary Target ("Yes" / "No" or 1 / 0) | CRM Milestone Event | Target variable. Exhibits natural class imbalance (~25% positive, 75% negative). Requires stratified splitting and PR-AUC optimization. |

---

## 3. Standardization and Conversion Rules

### A. Pakistani Currency (Rupee / PKR)
- **1 Crore (1 Cr)** = $10,000,000\text{ PKR}$ ($10^7$)
- **1 Lac / Lakh** = $100,000\text{ PKR}$ ($10^5$)
- **1 Thousand (K)** = $1,000\text{ PKR}$ ($10^3$)

### B. Pakistani Land Area Units
- **1 Kanal** = $20\text{ Marlas} = 4,500\text{ sq ft}$ (standard Punjab/Islamabad LDA/CDA metric)
- **1 Marla** = $225\text{ sq ft} = 25\text{ sq yards}$
- **1 Square Yard (Guz)** = $9\text{ sq ft} = \frac{9}{225}\text{ Marla} = 0.04\text{ Marla}$
- **Standard Base Unit for Platform Modeling**:
  - Plot Size: **`plot_size_marla`**
  - Covered Area: **`covered_area_sqft`**
