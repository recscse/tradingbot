import os
import sys
import argparse
import google.generativeai as genai
from github import Github
from datetime import datetime

def generate_docs_and_changelog(repo_name, pr_number, github_token, gemini_api_key):
    """
    AI Documentation & Changelog Agent.
    Analyzes the PR and generates a semantic changelog and doc updates.
    """
    # 1. Setup
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))
    
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    # 2. Analyze PR Diff for Documentation Needs
    print(f"📄 Analyzing PR #{pr_number} for documentation impact...")
    files = pr.get_files()
    file_list = [f.filename for f in files]
    
    # Combined diff for better context (limiting size for LLM)
    combined_diff = "
".join([f.patch for f in files if f.patch])[:10000]
    
    prompt = f"""
    You are a Technical Writer and Senior Developer. Review the following Pull Request details and diff.
    PR Title: {pr.title}
    PR Body: {pr.body}
    Changed Files: {', '.join(file_list)}
    
    Tasks:
    1. Generate a "Semantic Changelog" entry (What changed? Why? Impact?).
    2. Identify if any NEW services, strategies, or APIs were added that require new documentation files.
    3. Suggest updates to the main README.md or existing docs/ files if necessary.
    
    Diff:
    {combined_diff}
    
    Format your response as:
    ### 📝 Semantic Changelog
    [A human-readable summary of the changes]
    
    ### 📚 Documentation Impact
    - [Impact 1: e.g., Update README to include new Upstox endpoint]
    - [Impact 2: e.g., New strategy 'X' added to docs/strategies/]
    """
    
    response = model.generate_content(prompt)
    ai_output = response.text.strip()
    
    # 3. Post to GitHub
    comment = f"## 🤖 AI Documentation & Changelog Agent

{ai_output}

"
    pr.create_issue_comment(comment)
    print("✅ Documentation & Changelog suggestions posted.")
    
    # 4. (Optional) Auto-update CHANGELOG.md if in a specific branch/environment
    # For now, we'll just suggest the update to keep it safe.

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True)
    parser.add_argument("--github-token", required=True)
    parser.add_argument("--gemini-api-key", required=True)
    
    args = parser.parse_args()
    
    try:
        generate_docs_and_changelog(args.repo, args.pr, args.github_token, args.gemini_api_key)
        print("✅ Docs Agent run completed.")
    except Exception as e:
        print(f"❌ Error in Docs Agent: {e}")
        sys.exit(1)
