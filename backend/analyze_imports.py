import ast
import os
import sys

def get_imports(directory):
    imports = set()
    for root, dirs, files in os.walk(directory):
        # Exclude .venv and __pycache__
        dirs[:] = [d for d in dirs if d not in ['.venv', '__pycache__', 'node_modules', '.git']]
        
        for file in files:
            if file.endswith(".py") and file != "analyze_imports.py":
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=path)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    imports.add(alias.name.split('.')[0])
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    imports.add(node.module.split('.')[0])
                except Exception as e:
                    # Ignore errors for now
                    pass
    return imports

if __name__ == "__main__":
    directory = os.path.dirname(os.path.abspath(__file__))
    used_imports = get_imports(directory)
    print("Used imports:")
    for imp in sorted(used_imports):
        print(imp)
