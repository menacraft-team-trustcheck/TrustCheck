# 🛡️ TrustCheck OSINT Platform
> **MenaCraft Hackathon 2026 Submission**
> Live Multi-Axis Forensic Verification Suite

TrustCheck is a high-performance, expert-level media verification platform designed to combat the "liar's dividend" and the rise of high-fidelity deepfakes. It moves beyond single-prompt AI checks by running a parallel, multi-axis investigation pipeline that resolves contradictions in forensic data.

## 🏗️ System Architecture: The 5-Axis Forensic Engine

TrustCheck doesn't just ask if something is "real." It investigates the content across 5 independent dimensions:

### 1. Visual Forensics (Axis A)
- **Neural Discovery**: Leverages LLaMA 3.2 Vision and Qwen2.5-VL to detect AI generation fingerprints, lighting inconsistencies, and neural artifacts.
- **Local ELA**: Replaced third-party vision heatmaps with a **local Error Level Analysis (ELA)** module. This analyzes JPEG re-save artifacts to identify exactly which regions of an image have been digitally manipulated.

### 2. Acoustic Forensics (Axis B)
- **Neural Voice Detection**: Analyzes audio for "Robotic Perfection." 
- **Micro-perturbation Analysis**: Detects Jitter (F0 instability) and Shimmer (amplitude instability) that are present in human speech but often missing in Neural TTS (Canva, ElevenLabs).
- **Vocoder Fingerprinting**: Identifies spectral-contrast anomalies characteristic of digital vocoders and neural synthesis.

### 3. Contextual Consistency (Axis C)
- **Semantic Mapping**: Checks if the visual content matches the user claim (e.g., "Is that really a forest in Tunisia?").
- **Fact-Check Integration**: Real-time cross-referencing with the **Google Fact Check Tools API** to identify known viral misinformation.

### 4. Digital Footprint (Axis D)
- **EXIF Forensics**: Extracts deep metadata from files including camera serials, lens focal length, and software history (Adobe Photoshop/Canva tags).
- **GPS-Stripping Detection**: Flags "high-suspicion" signals when GPS hardware exists but coordinates have been deliberately scrubbed.

### 5. Source Credibility (Axis E)
- **Deterministic Signals**: Checks for suspicious TLDs (.xyz, .top), typosquatting, and emotional amplification patterns.
- **Reputational Assessment**: Blends automated domain forensics with LLM reputational analysis.

---

## 🧠 Master Forensic Synthesis
The platform features a **Chief Investigator** reasoning layer (LLaMA 3.3 70B). This layer reviews all 5 axis reports, identifies contradictions (e.g., "AI-flagged audio that appears perfectly studio-clean"), and produces a final **Weighted Risk Verdict** (CRITICAL to LOW).

## 🛠️ Technical Stack
- **Backend**: Python (FastAPI), ThreadPoolExecutor (Parallel analysis).
- **ML/LLM**: Groq (LLaMA Series), OpenRouter (Vision Models), DeepSeek.
- **Digital Signal Processing**: Librosa (Acoustics), OpenCV (Image ELA), piexif.
- **Database**: Supabase (Forensic history + JSONB).
- **Frontend**: **Next.js 15+ "Investigation Room" Dashboard**. A high-performance, reactive React frontend using Radix UI and Tailwind CSS for a premium "Cyber-Forensic" aesthetic. Built with static-export for seamless FastAPI integration.

## 🚀 Getting Started
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Configure `.env` with your API keys (Groq, OpenRouter, Google, Supabase).
4. Run the engine: `python -m uvicorn app:app --reload`
5. Access the command center at `http://localhost:8000/ui`

---
**Developed for the MenaCraft Hackathon — 2026**
