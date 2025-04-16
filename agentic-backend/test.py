import re
import langchain
from typing import Annotated, List
from typing_extensions import Literal, TypedDict
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import json
import markdown
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from typing import Optional
from langchain_ollama.chat_models import ChatOllama
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
import operator
from langgraph.graph import StateGraph, START, END
from pprint import pprint
#llm = ChatOllama(model="llama3.2:latest")

from prompts.load_prompts import mainPrompt, jsonPrompt, gitignorePrompt, envPrompt, eslintPrompt, vitestPrompt, prettierPrompt, extractPrompt, dockerPrompt
extractPrompt = extractPrompt()
mainPrompt = mainPrompt()
jsonPrompt = jsonPrompt()
gitignorePrompt = gitignorePrompt()
envPrompt = envPrompt()
prettierPrompt = prettierPrompt()
eslintPrompt = eslintPrompt()
vitestPrompt = vitestPrompt()
dockerPrompt = dockerPrompt()
print(mainPrompt)

# Prompts for loading the files, will be automated lateron
with open("files/package.json", "r") as file:
    packageFile = file.read()
with open("files/.gitignore", "r") as file:
    gitIgnoreFile = file.read()
with open("files/.env", "r") as file:
    envFile = file.read()
with open("files/.prettierignore", "r") as file:
    prettierIgnoreFile = file.read()
with open("files/.prettierrc", "r") as file:
    prettierrcFile = file.read()
with open("files/eslint.config.js", "r") as file:
    eslintFile = file.read()
with open("files/Dockerfile", "r") as file:
    dockerFile = file.read()


print(packageFile)
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key=groq_api_key
    )

# Main State of graph
class mainState(BaseModel):
    dependencies: List[str]
    installCommands : List[str]
    gitignoreSuggestions : str
    envSuggestions : str
    prettierSuggestions : str
    vitestSuggestions : str
    eslintSuggestions : str
    dockerSuggestions: str

# Defining schemans for getting structured output from llm
class installSchema(BaseModel):
    commands : List[str]
class extractPackagesSchema(BaseModel):
    dependencies: List[str]

# Nodes
def extractDepNode(state: mainState):
    file = packageFile
    prompt = ChatPromptTemplate([
        ("system", extractPrompt),
        ("user", "this is the main package.json file {file}")

    ])
    structured_llm = llm.with_structured_output(extractPackagesSchema)
    chain = prompt | structured_llm

    response = chain.invoke({"file": file})
    return {"dependencies": response.dependencies}

def packageNode(state: mainState):
    file = packageFile
    prompt = ChatPromptTemplate([
        ("system", mainPrompt),
        ("system", jsonPrompt),
        ("user", "this is the main package.json file {file}")

    ])
    structured_llm = llm.with_structured_output(installSchema)
    chain = prompt | structured_llm

    response = chain.invoke({'file': file})
    return {"installCommands": response.commands}

def gitIgnoreNode(state: mainState):
    file =  gitIgnoreFile
    prompt = ChatPromptTemplate([
        ("system", mainPrompt),
        ("user", "this is the list of dependencies {depState}"),
        ("system", gitignorePrompt),
        ("user", "this is the gitignore file {file}")
    ])
    chain = prompt | llm

    response = chain.invoke({"depState": state.dependencies, 'file': file})

    return {"gitignoreSuggestions": response.content}

def envNode(state: mainState):
    file =  envFile
    prompt = ChatPromptTemplate([
        ("system", mainPrompt),
        ("user", "this is the list of dependencies {depState}"),
        ("system", envPrompt),
        ("user", "this is the env file {file}")
    ])
    chain = prompt | llm

    response = chain.invoke({"depState": state.dependencies, 'file': file})
    return {"envSuggestions": response.content}

def dockerNode(state: mainState):
    file =  dockerFile
    prompt = ChatPromptTemplate([
        ("system", mainPrompt),
        ("user", "this is the list of dependencies {depState}"),
        ("system", dockerPrompt),
        ("user", "this is the env file {file}")
    ])
    chain = prompt | llm

    response = chain.invoke({"depState": state.dependencies, 'file': file})
    return {"dockerSuggestions": response.content}

def prettierrcNode(state: mainState):
    file =  prettierrcFile
    file1 = prettierIgnoreFile
    prompt = ChatPromptTemplate([
        ("system", mainPrompt),
        ("user", "this is the list of dependencies {depState}"),
        ("system", prettierPrompt),
        ("user", "this is the prettierrc file {file} and this is prettierIgnore file {file1}")
    ])
    chain = prompt | llm

    response = chain.invoke({"depState": state.dependencies, 'file': file, 'file1':file1})
    return {"prettierSuggestions": response.content}

def eslintNode(state: mainState):
    return

def generateHTML(final_state):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are expert in generating html from markdown files, and you don't miss any of the details"),
        ("user", "Generate HTML for a project setup using this data: {final_state}"),
        ("user", "Just return in html format only, don't return markdown")
    ])

    chain = prompt | llm

    response = chain.invoke({"final_state": str(final_state)})

    return response.content

app = StateGraph(mainState)

app.add_node(extractDepNode, "extractDepNode")
app.add_node(packageNode, "packageNode")
app.add_node(gitIgnoreNode, "gitIgnoreNode")
app.add_node(envNode, "envNode")
app.add_node(prettierrcNode, "prettierrcNode")
app.add_node(dockerNode, "dockerNode")

app.add_edge(START, "extractDepNode")
app.add_edge("extractDepNode", "packageNode")
app.add_edge("packageNode", "gitIgnoreNode")
app.add_edge("gitIgnoreNode", "envNode")
app.add_edge("envNode", "prettierrcNode")
app.add_edge("prettierrcNode", "dockerNode")
app.add_edge("dockerNode", END)
graph = app.compile()

def run_langgraph():
    initial_state = mainState(
        dependencies=[],
        installCommands=[],
        gitignoreSuggestions="",
        envSuggestions="",
        prettierSuggestions="",
        vitestSuggestions="",
        eslintSuggestions="",
        dockerSuggestions= ""
    )
    final_state = graph.invoke(initial_state)
    html_content = generateHTML(final_state)
    return html_content
## Useful for debugging (streaming)
# for event in graph.stream(initial_state, stream_mode="values"):
#     print("Dependencies:", event["dependencies"])
#     print("Install Commands:", event["installCommands"])
#     print("Gitignore Suggestions:", event["gitignoreSuggestions"])
#     print("Env Suggestions:", event["envSuggestions"])
#     print("Prettier Suggestions:", event["prettierSuggestions"])
#     print("Vitest Suggestions:", event["vitestSuggestions"])
#     print("Eslint Suggestions:", event["eslintSuggestions"])
#     print("-" * 50)
