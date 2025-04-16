from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from typing import List
import os
from test import run_langgraph
from generate_html import generate_html_content

app = FastAPI()

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    # ensure directories exist, coz it throws error everytime it runs
    if not os.path.exists("files"):
        os.makedirs("files")
    if not os.path.exists("static"):
        os.makedirs("static")

    for file in files:
        filename = os.path.basename(file.filename)
        with open(f"files/{filename}", "wb") as buffer:
            buffer.write(await file.read())

    html_content = run_langgraph()
    #html_content = generate_html_content(final_state)
    with open("static/report.html", "w") as f:
        f.write(html_content)

    return {"message": "Report generated, please visit /read-report to see it"}

@app.get("/read-report", response_class=HTMLResponse)
async def get_report():
    try:
        with open("static/report.html", "r") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Report not found</h1>", status_code=404)
