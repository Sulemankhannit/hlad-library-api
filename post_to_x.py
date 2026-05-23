import subprocess
import os
import requests
import sys
# 1. Import the configuration utility
from dotenv import load_dotenv

# 2. Force it to load the physical .env file from your current folder path
load_dotenv()

def get_last_commit_diff():
    try:
        commit_msg = subprocess.check_output(["git", "log", "-1", "--pretty=%B"]).decode("utf-8").strip()
        git_diff = subprocess.check_output(["git", "diff", "HEAD~1", "HEAD"]).decode("utf-8")
        return commit_msg, git_diff[:2000]
    except Exception as e:
        print(f"❌ [Git Error]: Failed to read repository history. Detail: {e}")
        sys.exit(1)

def generate_x_post():
    commit_msg, diff = get_last_commit_diff()
    
    system_prompt = (
        "You are an elite, highly engaging tech builder tracking your journey on X. "
        "Write a short, punchy post based on the provided Git diff using 'The Engineering Journey' format.\n\n"
        "CRITICAL RULES:\n"
        "1. THE HOOK (First 2 lines): Explain the win or the failure in simple, high-impact English. "
        "Make it relatable to a non-technical person (e.g., 'Fixed a bug where my system was accidentally talking to itself').\n"
        "2. THE VALUE (Next 2 lines): Explain why this matters for the user experience or system stability. "
        "Recruiters love this because it shows product mindset.\n"
        "3. THE GEEK DROP (Last 2 lines): Drop a highly targeted engineering detail (like space complexity, async architecture, "
        "or network states). Founders love this because it proves you aren't faking it.\n"
        "4. TONE: Confident, authentic, building-in-public vibe. Zero corporate boilerplate. Absolutely no emojis like 🚀."
    )
    
    prompt = f"Commit Message: {commit_msg}\n\nCode Differential:\n{diff}"
    
    # 3. This will now successfully match the exact string inside your .env file!
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ [Environment Error]: GEMINI_API_KEY variable is missing from your .env file or OS memory.")
        sys.exit(1)
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}]
    }
    
    print("📡 Contacting Gemini API Gateway using .env credentials...")
    response = requests.post(url, json=payload)
    response_json = response.json()
    
    if 'candidates' in response_json and len(response_json['candidates']) > 0:
        tweet_draft = response_json['candidates'][0]['content']['parts'][0]['text']
        print("\n--- 📝 YOUR AUTOMATED X POST DRAFT ---")
        print(tweet_draft)
        print("---------------------------------------\n")
    else:
        print("\n❌ [Gemini API Server Error Call Failed]")
        print(f"HTTP Status Code: {response.status_code}")
        print("Raw Server Response Payload:")
        print(response.text)
        print("----------------------------------------\n")

if __name__ == "__main__":
    generate_x_post()