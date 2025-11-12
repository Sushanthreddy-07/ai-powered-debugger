import ast
import subprocess
import tempfile
import os


def analyze_with_ast(code: str):
   
    try:
        tree = ast.parse(code)
        node_types = [type(node).__name__ for node in ast.walk(tree)]
        summary = {}
        for node in node_types:
            summary[node] = summary.get(node, 0) + 1
        return summary
    except SyntaxError as e:
        return {"error": f"SyntaxError: {str(e)}"}


def analyze_with_pylint(code: str):
  
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        result = subprocess.run(
            ["pylint", temp_file_path, "--disable=all", "--enable=E,W,C,R"],
            capture_output=True,
            text=True
        )
        output = result.stdout
        messages = [line for line in output.splitlines() if ":" in line]
        return messages
    except Exception as e:
        return [f"Pylint error: {str(e)}"]
    finally:
        os.unlink(temp_file_path)
