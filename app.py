from flask import (
    Flask,
    render_template,
    request,
    Response,
    stream_with_context,
    jsonify,
    session  # Import session - we might use it later for better state management
)
from dotenv import load_dotenv
import os
import logging

import google.generativeai as genai

from mot_data import MotData  # Assuming mot_data.py is in the same directory

load_dotenv()
genai.configure(api_key=os.getenv("gemini_api_key"))
model = genai.GenerativeModel('gemini-2.0-flash')
chat_session = model.start_chat(history=[])

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.urandom(24) # Consider stronger secret key for production
logging.basicConfig(level=logging.ERROR)

gemini_streaming_response = None # Global variable to store Gemini streaming response (WARNING: Not thread-safe for production)


@app.route("/", methods=["GET"])
def index():
    """Renders the main homepage for the app"""
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template("index.html", chat_history=session['chat_history'])


@app.route("/chat", methods=["POST"])
def chat():
    """
    Takes in registration, fetches MOT data, sends to Gemini for summary,
    and initiates streaming of Gemini's summary.
    """
    global gemini_streaming_response # Declare we are using the global variable
    gemini_streaming_response = None # Reset global variable at the start of each request

    registration = request.json.get("registration")
    if not registration:
        return jsonify(success=False, error="Registration number is required"), 400

    try:
        mot_data_instance = MotData(registration)
        mot_summary = mot_data_instance.generate_mot_summary()

        if "No MoT test data available" in mot_summary:
            return jsonify(success=False, error=mot_summary), 400 # Return error if no MOT data

        # Prepare prompt for Gemini - summarize the MOT summary
        prompt = f"Summarize the following vehicle MOT history:\n\n{mot_summary}"

        # Start streaming response from Gemini
        gemini_streaming_response = chat_session.send_message(prompt, stream=True)

        return jsonify(success=True) # Just confirm success for now, streaming happens in /stream

    except Exception as e:
        logging.error(f"Error processing MOT data or Gemini API: {e}")
        return jsonify(success=False, error="Error processing your request. Please try again."), 500


@app.route("/stream", methods=["GET"])
def stream():
    """
    Streams the Gemini-generated summary of the MOT data to the client.
    """
    def generate():
        global gemini_streaming_response # Access the global streaming response

        if gemini_streaming_response is None:
            yield "data: Error: No Gemini summary available. Please submit a registration first.\n\n"
            return

        assistant_response_content = ""
        try:
            for chunk in gemini_streaming_response:
                assistant_response_content += chunk.text
                yield f"data: {chunk.text}\n\n"
        except Exception as e: # Catch potential streaming errors
            logging.error(f"Error during Gemini summary streaming: {e}")
            yield "data: Error: Problem streaming summary from model. Please try again.\n\n"
        finally:
            gemini_streaming_response = None # Reset global variable after streaming is done

        # Removed: yield "data: \n\n" # Removed - likely not needed for SSE stream end


    return Response(stream_with_context(generate()), mimetype="text/event-stream")


if __name__ == '__main__':
    app.run(debug=True)