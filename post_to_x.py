import subprocess
import os
import requests

def get_last_commit_diff():
    # 1. Grab the structural text of your last commit and its code changes
    commit_msg = subprocess.check_output(["git", "log", "-1", "--pretty=%B"]).decode("utf-8").strip()
    git_diff = subprocess.check_output(["git", "diff", "HEAD~1", "HEAD"]).decode("utf-8")
    return commit_msg, git_diff[:2000] # Cap diff size for context window safety

def generate_x_post():
    commit_msg, diff = get_last_commit_diff()
    
    # 2. Frame the specialized system prompt for developer social optimization
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
    
    # Send to your Gemini API endpoint (Using a secure local environment variable)
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-2.5:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}]
    }
    
    response = requests.post(url, json=payload)
    tweet_draft = response.json()['candidates'][0]['content']['parts'][0]['text']
    
    print("\n--- 📝 YOUR AUTOMATED X POST DRAFT ---")
    print(tweet_draft)
    print("---------------------------------------\n")

if __name__ == "__main__":
    generate_x_post()