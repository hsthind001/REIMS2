#!/usr/bin/env python3
"""
Static Analysis Script to Detect Variable Scope Issues

This script analyzes Python files to detect potential variable scope issues
like the one that occurred with document_type not being passed through method calls.

Run this before commits to catch issues early:
    python scripts/check_method_signatures.py app/services/extraction_orchestrator.py

Exit codes:
    0 = No issues found
    1 = Potential issues detected
"""

import ast
import sys
from typing import List, Dict, Set, Tuple
from pathlib import Path


class MethodCallAnalyzer(ast.NodeVisitor):
    """Analyzes Python AST to find potential variable scope issues"""

    def __init__(self):
        self.methods: Dict[str, Dict] = {}  # method_name -> {params, calls}
        self.current_method: str = None
        self.issues: List[Dict] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track method definitions and their parameters"""
        if node.name.startswith('_') or node.name == '__init__':
            # Extract parameter names
            params = set()
            for arg in node.args.args:
                if arg.arg != 'self':
                    params.add(arg.arg)

            self.methods[node.name] = {
                'params': params,
                'calls': [],
                'lineno': node.lineno,
                'variables_used': set()
            }

            # Analyze method body
            prev_method = self.current_method
            self.current_method = node.name
            self.generic_visit(node)
            self.current_method = prev_method

    def visit_Call(self, node: ast.Call):
        """Track method calls and their arguments"""
        if self.current_method and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'self':
                method_name = node.func.attr

                # Extract argument names (for keyword args)
                kwargs = {}
                for keyword in node.keywords:
                    if isinstance(keyword.value, ast.Name):
                        kwargs[keyword.arg] = keyword.value.id

                self.methods[self.current_method]['calls'].append({
                    'method': method_name,
                    'kwargs': kwargs,
                    'lineno': node.lineno
                })

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        """Track variable usage in methods"""
        if self.current_method:
            self.methods[self.current_method]['variables_used'].add(node.id)
        self.generic_visit(node)

    def analyze_scope_issues(self):
        """Detect variables used but not defined in method scope"""
        for method_name, method_data in self.methods.items():
            params = method_data['params']
            variables_used = method_data['variables_used']

            # Check for common problematic variable names
            problematic = {'document_type', 'upload_id', 'property_id', 'period_id'}
            used_without_param = variables_used & problematic - params

            if used_without_param:
                self.issues.append({
                    'type': 'scope_issue',
                    'method': method_name,
                    'lineno': method_data['lineno'],
                    'variables': list(used_without_param),
                    'message': f"Method '{method_name}' uses {used_without_param} but doesn't have them as parameters"
                })

    def analyze_parameter_passing(self):
        """Check if methods properly pass parameters to called methods"""
        for caller_method, caller_data in self.methods.items():
            caller_params = caller_data['params']

            for call in caller_data['calls']:
                called_method = call['method']
                kwargs_passed = set(call['kwargs'].keys())

                if called_method in self.methods:
                    called_params = self.methods[called_method]['params']

                    # Check if important parameters are missing
                    important_params = {'document_type', 'upload_id', 'property_id'}
                    required = called_params & important_params

                    # Parameters that should be passed but aren't
                    missing = required - kwargs_passed

                    if missing and required:
                        # Check if caller has these params available
                        available_in_caller = missing & caller_params

                        if available_in_caller:
                            self.issues.append({
                                'type': 'missing_parameter',
                                'method': caller_method,
                                'calls': called_method,
                                'lineno': call['lineno'],
                                'missing': list(available_in_caller),
                                'message': f"Method '{caller_method}' calls '{called_method}' but doesn't pass {available_in_caller}"
                            })

    def print_report(self):
        """Print analysis report"""
        if not self.issues:
            print("✅ No potential scope issues detected!")
            return 0

        print(f"⚠️  Found {len(self.issues)} potential issue(s):\n")

        for i, issue in enumerate(self.issues, 1):
            print(f"{i}. {issue['type'].upper()} at line {issue['lineno']}")
            print(f"   {issue['message']}")
            if 'variables' in issue:
                print(f"   Variables: {', '.join(issue['variables'])}")
            if 'missing' in issue:
                print(f"   Missing parameters: {', '.join(issue['missing'])}")
            print()

        return 1


def analyze_file(file_path: Path) -> int:
    """Analyze a Python file for scope issues"""
    print(f"Analyzing {file_path}...\n")

    try:
        with open(file_path, 'r') as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        analyzer = MethodCallAnalyzer()
        analyzer.visit(tree)
        analyzer.analyze_scope_issues()
        analyzer.analyze_parameter_passing()

        return analyzer.print_report()

    except SyntaxError as e:
        print(f"❌ Syntax error in {file_path}: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error analyzing {file_path}: {e}")
        return 1


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python check_method_signatures.py <file_path>")
        print("Example: python check_method_signatures.py app/services/extraction_orchestrator.py")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        sys.exit(1)

    exit_code = analyze_file(file_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
