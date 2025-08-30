#!/usr/bin/env python3
"""
Automated Coding Standards Checker

This script validates that all code follows the comprehensive coding standards
defined in CLAUDE.md, LINE_BY_LINE_STANDARDS.md, and related documentation.
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

class CodingStandardsChecker:
    """Comprehensive coding standards validation."""
    
    def __init__(self, project_root: str):
        """Initialize the standards checker.
        
        Args:
            project_root: Root directory of the project to check
        """
        self.project_root = Path(project_root)
        self.violations: List[Dict[str, str]] = []
        self.python_files: List[Path] = []
        self.js_files: List[Path] = []
        
    def check_all_standards(self) -> bool:
        """Execute comprehensive standards check.
        
        Returns:
            True if all standards pass, False otherwise
        """
        print("🔍 Running Comprehensive Coding Standards Check...")
        
        self._discover_files()
        
        # Python-specific checks
        for python_file in self.python_files:
            self._check_python_file(python_file)
            
        # JavaScript/React-specific checks
        for js_file in self.js_files:
            self._check_javascript_file(js_file)
            
        # Cross-cutting concerns
        self._check_security_patterns()
        self._check_financial_precision()
        self._check_documentation_standards()
        
        return self._report_results()
        
    def _discover_files(self) -> None:
        """Discover all relevant code files."""
        # Python files
        self.python_files = list(self.project_root.glob("**/*.py"))
        self.python_files = [f for f in self.python_files if not self._should_skip_file(f)]
        
        # JavaScript/TypeScript files
        self.js_files = list(self.project_root.glob("**/*.js"))
        self.js_files.extend(self.project_root.glob("**/*.jsx"))
        self.js_files.extend(self.project_root.glob("**/*.ts"))
        self.js_files.extend(self.project_root.glob("**/*.tsx"))
        self.js_files = [f for f in self.js_files if not self._should_skip_file(f)]
        
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped from analysis."""
        skip_patterns = [
            "venv/", "node_modules/", ".git/", "__pycache__/",
            "build/", "dist/", ".pytest_cache/", "coverage/"
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)
        
    def _check_python_file(self, file_path: Path) -> None:
        """Comprehensive Python file standards check."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Parse AST for deeper analysis
            try:
                tree = ast.parse(content, filename=str(file_path))
                self._check_python_ast(tree, file_path)
            except SyntaxError as e:
                self._add_violation(file_path, "syntax_error", f"Syntax error: {e}")
                
            # Content-based checks
            self._check_python_content(content, file_path)
            
        except Exception as e:
            self._add_violation(file_path, "file_error", f"Error reading file: {e}")
            
    def _check_python_ast(self, tree: ast.AST, file_path: Path) -> None:
        """Check Python AST for standards compliance."""
        for node in ast.walk(tree):
            # Function definition checks
            if isinstance(node, ast.FunctionDef):
                self._check_function_standards(node, file_path)
                
            # Class definition checks
            elif isinstance(node, ast.ClassDef):
                self._check_class_standards(node, file_path)
                
            # Variable assignment checks
            elif isinstance(node, ast.Assign):
                self._check_variable_standards(node, file_path)
                
    def _check_function_standards(self, node: ast.FunctionDef, file_path: Path) -> None:
        """Check function against coding standards."""
        func_name = node.name
        
        # Naming convention check
        if not self._is_snake_case(func_name) and not func_name.startswith('_'):
            self._add_violation(
                file_path, "naming_convention", 
                f"Function '{func_name}' should use snake_case naming"
            )
            
        # Docstring check
        docstring = ast.get_docstring(node)
        if not docstring and not func_name.startswith('_'):
            self._add_violation(
                file_path, "missing_docstring", 
                f"Function '{func_name}' missing comprehensive docstring"
            )
        elif docstring:
            self._check_docstring_quality(docstring, func_name, file_path)
            
        # Type hints check
        if not node.returns and not func_name.startswith('_'):
            self._add_violation(
                file_path, "missing_type_hints", 
                f"Function '{func_name}' missing return type hint"
            )
            
        # Parameter type hints
        for arg in node.args.args:
            if not arg.annotation and arg.arg != 'self':
                self._add_violation(
                    file_path, "missing_type_hints", 
                    f"Parameter '{arg.arg}' in function '{func_name}' missing type hint"
                )
                
    def _check_docstring_quality(self, docstring: str, func_name: str, file_path: Path) -> None:
        """Check docstring quality and completeness."""
        required_sections = ['Args:', 'Returns:', 'Raises:']
        
        # Check for required sections in public functions
        if not func_name.startswith('_'):
            for section in required_sections:
                if section not in docstring:
                    self._add_violation(
                        file_path, "incomplete_docstring", 
                        f"Function '{func_name}' docstring missing '{section}' section"
                    )
                    
    def _check_class_standards(self, node: ast.ClassDef, file_path: Path) -> None:
        """Check class against coding standards."""
        class_name = node.name
        
        # PascalCase naming check
        if not self._is_pascal_case(class_name):
            self._add_violation(
                file_path, "naming_convention", 
                f"Class '{class_name}' should use PascalCase naming"
            )
            
        # Docstring check
        docstring = ast.get_docstring(node)
        if not docstring:
            self._add_violation(
                file_path, "missing_docstring", 
                f"Class '{class_name}' missing comprehensive docstring"
            )
            
    def _check_variable_standards(self, node: ast.Assign, file_path: Path) -> None:
        """Check variable assignment standards."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                
                # Check for descriptive naming
                if self._is_generic_name(var_name):
                    self._add_violation(
                        file_path, "generic_naming", 
                        f"Variable '{var_name}' has generic name, use descriptive naming"
                    )
                    
    def _check_python_content(self, content: str, file_path: Path) -> None:
        """Check Python file content for standards compliance."""
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # f-string usage check
            if '.format(' in line or '%' in line and 'f"' not in line and 'f\'' not in line:
                self._add_violation(
                    file_path, "string_formatting", 
                    f"Line {line_num}: Use f-strings instead of .format() or % formatting"
                )
                
            # Hardcoded secrets check
            if self._contains_hardcoded_secret(line):
                self._add_violation(
                    file_path, "security_violation", 
                    f"Line {line_num}: Potential hardcoded secret detected"
                )
                
            # Float for financial calculations
            if 'float(' in line and ('price' in line.lower() or 'money' in line.lower() 
                                   or 'amount' in line.lower() or 'balance' in line.lower()):
                self._add_violation(
                    file_path, "financial_precision", 
                    f"Line {line_num}: Use Decimal instead of float for financial calculations"
                )
                
    def _check_javascript_file(self, file_path: Path) -> None:
        """Check JavaScript/React file for standards compliance."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Class component check (should use functional components)
                if 'class ' in line and 'extends React.Component' in line:
                    self._add_violation(
                        file_path, "react_standards", 
                        f"Line {line_num}: Use functional components with hooks instead of class components"
                    )
                    
                # Missing accessibility attributes
                if '<button' in line and 'aria-label' not in line and 'aria-labelledby' not in line:
                    self._add_violation(
                        file_path, "accessibility", 
                        f"Line {line_num}: Button missing accessibility attributes (aria-label)"
                    )
                    
        except Exception as e:
            self._add_violation(file_path, "file_error", f"Error reading file: {e}")
            
    def _check_security_patterns(self) -> None:
        """Check for security anti-patterns across all files."""
        # This would implement comprehensive security checks
        pass
        
    def _check_financial_precision(self) -> None:
        """Check financial calculation precision standards."""
        # This would implement financial-specific validation
        pass
        
    def _check_documentation_standards(self) -> None:
        """Check documentation completeness and quality."""
        # Check for README, API docs, etc.
        pass
        
    def _is_snake_case(self, name: str) -> bool:
        """Check if name follows snake_case convention."""
        return re.match(r'^[a-z][a-z0-9_]*[a-z0-9]$', name) is not None
        
    def _is_pascal_case(self, name: str) -> bool:
        """Check if name follows PascalCase convention."""
        return re.match(r'^[A-Z][a-zA-Z0-9]*$', name) is not None
        
    def _is_generic_name(self, name: str) -> bool:
        """Check if variable name is too generic."""
        generic_names = {'data', 'item', 'value', 'val', 'temp', 'var', 'obj', 'result'}
        return name.lower() in generic_names
        
    def _contains_hardcoded_secret(self, line: str) -> bool:
        """Check if line contains potential hardcoded secrets."""
        patterns = [
            r'password\s*=\s*["\'][^"\']{8,}["\']',
            r'api_key\s*=\s*["\'][^"\']{20,}["\']',
            r'secret\s*=\s*["\'][^"\']{16,}["\']',
            r'token\s*=\s*["\'][^"\']{32,}["\']'
        ]
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns)
        
    def _add_violation(self, file_path: Path, violation_type: str, message: str) -> None:
        """Add a standards violation."""
        self.violations.append({
            'file': str(file_path.relative_to(self.project_root)),
            'type': violation_type,
            'message': message
        })
        
    def _report_results(self) -> bool:
        """Report standards check results."""
        if not self.violations:
            print("✅ All coding standards checks passed!")
            return True
            
        print(f"❌ Found {len(self.violations)} coding standards violations:")
        print()
        
        # Group violations by type
        violations_by_type = {}
        for violation in self.violations:
            violation_type = violation['type']
            if violation_type not in violations_by_type:
                violations_by_type[violation_type] = []
            violations_by_type[violation_type].append(violation)
            
        # Report by category
        for violation_type, violations in violations_by_type.items():
            print(f"📋 {violation_type.replace('_', ' ').title()} ({len(violations)} issues):")
            for violation in violations[:5]:  # Limit to first 5 per category
                print(f"  📄 {violation['file']}: {violation['message']}")
            if len(violations) > 5:
                print(f"  ... and {len(violations) - 5} more")
            print()
            
        print("🔧 Please fix these violations before proceeding.")
        print("📚 Reference: CLAUDE.md, LINE_BY_LINE_STANDARDS.md, CODE_REVIEW_CRITERIA.md")
        
        return False

def main():
    """Main entry point for standards checker."""
    project_root = os.getcwd()
    checker = CodingStandardsChecker(project_root)
    
    success = checker.check_all_standards()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()