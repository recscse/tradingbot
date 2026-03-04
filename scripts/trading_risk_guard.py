import os
import sys
import re
import argparse

# --- Risk Configuration ---
# Regex patterns for dangerous patterns
RISK_PATTERNS = {
    "hardcoded_secrets": re.compile(r"(API_KEY|SECRET|PASSWORD|TOKEN|TOKEN_SECRET)\s*=\s*['\"][a-zA-Z0-9_\-]{10,}['\"]", re.IGNORECASE),
    "unlocalized_time": re.compile(r"datetime\.now\(\)(?!\.astimezone|.*tz=)", re.IGNORECASE),
    "missing_stop_loss": re.compile(r"place_order\((?!.*stop_loss)", re.IGNORECASE),
    "hardcoded_lots": re.compile(r"quantity\s*=\s*\d+", re.IGNORECASE),
}

# Paths to skip
SKIP_PATHS = ["tests/", "scripts/", "venv/", ".venv/"]

def scan_file(file_path):
    """
    Scans a single file for risk patterns.
    """
    violations = []
    
    # Only scan Python files for now
    if not file_path.endswith('.py'):
        return violations
        
    if any(skip in file_path for skip in SKIP_PATHS):
        return violations

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            line_num = i + 1
            for risk_type, pattern in RISK_PATTERNS.items():
                if pattern.search(line):
                    # Special check for stop_loss: only flag in trading related files
                    if risk_type == "missing_stop_loss" and "trading" not in file_path:
                        continue
                        
                    violations.append({
                        "type": risk_type,
                        "line": line_num,
                        "content": line.strip(),
                        "file": file_path
                    })
    except Exception as e:
        print(f"⚠️ Could not read {file_path}: {e}")
        
    return violations

def main(diff_files):
    """
    Main entry point for the risk guard.
    """
    all_violations = []
    
    for file_path in diff_files:
        if os.path.exists(file_path):
            violations = scan_file(file_path)
            all_violations.extend(violations)
            
    if all_violations:
        print("\n🚨 TRADING RISK VIOLATIONS DETECTED!")
        print("=" * 60)
        for v in all_violations:
            print(f"FAILED: {v['file']}:{v['line']}")
            print(f"TYPE:   {v['type'].upper()}")
            print(f"CODE:   {v['content']}")
            print("-" * 60)
        
        print(f"\n❌ Total violations: {len(all_violations)}")
        sys.exit(1)
    else:
        print("✅ No trading risk violations detected.")
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs='+', help="List of files to scan")
    args = parser.parse_args()
    
    main(args.files)
