# 🚀 Pull Request Automation Guide
**Automated PR Creation and Merging for Trading Bot**

## 📋 Overview

Your repository now has **full PR automation** that handles:
1. **Auto PR Creation** - Creates PRs when you push to feature branches
2. **Auto Merge** - Merges PRs automatically when conditions are met
3. **Branch Management** - Validates branch names and cleans up old branches

## 🎯 How It Works

### **1. Auto PR Creation**

**Triggers when you push to:**
- `feature/*` branches
- `fix/*` branches  
- `hotfix/*` branches
- `enhancement/*` branches
- `refactor/*` branches

**What it does:**
- ✅ Creates PR automatically with smart title and description
- 🏷️ Adds relevant labels based on file changes
- 👥 Assigns appropriate reviewers
- 📊 Analyzes code changes and impact
- 🔍 Provides testing checklist

### **2. Auto Merge**

**Merges automatically when:**
- ✅ All CI checks pass (Frontend CI, Backend CI, PR Review)
- ✅ No merge conflicts
- ✅ Required approvals obtained (if needed)
- ✅ No "changes requested" reviews
- 🏷️ PR has auto-merge eligible labels

**Safety checks:**
- 🛡️ Trading-related PRs require senior approval
- 🚨 Hotfix PRs get expedited processing  
- 🚫 Draft PRs are never auto-merged
- ⛔ PRs with `no-auto-merge` label are skipped

## 💡 Usage Examples

### **Example 1: Simple Feature**
```bash
# Create and switch to feature branch
git checkout -b feature/add-new-indicator

# Make your changes
echo "New trading indicator" > indicator.py
git add .
git commit -m "Add new RSI indicator for trading signals"

# Push to trigger auto PR creation
git push origin feature/add-new-indicator
```

**Result:** 
- 🤖 Auto-creates PR with title: "feat: add new indicator" 
- 🏷️ Adds labels: `auto-created`, `feature`, `backend`, `trading`
- 👥 Requests review from backend reviewer
- ⏳ Waits for CI checks, then auto-merges if all pass

### **Example 2: Hotfix**
```bash
# Create hotfix branch
git checkout -b hotfix/fix-trading-bug

# Fix critical issue
git add .
git commit -m "Fix critical order execution bug"
git push origin hotfix/fix-trading-bug
```

**Result:**
- 🚨 Auto-creates PR with `hotfix` and `high-priority` labels
- 👨‍💼 Requests review from senior developer  
- ⚡ Auto-merges immediately after checks pass (expedited)

### **Example 3: Manual Control**
```bash
# Create branch but prevent auto-merge
git checkout -b feature/experimental-feature
git add .
git commit -m "Add experimental trading strategy [skip-pr]"
git push origin feature/experimental-feature
```

**Result:**
- 🚫 `[skip-pr]` in commit message prevents auto PR creation
- 📝 Create PR manually when ready
- 🏷️ Add `no-auto-merge` label to prevent auto-merge

## 🛠️ Configuration Options

### **Control Auto PR Creation**

**Skip auto PR creation:**
- Add `[skip-pr]` to your commit message
- Push to non-matching branch names (e.g., `temp/testing`)

**Customize PR content:**
- Use conventional commit format: `feat:`, `fix:`, `hotfix:`, etc.
- Branch name becomes part of PR title automatically

### **Control Auto Merge**

**Enable auto-merge:**
- Use conventional commit titles (`feat:`, `fix:`, etc.)
- Keep PRs focused and small
- Ensure all tests pass

**Prevent auto-merge:**
- Add `no-auto-merge` label to PR
- Keep PR in draft mode
- Use non-conventional PR titles

### **Branch Naming Convention**

**Required format:**
```bash
feature/description      # New features
fix/description         # Bug fixes  
hotfix/description      # Urgent fixes
enhancement/description # Improvements
refactor/description    # Code refactoring
docs/description        # Documentation
test/description        # Tests
chore/description       # Maintenance
```

**Examples:**
```bash
✅ feature/add-fibonacci-strategy
✅ fix/order-execution-timeout  
✅ hotfix/token-refresh-error
❌ my-feature-branch
❌ test_branch
❌ experimental
```

## ⚙️ Customization

### **Add Team Members**

Edit `.github/workflows/auto-pr-creation.yml`:
```yaml
# Replace with actual GitHub usernames
REVIEWERS+=("your-backend-dev")     # Backend reviewer
REVIEWERS+=("your-frontend-dev")    # Frontend reviewer  
REVIEWERS+=("your-senior-dev")      # Senior/Trading reviewer
```

### **Modify Auto-Merge Rules**

Edit `.github/workflows/auto-merge.yml`:
```yaml
# Required checks (customize these)
const requiredChecks = [
  'Frontend CI/CD Clean / test',
  'Backend CI/CD / test', 
  'PR Review & Quality / pr-validation'
];
```

### **Change Approval Requirements**

```yaml
# Customize approval logic
const needsSeniorApproval = prInfo.labels.some(label => 
  ['trading', 'high-priority', 'hotfix', 'security'].includes(label)
);
```

## 🚨 Safety Features

### **Trading System Protection**
- 🛡️ **Trading-related changes** require senior developer approval
- 🔍 **Security changes** get extra scrutiny
- ⚠️ **Critical files** (requirements.txt, migrations) trigger alerts
- 📊 **Large PRs** (20+ files) get `size/XL` label and extra review

### **Quality Gates**
- ✅ **All CI checks** must pass before merge
- 🔄 **No merge conflicts** allowed
- 👥 **Required approvals** must be obtained
- 🚫 **Changes requested** blocks auto-merge

### **Rollback Safety**
- 📈 **Squash merge** keeps clean history
- 🏷️ **Auto-generated commit messages** for traceability
- 💬 **Detailed merge comments** with full context
- 🔄 **Easy revert** if issues are found

## 📊 Monitoring & Insights

### **PR Analytics**
- 📈 Track auto-merge success rate
- ⏱️ Monitor time from PR creation to merge
- 🏷️ Analyze which labels correlate with faster merges
- 👥 Review team response times

### **Branch Health**
- 🧹 **Weekly stale branch cleanup**
- 📊 **Branch naming compliance** reports
- 🔄 **Automatic branch deletion** after merge

## 🆘 Troubleshooting

### **PR Not Auto-Created**
- ✅ Check branch name follows convention
- ✅ Ensure commit message doesn't contain `[skip-pr]`
- ✅ Verify you pushed to a feature branch (not main)
- ✅ Check GitHub Actions logs for errors

### **Auto-Merge Not Working**  
- ✅ Verify all CI checks are passing
- ✅ Check for merge conflicts
- ✅ Ensure no `no-auto-merge` label
- ✅ Confirm PR is not in draft mode
- ✅ Check if approvals are required and obtained

### **Branch Name Rejected**
- ✅ Use format: `feature/your-description`
- ✅ Only use letters, numbers, hyphens, underscores, dots
- ✅ Check the issue created for guidance
- ✅ Rename branch: `git branch -m old-name feature/new-name`

## 🎉 Benefits

### **For Developers**
- ⚡ **Faster workflow** - No manual PR creation
- 🎯 **Focus on coding** - Less process overhead  
- 🔄 **Consistent quality** - Automated checks and reviews
- 📊 **Better insights** - Automatic change analysis

### **For Team**
- 🚀 **Faster delivery** - Automated merge when ready
- 🛡️ **Better security** - Consistent review process
- 🧹 **Cleaner repository** - Automatic branch cleanup
- 📈 **Improved quality** - Consistent standards enforcement

---

**Your PR automation is now live! 🚀 Start using feature branches and watch the magic happen! ✨**