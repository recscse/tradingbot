import os
import sys
import argparse
import google.generativeai as genai
from github import Github

def review_pr(repo_name, pr_number, github_token, gemini_api_key):
    """
    AI-powered PR Reviewer using Gemini.
    Analyzes the diff of a PR and posts review comments.
    """
    # 1. Setup GitHub & Gemini
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))
    
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')
    
    # 2. Get PR Diff
    print(f"🔍 Analyzing PR #{pr_number}: {pr.title}")
    files = pr.get_files()
    
    for file in files:
        if file.status == "removed":
            continue
            
        print(f"📄 Reviewing: {file.filename}")
        
        # 3. Request AI Review for each file
        prompt = f"""
        You are a Senior Trading Systems Architect. Review the following code diff from a Pull Request.
        Repository context: Algorithmic trading platform (FastAPI/Python/React).
        
        Focus on:
        1. Trading Safety: Logic bugs in order execution, risk management, slippage.
        2. Scalability: Efficient data handling, database queries.
        3. Code Quality: PEP 8 (Python) or clean TypeScript.
        4. Edge Cases: Handling API failures, timeouts, invalid user inputs.
        
        File: {file.filename}
        Diff:
        {file.patch}
        
        Return your review in the following format:
        [LINE_NUMBER]: [CRITICAL/SUGGESTION] - [Observation]
        
        If the code looks perfect, just say "LGTM".
        """
        
        response = model.generate_content(prompt)
        review_text = response.text.strip()
        
        if "LGTM" in review_text or not review_text:
            continue
            
        # 4. Parse AI Suggestions and post to GitHub
        # (Simplified: Posting as a single summary comment per file for now)
        summary = f"### 🤖 AI Code Review for `{file.filename}`

{review_text}"
        pr.create_issue_comment(summary)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True)
    parser.add_argument("--github-token", required=True)
    parser.add_argument("--gemini-api-key", required=True)
    
    args = parser.parse_args()
    
    try:
        review_pr(args.repo, args.pr, args.github_token, args.gemini_api_key)
        print("✅ PR Review completed successfully.")
    except Exception as e:
        print(f"❌ Error during PR review: {e}")
        sys.exit(1)
