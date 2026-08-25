# Task 4 — TTS Evaluation: Local TTS vs ElevenLabs

## Our Stack Decision

**Primary TTS: Local** (Coqui TTS / Piper) — runs offline, zero cost, no API key.  
**ElevenLabs:** Free tier only — used for demo comparison, not production.

---

## Comparison: Local TTS vs ElevenLabs Free Tier

| Feature | Local TTS (Coqui/Piper) | ElevenLabs Free Tier |
|---|---|---|
| **Cost** | ✅ Free forever | ⚠️ 10,000 chars/month limit |
| **Latency** | ~300–600ms (CPU), ~100ms (GPU) | ~400–800ms (API round-trip) |
| **Naturalness** | Moderate — improving fast | Very high |
| **UrduLish Support** | ⚠️ Limited — English model, Urdu words may sound off | ⚠️ Better switching but still imperfect |
| **Voice Cloning** | ❌ Not available locally (without fine-tuning) | ✅ 1 custom voice on free tier |
| **Streaming** | ✅ Possible with chunk generation | ✅ Available |
| **Internet Required** | ✅ No — fully offline | ❌ Yes — API call |
| **Privacy** | ✅ All audio stays local | ⚠️ Audio sent to ElevenLabs servers |
| **Customization** | ✅ Full control — model, voice, speed | Limited on free tier |

---

## Test Results

### Test 1: English Sentence
> *"This property is ideally located near the main highway with easy access to schools."*

- **Local Coqui TTS:** Clear, natural. Slight robotic edge on longer sentences.
- **ElevenLabs:** Noticeably more expressive and natural-sounding.

### Test 2: UrduLish Sentence
> *"Assalam-o-Alaikum! RealEstate Hub se baat ho rahi hai. Main Haroon hoon."*

- **Local Coqui TTS:** Urdu words sound slightly off — model is English-first. Understandable but not native.
- **ElevenLabs:** Better pronunciation on Roman Urdu but still not fully native. Pauses slightly at language switch.

### Test 3: Latency (local machine, CPU)
- **Local Coqui TTS:** ~450ms for a 10-word sentence (CPU). ~120ms on GPU.
- **ElevenLabs API:** ~550ms including network round-trip.

---

## Conclusion

**Local TTS (Coqui / Piper) is the primary choice for this project.**

Reasons:
1. **Zero cost** — no API quota to worry about during development or demo.
2. **Privacy** — customer audio never leaves the machine.
3. **Offline** — works without internet, no outages.
4. **Latency is comparable** on CPU and faster on GPU.

ElevenLabs free tier is used only as a **quality benchmark** — a side-by-side demo to show stakeholders how a production upgrade would sound. When the client is ready to invest in premium TTS for a live deployment, ElevenLabs or Fish Audio would be the natural upgrade path.

> **Upgrade path:** Local TTS → ElevenLabs paid / Fish Audio when going to production with real phone calls.
