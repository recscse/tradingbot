import os
import sys
import argparse
import google.generativeai as genai
from github import Github

def review_pr(repo_name, pr_number, github_token, gemini_api_key):
    """
    AI-powered PR Reviewer using Gemini 2.0 Flash.
    Analyzes the diff of a PR and posts high-quality architectural reviews.
    """
    # 1. Setup GitHub & Gemini
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))
    
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # 2. Get PR Diff
    print(f"🔍 Analyzing PR #{pr_number}: {pr.title}")
    files = pr.get_files()
    
    overall_review = []
    
    for file in files:
        if file.status == "removed" or not file.patch:
            continue
            
        print(f"📄 Reviewing: {file.filename}")
        
        # 3. Request AI Review for each file with enhanced instruction
        prompt = f"""
        You are a Senior Trading Systems Architect and Lead DevOps Engineer. 
        Your goal is to provide a professional, critical, and constructive review of the following code diff.
        
        Context: High-frequency Algorithmic Trading Platform (Python/FastAPI/React).
        
        Critical Review Criteria:
        1. **Trading Integrity**: Look for race conditions in order execution, incorrect lot size handling, or lack of slippage consideration.
        2. **Risk Management**: Check if every trading operation has a stop-loss and proper position sizing logic.
        3. **Performance**: Identify O(N^2) operations in data processing or blocking calls in async functions.
        4. **Resilience**: Ensure API calls (Upstox, etc.) have try-except blocks and timeouts.
        5. **Clean Code**: Enforce PEP 8, consistent naming, and TypeScript best practices.
        
        File: {file.filename}
        Diff:
        {file.patch}
        
        Instructions for your response:
        - Be direct and technical. Avoid filler words like "I think" or "maybe".
        - If you find a bug, explain WHY it is a bug and PROVIDE a code snippet fix.
        - Use Markdown for formatting.
        - Format: [LINE_NUMBER]: [CRITICAL/SUGGESTION/BUG] - [Detail]
        - If the file is perfect, respond only with "LGTM".
        """
        
        try:
            response = model.generate_content(prompt)
            review_text = response.text.strip()
            
            if "LGTM" not in review_text and review_text:
                overall_review.append(f"#### 📄 `{file.filename}`\n\n{review_text}")
        except Exception as e:
            print(f"⚠️ Error reviewing {file.filename}: {e}")

    # 4. Post Consolidated Review to GitHub
    if overall_review:
        summary_intro = f"## 🤖 AI Architectural Review for PR #{pr_number}\n"
        summary_intro += "> **Role:** Senior Trading Architect Agent\n"
        summary_intro += "> **Model:** Gemini 2.0 Flash\n\n"
        
        full_comment = summary_intro + "\n\n---\n\n".join(overall_review)
        full_comment += "\n\n*Note: This review is automated. Please verify all suggestions before merging.*"
        
        pr.create_issue_comment(full_comment)
    else:
        pr.create_issue_comment("## 🤖 AI Architectural Review\n\n✅ **LGTM!** All changes follow our architectural standards. 🚀")

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
