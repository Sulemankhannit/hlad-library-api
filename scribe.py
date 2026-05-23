# scribe.py
import subprocess
import sys
from google import genai
from google.genai import types
from notion_client import Client
from pydantic_settings import BaseSettings

class ScribeSettings(BaseSettings):
    NOTION_TOKEN: str
    NOTION_DATABASE_ID: str
    GEMINI_API_KEY: str

    model_config = {"env_file": ".env", "extra": "ignore"}

try:
    config = ScribeSettings()
except Exception as e:
    print(f"❌ Scribe Configuration Error: {e}")
    sys.exit(1)

notion = Client(auth=config.NOTION_TOKEN)
ai_client = genai.Client(api_key=config.GEMINI_API_KEY)

def get_git_diff() -> str:
    """Safely extracts the staged changes or the last commit differences."""
    try:
        # We fetch the difference between our current local state and the remote branch
        # This captures everything we are about to push.
        result = subprocess.run(
            ["git", "diff", "origin/main...HEAD"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # Fallback: if there is no remote tracking branch yet, grab the last commit
        diff_text = result.stdout.strip()
        if not diff_text:
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            diff_text = result.stdout.strip()
            
        return diff_text if diff_text else "No code changes detected."
    except Exception as e:
        print(f"⚠️ Failed to gather Git tracking details: {e}")
        return "No code changes detected."

def analyze_code_changes(git_diff: str) -> str:
    """Instructs Gemini to audit the code delta for system design and architecture logs."""
    if git_diff == "No code changes detected.":
        return "### Empty Log\nNo notable backend code alterations detected during this sync window."

    system_instruction = (
        "You are an elite Principal Backend Engineer auditing a junior's code delta. "
        "Analyze the incoming raw git diff output and transform it into a world-class "
        "interview preparation curriculum log entry. "
        "Structure the output with these exact headers:\n\n"
        "## 🧩 1. Deep Concepts Unboxed\n"
        "Deduce what underlying architectural or software engineering mechanics were implemented "
        "(e.g., ASGI loop, Context Managers, Relational Normalization, Pydantic Type Coercion). "
        "Explain WHY they matter for performance and scalability in interviews.\n\n"
        "## 🛠️ 2. Structural Implementations\n"
        "List the precise files changed, new functions engineered, and changes to the data models.\n\n"
        "## 🐛 3. Optimization Opportunities & Risks\n"
        "Actively look at the code lines removed/added. Point out potential race conditions, "
        "unhandled errors, memory leaks, or execution blocks introduced by these changes."
    )
    
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=f"Analyze this code delta:\n\n{git_diff}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2, # Highly analytical, cold, deterministic execution mapping
        )
    )
    return response.text

def push_to_notion(structured_markdown: str):
    print("🚀 Shipping automated Git-driven audit to Notion Vault...")
    
    # Simple block truncation to respect Notion's 2000 character limit per paragraph block
    truncated_content = structured_markdown if len(structured_markdown) < 2000 else structured_markdown[:1995] + "\n..."
    
    notion.pages.create(
        parent={"database_id": config.NOTION_DATABASE_ID},
        properties={
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": "Automated Code Log: HLAD Library Service"
                        }
                    }
                ]
            }
        },
        children=[
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": truncated_content}
                        }
                    ]
                }
            }
        ]
    )
    print("✅ Entry securely anchored inside your learning database!")

if __name__ == "__main__":
    print("📦 Gathering local code diffs...")
    diff = get_git_diff()
    
    print("🤖 Processing code mechanics via Gemini Core...")
    analysis = analyze_code_changes(diff)
    
    print("\n--- Visualizing Generated Analysis ---")
    print(analysis)
    print("--------------------------------------\n")
    
    push_to_notion(analysis)