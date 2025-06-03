from flask import Flask, jsonify
from api.twilio_routes import twilio_bp
from api.message_processor import process_queued_messages
import threading
import os
import logging
import traceback

app = Flask(__name__)
app.register_blueprint(twilio_bp, url_prefix='/twilio')

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error("Unhandled Exception: %s\n%s", str(e), traceback.format_exc())
    response = {
        "error": "An unexpected error occurred.",
        "details": str(e)
    }
    return jsonify(response), 500

def start_message_processor():
    """Start the message processor in a separate thread"""
    processor_thread = threading.Thread(target=process_queued_messages, daemon=True)
    processor_thread.start()

if __name__ == '__main__':
    start_message_processor()
    port = int(os.getenv('PORT', 5000))
    
    # In production, use gunicorn instead of app.run()
    if os.getenv('ENVIRONMENT') == 'production':
        # Railway will use gunicorn
        pass
    else:
        # Dev server
        app.run(host='0.0.0.0', port=port, debug=True) 