import os
import uuid
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from langgraph.types import Command

from pipeline import graph

# Initialize Flask (it automatically knows to use templates/ and static/ folders)
app = Flask(__name__)

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------------------------------------------------------
# Helper Function
# ---------------------------------------------------------
# ---------------------------------------------------------
# Helper Function
# ---------------------------------------------------------
def format_captions_for_frontend(captions_data):
    """
    Sends a list of dictionaries to the frontend so the JS can 
    put the platform name above the box, and the text inside it.
    """
    if isinstance(captions_data, dict):
        formatted = []
        for platform, text in captions_data.items():
            formatted.append({"platform": platform, "text": text})
        return formatted
    return captions_data if captions_data else []

# ---------------------------------------------------------
# Static File Serving (Frontend)
# ---------------------------------------------------------

@app.route('/')
def serve_frontend():
    # Flask automatically looks in the /templates folder for this
    return render_template('index.html')

# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

@app.route('/api/draft', methods=['POST'])
def draft_captions():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    description = request.form.get('description', '')

    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    try:
        filename = secure_filename(file.filename)
        file_extension = filename.split(".")[-1]
        temp_file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}.{file_extension}")
        file.save(temp_file_path)

        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        initial_input = {
            "image_path": temp_file_path,
            "user_description": description
        }

        # Run the graph until the human_review interrupt
        for event in graph.stream(initial_input, config, stream_mode="values"):
            pass 

        state = graph.get_state(config)
        raw_captions = state.values.get("captions", {})
        
        # Convert dict to list for JS compatibility
        formatted_captions = format_captions_for_frontend(raw_captions)

        if not formatted_captions:
            return jsonify({"error": "Failed to generate captions."}), 500

        return jsonify({
            "status": "success",
            "thread_id": thread_id,
            "captions": formatted_captions
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/review', methods=['POST'])
def review_captions():
    data = request.json
    thread_id = data.get('thread_id')
    feedback = data.get('feedback', '')
    selected_caption = data.get('selected_caption', '')

    if not thread_id:
        return jsonify({"error": "Missing thread_id"}), 400

    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)
    
    if not state.next:
        return jsonify({"error": "No active session found for this thread."}), 400

    try:
        user_intent = feedback.strip().lower()
        
        # Check if the user wants to retry, exit, or refine
        if user_intent not in ["retry", "exit"]:
            if not user_intent: 
                # NO FEEDBACK: Flag this so the pipeline knows to skip the LLM
                user_intent = f"APPROVE_EXACT: {selected_caption}"
            else:
                # FEEDBACK PROVIDED: Send the instructions to the LLM
                user_intent = f"I chose this caption: '{selected_caption}'. Instructions: {feedback}"

        # Resume the graph with the user's feedback
        for event in graph.stream(Command(resume=user_intent), config, stream_mode="values"):
            pass
            
        new_state = graph.get_state(config)
        
        # If the graph finished running
        if not new_state.next:
            final_text = new_state.values.get("final_output", "")
            return jsonify({
                "status": "completed",
                "final_caption": final_text
            })
        
        # If the user typed "retry", the graph loops back and pauses at human_review again
        elif new_state.next[0] == "human_review":
            raw_captions = new_state.values.get("captions", {})
            formatted_captions = format_captions_for_frontend(raw_captions)
            
            return jsonify({
                "status": "drafted",
                "captions": formatted_captions
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)