import os
import re
import sys
import subprocess
import streamlit as st
import prompt_templates as pt
from dotenv import load_dotenv
from openai import OpenAI
from analyzer import analyze_with_ast, analyze_with_pylint

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_code(prompt):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": pt.main_system_prompt()},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        top_p=1,
        stream=False
    )
    final_output = response.choices[0].message.content
    lines = final_output.split('\n')
    cleaned_lines = [line.rstrip() for line in lines if not line.strip().startswith('```') and not line.strip().endswith('```')]
    return '\n'.join(cleaned_lines)

def extract_function_parameters(code):
    function_definitions = re.findall(r'def\s+\w+\((.*?)\):', code)
    parameters = []
    for definition in function_definitions:
        params = definition.split(',')
        for param in params:
            param_name = param.split('=')[0].strip()
            if param_name:
                parameters.append(param_name)
    return list(set(parameters))

def prepare_code_for_execution(code, user_inputs):
    for var, value in user_inputs.items():
        escaped_var = re.escape(var)
        pattern = rf'{escaped_var}\s*=\s*[^\n]*'
        normalized_value = value.replace('\\', '\\\\')
        replacement = f'{var} = r"{normalized_value}"'
        code = re.sub(pattern, replacement, code)
    return code

def execute_code(code, timeout=3000):
    try:
        result = subprocess.run([f"{sys.executable}", '-c', code], capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            if "ModuleNotFoundError" in result.stderr:
                missing_modules = extract_missing_modules(result.stderr)
                for module in missing_modules:
                    install_module(module)
                result = subprocess.run([f"{sys.executable}", '-c', code], capture_output=True, text=True, timeout=timeout)
                if result.returncode != 0:
                    return False, result.stderr
            else:
                return False, result.stderr
        return True, result.stdout
    except subprocess.TimeoutExpired:
        return False, "Code execution timed out"
    except Exception as e:
        return False, str(e)

def extract_missing_modules(error_message):
    with st.spinner("Analyzing error message for missing modules..."):
        missing_modules = re.findall(r"ModuleNotFoundError: No module named '(\\w+)'", error_message)
    if missing_modules:
        st.info(f"Detected missing modules: {', '.join(missing_modules)}")
    else:
        st.info("No missing modules detected.")
    return missing_modules

def install_module(module_name):
    with st.spinner(f"Installing module: {module_name}..."):
        pip_command = [sys.executable, '-m', 'pip', 'install', module_name]
        result = subprocess.run(pip_command, capture_output=True, text=True)
        if result.returncode == 0:
            st.success(f"Successfully installed {module_name}")
        else:
            st.error(f"Failed to install {module_name}. Error: {result.stderr}")
    return result.returncode == 0

def handle_missing_modules(error_message):
    missing_modules = extract_missing_modules(error_message)
    if missing_modules:
        st.warning("Attempting to install missing modules...")
        for module in missing_modules:
            install_module(module)
    else:
        st.info("No missing modules to install.")
    return missing_modules

def fix_code(code, error_message):
    ast_summary = analyze_with_ast(code)
    pylint_issues = analyze_with_pylint(code)
    pylint_text = "\n".join(pylint_issues) if pylint_issues else "No issues reported by Pylint."

    prompt = f"""You are an AI programming assistant.

The following Python code has issues:

### Original Code:
{code}

### Runtime Error:
{error_message}

### AST Summary (code structure):
{ast_summary}

### Pylint Warnings/Errors:
{pylint_text}

Please fix the code so that it runs correctly. Only return valid Python code, no explanation. Wrap the code in triple backticks (```).
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": pt.main_system_prompt()},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        top_p=1,
        stream=False
    )

    fixed_code = response.choices[0].message.content
    lines = fixed_code.split('\n')
    cleaned_lines = [line.rstrip() for line in lines if not line.strip().startswith('```') and not line.strip().endswith('```')]
    return '\n'.join(cleaned_lines)

def render_input_fields(parameters):
    user_inputs = {}
    for parameter in parameters:
        user_inputs[parameter] = st.text_input(f"Value for `{parameter}`:", "")
    return user_inputs

def determine_execution_success(output, user_inputs):
    if any(value.strip() == "" for value in user_inputs.values()):
        return "Error", "Empty user input detected."
    if not output.strip():
        return "Error", "No output was produced by the code execution."
    error_indicators = [
        "error", "exception", "traceback", "failed", "syntax error",
        "attribute error", "type error", "name error", "value error",
        "index error", "key error", "zero division error",
        "does not exist", "cannot find", "is not defined", "permission denied", "code execution timed out"
    ]
    for indicator in error_indicators:
        if indicator in output.lower():
            return "Error", f"Error detected: {output}"
    return "Success", output

def handle_execution_errors(error_message):
    if "SyntaxError" in error_message:
        return "Syntax Error detected. Please review the generated code for potential issues."
    elif "TypeError" in error_message:
        return ("Type Error detected. Ensure that the function is being called with the correct argument types.\n"
                "Example: Passing an integer where a string is expected could cause this issue.")
    elif "NameError" in error_message:
        return "Name Error: A variable or function is not defined. Please ensure that all names used in the code are properly defined."
    elif "ModuleNotFoundError" in error_message:
        return "Module Not Found: The code is trying to use a Python module that is not installed."
    elif "IndexError" in error_message:
        return ("Index Error: The code is trying to access an index that doesn't exist. This often happens when working with lists or arrays.")
    elif "KeyError" in error_message:
        return ("Key Error: The code is trying to access a dictionary key that doesn't exist. Make sure you're accessing valid keys.")
    else:
        return "An unknown error occurred. Please check the code and inputs."

# This file is part of the AIbugfixer project.