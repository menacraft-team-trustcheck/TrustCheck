# 📊 TrustCheck: Final Project Report — MenaCraft Hackathon 2026

## 🛡️ Core Concept
TrustCheck is a digital media verification suite designed to automate professional Open Source Intelligence (OSINT) workflows. It replaces the "one-shot AI prompt" with a dedicated, multi-axis investigation pipeline that identifies hidden forensic evidence.

## ✅ Accomplished Features

### Axis A: Neural Authenticity & Visual Forensics
- **Deepfake Prediction**: Leverages LLaMA 3.2 Vision and Qwen2.5-VL to detect AI generation fingerprints and lighting inconsistencies.
- **Local ELA Analysis**: Implemented a local OpenCV/Pillow-based **Error Level Analysis (ELA)** heatmap that identifies exactly which pixels have been digitally edited or re-compressed, providing zero-cost forensic mapping.

### Axis B: Acoustic Forensic Profiling (v3.0 Engine)
- **Neural Voice Detection**: Detects high-fidelity AI voices (Canva, ElevenLabs, Murf) that other systems miss.
- **Silicon Silence Extraction**: Identifies regions of absolute digital zero noise floors ($< -90\text{ dB}$)—a definitive artifact of neural vocoders.
- **Neural Synthesis Multiplier**: Implemented a non-linear scoring engine that exponentially flags "robotic perfection" when Jitter/Shimmer, Pitch Stability, and Energy Dynamics hit digital-flat thresholds simultaneously.
- **Acoustic Fingerprinting**: Analyzes micro-perturbations across pitch (Jitter) and amplitude (Shimmer) that are naturally occurring in human speech but absent in neural synthesis.

### Axis C: Context & Geolocation
- **Semantic Mapping**: Checks if visual content matches the user claim (e.g., verifying a Tunisian forest through semantic recognition).
- **Metadata Extraction**: Extracts camera make, model, exposure, and lens focal length.
- **GPS-Stripping Detection**: Identifies "Red Flag" signals when location data has been deliberately removed from GPS-capable devices.

### Axis D: Source & Credibility
- **Domain Forensics**: Checks for suspicious TLDs, emotional amplification patterns, and typosquatting.
- **Reputational Blending**: 60/40 weighted blend of local deterministic signals and LLM-based reputational analysis.

---

## 🤖 The Reasoning Oracle (Synthesis Layer)
All forensic reports (Visual, Acoustic, Contextual, Metadata, Credibility) are synthesized by a **Chief Investigator** (LLaMA 3.3 70B). This reasoning layer:
1.  **Identifies Contradictions**: e.g., "AI-flagged audio that is too high-fidelity (HNR > 25dB) but lacks any natural jitter."
2.  **Calculates Risk %**: Produces a weighted certainty score across all axes.
3.  **Delivers Narrative Verdicts**: Translates complex forensic data into 2-sentence actionable conclusions for the user.

## 🎨 Premium "Investigation Room" Dashboard
- **Next.js 15+ Core**: A high-performance, reactive OSINT dashboard built with modern React.
- **Cyber-Forensic Aesthetic**: Glassmorphism, neon green/cyan accents, and real-time scanning animations.
- **Holographic Visualization**: Real-time status pulses for providers and dynamic "heartbeat" animations during forensic analysis.
- **Static Scalability**: Built with 'next export' to ensure it can be served at zero-cost by the FastAPI engine on any port.

## 🚀 Future Roadmap
- **Blockchain Verification**: Integrate content hashing with provenance standards (C2PA).
- **Batch OSINT Intelligence**: Social graph analysis of cross-platform misinformation campaigns.
- **Advanced Video Deepfake temporal checks**: Detect frame-to-frame F0 inconsistencies.

---
**Prepared by Antigravity AI for the MenaCraft Hackathon — 2026**
