# Task 2 — Conversation Flow Designs

---

## Flow 1: Buyer Inquiry

```mermaid
flowchart TD
    A[Call Connects] --> B[Greeting:\nAssalam-o-Alaikum! RealEstate Hub se baat ho rahi hai.]
    B --> C[Ask Intent:\nKya aap koi property kharidna chahte hain?]
    C --> D[Collect Requirements:\nBudget? Location? Bedrooms? Commercial/Residential?]
    D --> E[RAG: Search Matching Properties]
    E --> F{Properties Found?}
    F -->|Yes| G[Present Top 3 Options with details]
    F -->|No| H[Apologize & offer to notify when available]
    G --> I{Customer Interested?}
    I -->|Yes| J[Book Site Visit]
    I -->|Objection| K[Handle Objection → Re-offer]
    J --> L[Confirm Date/Time → Send Email]
    L --> M[End Call Warmly]
    K --> I
    H --> M
```

---

## Flow 2: Rental Inquiry

```mermaid
flowchart TD
    A[Call Connects] --> B[Greeting]
    B --> C[Ask: Rental ya purchase?]
    C -->|Rental| D[Ask: Location, Budget/month, Duration?]
    D --> E[RAG: Search Rentals]
    E --> F{Available?}
    F -->|Yes| G[Share options: price, location, amenities]
    F -->|No| H[Suggest nearby areas or waitlist]
    G --> I{Ready to visit?}
    I -->|Yes| J[Book Viewing → Email Confirmation]
    I -->|Need time| K[Offer callback / WhatsApp follow-up]
    J --> L[End Call]
    K --> L
    H --> L
```

---

## Flow 3: Commercial Property Inquiry

```mermaid
flowchart TD
    A[Call Connects] --> B[Greeting]
    B --> C[Identify: Office? Shop? Warehouse?]
    C --> D[Ask: Area sqft, Location, Lease/Purchase?]
    D --> E[RAG: Commercial Listings]
    E --> F[Present options with rent/price per sqft]
    F --> G{Interest?}
    G -->|Yes| H[Schedule walkthrough]
    G -->|Wants details| I[Send brochure via email]
    H --> J[Confirm + Calendar Invite]
    I --> J
    J --> K[End Call]
```

---

## Flow 4: Investment Inquiry

```mermaid
flowchart TD
    A[Call Connects] --> B[Greeting]
    B --> C[Identify: Investor intent]
    C --> D[Ask: Budget? ROI expectation? Timeline?]
    D --> E[RAG: High-yield listings, payment plans]
    E --> F[Present investment options with expected returns]
    F --> G{Interested?}
    G -->|Yes| H[Book meeting with senior advisor]
    G -->|Skeptical| I[Share success stories / testimonials]
    I --> G
    H --> J[Calendar Invite + Email]
    J --> K[End Call]
```

---

## Flow 5: Returning Customer

```mermaid
flowchart TD
    A[Call Connects] --> B[Greeting + Name Recognition:\nAooo Ahmed bhai! Aap ka call aa gaya!]
    B --> C[Load previous conversation from DB]
    C --> D{Previous appointment?}
    D -->|Yes| E[Ask: Aap ne pehle X property dekhi thi. Kuch update chahiye?]
    D -->|No| F[Ask about new requirement]
    E --> G{Response}
    G -->|New property| H[Search + Present]
    G -->|Reschedule| I[Rescheduling Flow]
    G -->|Ready to buy| J[Transfer to closer / Book final meeting]
    H --> K[End Call]
    I --> K
    J --> K
```

---

## Flow 6: Appointment Rescheduling

```mermaid
flowchart TD
    A[Call Connects] --> B[Greeting]
    B --> C[Ask: Appointment reschedule karna hai?]
    C --> D[Fetch existing appointment from Calendar]
    D --> E[Confirm current slot with customer]
    E --> F[Ask for new preferred date/time]
    F --> G[Check Calendar Availability]
    G --> H{Slot Available?}
    H -->|Yes| I[Update Calendar + Send new confirmation email]
    H -->|No| J[Offer 2-3 alternatives]
    J --> G
    I --> K[Confirm verbally + End Call]
```

---

## Flow 7: Appointment Cancellation

```mermaid
flowchart TD
    A[Call Connects] --> B[Greeting]
    B --> C[Customer: Cancel karna hai appointment]
    C --> D[Fetch appointment details]
    D --> E[Confirm: Aap ki X tarikh ki visit cancel karna chahte hain?]
    E --> F{Confirm Cancel?}
    F -->|Yes| G[Cancel in Calendar + Send cancellation email]
    F -->|Reschedule instead| H[Go to Rescheduling Flow]
    G --> I[Ask reason gently for CRM logging]
    I --> J[Offer future help + End Call warmly]
    H --> J
```
