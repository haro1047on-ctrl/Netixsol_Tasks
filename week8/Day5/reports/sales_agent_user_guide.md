# Sales Agent Operations Manual: AI Real Estate Intelligence Hub

**Target Audience:** Real Estate Brokers, Inside Sales Reps (SDRs), Senior Closers  
**Language:** UrduLish & English  
**Portal Access:** `http://localhost:8501`  

---

## 1. Introduction: Moving from Gut-Feeling to AI-Backed Sales

Assalam-o-Alaikum! Welcome to the **AI Real Estate Intelligence Hub**.
In the past, quoting property prices relied on gut-feeling, leading to overpriced properties that sat on portals for months and underpriced deals where the agency lost commission. Similarly, calling leads randomly meant agents wasted hours on window shoppers while hot buyers cooled off.

This platform provides two empirical advantages:
1. **Accurate Property Valuations:** Instant fair market values in PKR with confidence ranges and clear verdicts.
2. **Prioritized Lead Scoring:** Automatic triage showing exactly which leads to call first to close deals faster.

---

## 2. Quoting Property Valuations (Tab 1)

### 2.1 How to Evaluate a Listing
1. Navigate to **🏠 Property Valuation** in the left sidebar.
2. Enter the property specifications:
   - **City & Society:** e.g., *Lahore -> DHA Phase 6* or *Islamabad -> Sector F-7*.
   - **Plot Size in Marla:** Enter Marla directly (Remember: $1\text{ Kanal} = 20\text{ Marla}$).
   - **Age of Property:** In years (Brand new = 0–1 yr).
   - **Asking / Listed Price:** Enter the seller's asking price to calculate the market verdict.
3. Click **Calculate Fair Market Valuation 🚀**.

### 2.2 How to Interpret Market Verdicts
- 🟢 **Fair Market Price (Within Range):** The seller's asking price matches prevailing market transactions ($\pm 10\%$). Recommended to list immediately.
- 🔴 **Overpriced (e.g. +18% Above Market):** The asking price is too high.  
  *How to talk to the seller:* *"Sir, hamaray AI model aur pichlay 3 mahinay ke transactions ke mutabiq is property ki munasib value 6.8 crore hai. Agar aap 8.0 crore demand karein ge toh listing stagnate ho jaye gi. Behtar hai ke hum 7.1 crore par launch karein."*
- 🟢 **Underpriced (Hot Deal!):** The asking price is below the 10th percentile bound.  
  *How to talk to investors:* *"Sir, yeh ek zabardast investment opportunity hai. Market value 4.5 crore hai jabkay seller emergency mein 3.8 crore demand kar raha hai. Foran token lagayein!"*

---

## 3. Lead Prioritization & Daily Workflow (Tab 2)

Every morning, the sales desk receives hundreds of multi-channel inquiries. Follow the **Operational Priority Badges**:

| Badge | Priority Tier | Conversion Probability | Response SLA | Action Required |
| :---: | :---: | :---: | :---: | :--- |
| 🔥 | **HOT** | **$p \ge 65\%$** | **Call within 1 Hour** | Assigned to Senior Closer. Objective: Lock on-site inspection tour date immediately. |
| 🌤 | **WARM** | **$35\% \le p < 65\%$** | **Call within 24 Hours** | WhatsApp outreach. Send 3 matched property brochures, address family or budget hesitation. |
| ❄️ | **COLD** | **$p < 35\%$** | **Automated Nurture** | Do NOT spend time placing manual voice calls. The prospect is automatically enrolled in our weekly WhatsApp newsletter drip. |

### Customer Personas
- **Serious First-Time Homebuyer (49.9% Close Rate):** Highly motivated family buyers. Prioritize NOC security, society amenities, and school proximity.
- **High-Net-Worth / Overseas Investor (26.6% Close Rate):** Fast digital decisions via WhatsApp. Pitch high-yield commercial plots and luxury villas.
- **Casual Window Shopper (22.6% Close Rate):** Early research stage; needs automated follow-ups.
- **Budget Renter (19.9% Close Rate):** Price-sensitive; guide towards flexible payment plans.

---

## 4. Chatting with the UrduLish AI Assistant (Tab 5)

Sales agents can chat directly with the AI Assistant on web or WhatsApp. The assistant uses real ML models and database tools:

### Practical Prompts
- *"DHA Phase 6 mein 1 kanal, 5 saal purana ghar, kitne ka jana chahiye?"*
- *"Islamabad F-7 mein 10 marla plot ka rate kya chal raha hai?"*
- *"Yeh client 3 calls kar chuka hai aur site visit book ki hai, iska priority level kya hai?"*
- *"DHA Lahore mein average per marla rate kya hai?"*

---

## 5. Explaining SHAP Rationales to Clients (Tab 3)

When a buyer or seller questions your valuation, open the **🔍 SHAP Explainability** tab:
- **Positive Drivers:** Show them that corner status, park view, solar installation, and brand-new construction objectively justify a price premium.
- **Negative Drivers:** Show sellers that structural age (>15 years) or excessive distance from main boulevards naturally commands a market discount.
