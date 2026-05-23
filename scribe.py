import subprocess
import sys
import os
from google import genai
from google.genai import types
from notion_client import Client
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Explicitly load the local .env configuration file
load_dotenv()

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
    """Safely extracts the staged changes or the last commit differences with strict UTF-8 rules."""
    try:
        # Check tracking difference between current HEAD and remote tracking branch
        result = subprocess.run(
            ["git", "diff", "origin/main...HEAD"], 
            capture_output=True, 
            text=True, 
            encoding="utf-8",
            errors="ignore", 
            check=True
        )
        
        diff_text = result.stdout.strip()
        if not diff_text:
            # Fallback to look exclusively at the very last commit payload 
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD"], 
                capture_output=True, 
                text=True, 
                encoding="utf-8",
                errors="ignore",
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

    # Print a diagnostic metrics log to check payload scale size
    print(f"📊 Analyzing code delta payload size: {len(git_diff)} characters.")

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
    
    try:
        # FIX: Enforce an explicit HTTP timeout limit to ensure the terminal can NEVER freeze indefinitely
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Analyze this code delta:\n\n{git_diff[:5000]}",  # Cap diff at 5000 characters for safety
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                # Set underlying HTTP gateway constraints safely
                http_options={'timeout': 20.0} 
            )
        )
        return response.text
    except Exception as e:
        print(f"❌ Gemini API Network Gateway Timed Out: {e}")
        return "### Analysis Timeout\nBackend extraction connection dropped during structural network processing."

def push_to_notion(structured_markdown: str):
    if "Analysis Timeout" in structured_markdown or "Empty Log" in structured_markdown:
        print("⚠️ Skipping Notion sync due to empty or missing analysis payload.")
        return

    print("🚀 Shipping concise toggle-based logs to Notion...")
    
    sections = {"concepts": [], "built": [], "risks": []}
    current_bucket = "concepts"
    
    for line in structured_markdown.split("\n"):
        line = line.strip().replace("**", "").replace("* ", "• ")
        if not line or "##" in line:
            if "1. Deep Concepts" in line: current_bucket = "concepts"
            elif "2. Structural" in line: current_bucket = "built"
            elif "3. Optimization" in line: current_bucket = "risks"
            continue
        
        sections[current_bucket].append(line)

    concepts_text = "\n".join(sections["concepts"])[:2000]
    built_text = "\n".join(sections["built"])[:2000]
    risks_text = "\n".join(sections["risks"])[:2000]

    toggle_blocks = [
        {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": "🧩 1. Deep Concepts Unboxed"}}],
                "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": concepts_text or "No concepts logged."}}]}}]
            }
        },
        {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": "🛠️ 2. Structural Implementations"}}],
                "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": built_text or "No structural updates."}}]}}]
            }
        },
        {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"type": "text", "text": {"content": "🐛 3. Optimization Opportunities & Risks"}}],
                "children": [{"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"type": "text", "text": {"content": risks_text or "No vulnerabilities flagged."}}]}}]
            }
        }
    ]

    try:
        notion.pages.create(
            parent={"database_id": config.NOTION_DATABASE_ID},
            properties={"Name": {"title": [{"text": {"content": "Concise Code Audit Log"}}]}},
            children=toggle_blocks
        )
        print("✅ Clean, interactive toggles anchored in Notion!")
    except Exception as e:
        print(f"❌ Notion write failed: {e}")

if __name__ == "__main__":
    print("📦 Gathering local code diffs...")
    diff = get_git_diff()
    
    print("🤖 Processing code mechanics via Gemini Core...")
    analysis = analyze_code_changes(diff)
    
    push_to_notion(analysis)
    print("✨ Sync cycle complete!")