import base64
import os
import re
import json
from typing import TypedDict, Literal
from pathlib import Path

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt

# =========================
# Load Environment Variables
# =========================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env")

# =========================
# State Definition
# =========================
class State(TypedDict):
    image_path: str
    user_description: str
    captions: dict
    feedback: str
    final_output: str

# =========================
# Models
# =========================
# FIXED: Using the correct Groq vision model
model = ChatGroq(
    model_name="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0.7,
    max_tokens=1024
)

text_model = ChatGroq(
    model_name="llama-3.1-8b-instant",
    temperature=0.7
)

# =========================
# Helpers: Load Prompts
# =========================
def load_system_prompt(user_description: str) -> str:
    prompt_path = Path("prompts/system_prompt.md")
    if not prompt_path.exists():
        return f"Describe this image. User context: {user_description}"
        
    template = prompt_path.read_text()
    return template.replace("{user_description}", user_description)

def load_refiner_prompt(captions: dict, feedback: str) -> str:
    prompt_path = Path("prompts/refiner_prompt.md")
    
    # Fallback in case the file doesn't exist yet
    if not prompt_path.exists():
        template = "Refine these based on feedback: {feedback}\n\n{linkedin_caption}\n{instagram_caption}\n{whatsapp_caption}"
    else:
        template = prompt_path.read_text()

    # FIXED: Using LangChain's PromptTemplate safely handles any markdown curly braces {}
    prompt_template = PromptTemplate.from_template(template)
    
    return prompt_template.format(
        linkedin_caption=captions.get("LinkedIn", "N/A"),
        instagram_caption=captions.get("Instagram", "N/A"),
        whatsapp_caption=captions.get("WhatsApp", "N/A"),
        feedback=feedback
    )

def load_json_instructions() -> str:
    prompt_path = Path("prompts/json_instructions.md")
    if not prompt_path.exists():
        return '{"option_1": "caption 1", "option_2": "caption 2", "option_3": "caption 3"}'
    return "\n\n" + prompt_path.read_text()

# =========================
# Nodes
# =========================
def drafter_node(state: State):
    print("\n--- STEP 1: DRAFTING ---")

    with open(state["image_path"], "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")

    base_prompt = load_system_prompt(state.get("user_description", ""))
    json_instructions = load_json_instructions()

    msg = HumanMessage(content=[
        {"type": "text", "text": base_prompt + json_instructions},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{img_base64}"
            }
        }
    ])

    response = model.invoke([msg])
    
    try:
        raw_text = response.content.replace("```json", "").replace("```", "").strip()
        parsed_captions = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"Warning: Vision model failed to return strict JSON. Raw output: {response.content}")
        parsed_captions = {
            "option_1": "Failed to parse caption.", 
            "option_2": "Failed to parse caption.", 
            "option_3": "Failed to parse caption."
        }

    return {"captions": parsed_captions}

def human_review_node(state: State):
    print("\n--- STEP 2: HUMAN REVIEW ---")

    review_request = {
        "task": "Review Captions",
        "context": state.get("user_description"),
        "options": state.get("captions"),
        "instructions": (
            "Type platform name (LinkedIn / Instagram / WhatsApp) "
            "with feedback (e.g., 'Instagram: add more emojis'). "
            "Type 'retry' to regenerate. "
            "Type 'exit' to quit."
        )
    }

    user_feedback = interrupt(review_request)

    return {"feedback": user_feedback}



def refiner_node(state: State):
    print("\n--- STEP 3: REFINING ---")
    
    feedback_str = state.get("feedback", "")
    
    # BYPASS THE LLM: If the user provided no feedback, just output the exact selection
    if feedback_str.startswith("APPROVE_EXACT: "):
        print("-> No feedback provided. Bypassing LLM and approving exact text.")
        clean_output = feedback_str.replace("APPROVE_EXACT: ", "", 1).strip()
        return {"final_output": clean_output}

    # RUN THE LLM: If feedback was provided, proceed normally
    refine_prompt = load_refiner_prompt(
        captions=state["captions"],
        feedback=feedback_str
    )

    refined_response = text_model.invoke(
        [HumanMessage(content=refine_prompt)]
    )
    
    raw_output = refined_response.content.strip()
    
    # Forcefully strip out any "Platform:" or "Label:" at the start of the text
    clean_output = re.sub(r'^([A-Za-z0-9 ]+):\s*\n*', '', raw_output, flags=re.IGNORECASE)
    
    # Remove accidental wrapping quotes if the LLM added them
    if clean_output.startswith('"') and clean_output.endswith('"'):
        clean_output = clean_output[1:-1].strip()

    return {"final_output": clean_output}


# =========================
# Router
# =========================
def route_feedback(state: State) -> Literal["drafter", "refiner", "__end__"]:
    feedback = state.get("feedback", "").strip().lower()

    if feedback == "retry":
        print("-> Routing back to drafter...")
        return "drafter"
    elif feedback == "exit":
        print("-> Exiting pipeline...")
        return "__end__"
    else:
        print("-> Routing to refiner...")
        return "refiner"


# =========================
# Graph Compilation
# =========================
builder = StateGraph(State)

builder.add_node("drafter", drafter_node)
builder.add_node("human_review", human_review_node)
builder.add_node("refiner", refiner_node)

builder.add_edge(START, "drafter")
builder.add_edge("drafter", "human_review")
builder.add_conditional_edges("human_review", route_feedback)
builder.add_edge("refiner", END)

memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)