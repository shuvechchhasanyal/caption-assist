# Executive Post Assistant 🚀

A full-stack AI application designed to help people generate, review, and refine high-quality social media captions in seconds. 

Built with **LangGraph** for a "Human-in-the-Loop" workflow and powered by **Groq's** blazing-fast Llama 3 vision and text models, this tool turns a single image and a brief context into polished, ready-to-publish copy.

## ✨ Features

* **AI Vision Integration:** Upload an image and provide optional context; the AI analyzes both to draft highly relevant captions.
* **Human-in-the-Loop Pipeline:** Built with LangGraph, the app pauses after drafting to allow the user to select their favorite option and provide specific revision instructions.
* **Iterative Refinement:** A secondary LLM agent applies your feedback to polish the chosen draft perfectly.
* **Premium User Interface:** Features a modern, responsive "Aurora Glassmorphism" dark theme with drag-and-drop file support.
* **Frictionless Workflow:** 1-click "Copy to Clipboard" functionality explicitly designed for executives and busy professionals.

## 🛠️ Tech Stack

* **Backend:** Python, Flask
* **AI & Orchestration:** LangChain, LangGraph
* **LLMs:** * `llama-3.2-11b-vision-preview` (Drafting & Vision Analysis via Groq)
  * `llama-3.1-8b-instant` (Feedback & Refinement via Groq)
* **Frontend:** Vanilla HTML5, CSS3, JavaScript (Fetch API)

## 📁 Project Structure

```text
AGENTS/
├── .env.example             # Template for required environment variables
├── .gitignore               # Files ignored by Git
├── README.md                # Project documentation
├── app.py                   # Main Flask server
├── pipeline.py              # LangGraph AI pipeline logic
├── requirements.txt         # Python dependencies
├── prompts/                 # LLM Instruction Files
│   ├── json_instructions.md
│   ├── refiner_prompt.md
│   └── system_prompt.md
├── static/                  # Frontend Assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── script.js
└── templates/               # HTML Templates
    └── index.html