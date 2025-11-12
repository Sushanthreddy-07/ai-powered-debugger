from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from helper_functions import (
    generate_code,
    fix_code,
    execute_code,
    prepare_code_for_execution,
    determine_execution_success
)

from analyzer import analyze_with_ast, analyze_with_pylint

app = FastAPI(title="AIbugfixer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PromptRequest(BaseModel):
    prompt: str

class FixRequest(BaseModel):
    code: str
    error_message: str

class ExecuteRequest(BaseModel):
    code: str
    user_inputs: dict = {}

@app.post("/generate")
def generate_code_endpoint(req: PromptRequest):
    code = generate_code(req.prompt)
    return {"code": code}

@app.post("/fix")
def fix_code_endpoint(req: FixRequest):
    fixed = fix_code(req.code, req.error_message)
    return {"fixed_code": fixed}

@app.post("/analyze")
def analyze_code_endpoint(req: PromptRequest):
    ast = analyze_with_ast(req.prompt)
    pylint = analyze_with_pylint(req.prompt)
    return {"ast_summary": ast, "pylint_report": pylint}

@app.post("/execute")
def execute_code_endpoint(req: ExecuteRequest):
    code_ready = prepare_code_for_execution(req.code, req.user_inputs)
    success, output = execute_code(code_ready)
    status, msg = determine_execution_success(output, req.user_inputs)
    return {
        "status": status,
        "output": msg,
        "success": success,
        "prepared_code": code_ready
    }
