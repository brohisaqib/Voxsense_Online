from groq import Groq
from dotenv import load_dotenv
from pathlib import Path
import os

# force .env path
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    print("❌ API key not found - .env load issue")
    exit()

print("API:", api_key[:15], "...")

client = Groq(api_key=api_key)

try:
    res = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL"),
        messages=[{"role": "user", "content": "Hello"}]
    )

    print("✅ Working")
    print(res.choices[0].message.content)

except Exception as e:
    print("❌ Error:", e)