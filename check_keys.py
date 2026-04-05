import os
from dotenv import load_dotenv
load_dotenv()

keys = [
    "GROQ_API_KEY",
    "DEEPSEEK_API_KEY", 
    "OPENROUTER_API_KEY",
    "HF_API_KEY",
    "GOOGLE_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
]

for k in keys:
    val = os.environ.get(k, "")
    if val:
        print(f"  {k}: SET ({val[:8]}...)")
    else:
        print(f"  {k}: MISSING")
