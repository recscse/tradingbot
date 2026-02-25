import os
import sys
import argparse
import google.generativeai as genai
from github import Github

def triage_issue(repo_name, issue_number, github_token, gemini_api_key):
    """
    AI Bug Triager Agent.
    Analyzes new issues and suggests root causes and fixes.
    """
    # 1. Setup
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    issue = repo.get_issue(int(issue_number))
    
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    # 2. Analyze Issue Content
    print(f"🐞 Triaging Issue #{issue_number}: {issue.title}")
    
    # Get a list of key files to help the AI map the issue
    # We'll provide a simplified directory structure
    file_structure = """
    - app.py (Main Entry)
    - services/ (Trading, Auth, Data Services)
    - strategies/ (Trading Strategies)
    - ui/ (Frontend React Code)
    - database/ (Models and Repositories)
    - core/ (Config, Security, WebSockets)
    """
    
    prompt = f"""
    You are a Senior Debugging Engineer for an Algorithmic Trading Platform. 
    Analyze the following GitHub Issue and suggest a root cause and fix.
    
    Issue Title: {issue.title}
    Issue Body: {issue.body}
    
    Codebase Overview:
    {file_structure}
    
    Tasks:
    1. Identify the likely files involved.
    2. If there's a stack trace, explain what the error means.
    3. Suggest a specific fix or investigation steps.
    4. Assign a priority (Low, Medium, High, Critical).
    
    Format your response as:
    ### 🕵️ AI Diagnosis
    - **Likely Files:** [e.g., services/upstox_service.py]
    - **Root Cause:** [Explain what's happening]
    - **Priority:** [Priority Level]
    
    ### 🛠️ Suggested Fix
    ```python
    # [Your suggested code or investigation steps]
    ```
    """
    
    response = model.generate_content(prompt)
    ai_output = response.text.strip()
    
    # 3. Post to GitHub
    comment = f"## 🤖 AI Bug Triager Response

{ai_output}

*This is an automated response to help speed up resolution.*"
    issue.create_comment(comment)
    
    # 4. Add labels based on priority (if AI suggests)
    if "Priority: Critical" in ai_output:
        issue.add_to_labels("critical", "bug")
    elif "Priority: High" in ai_output:
        issue.add_to_labels("high-priority", "bug")
    else:
        issue.add_to_labels("bug")

    print("✅ Issue triage completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--github-token", required=True)
    parser.add_argument("--gemini-api-key", required=True)
    
    args = parser.parse_args()
    
    try:
        triage_issue(args.repo, args.issue, args.github_token, args.gemini_api_key)
    except Exception as e:
        print(f"❌ Error in Bug Triager: {e}")
        sys.exit(1)
