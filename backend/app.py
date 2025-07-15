from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
from main import GmailAssistant
from voice_handler import VoiceHandler
from conversation_ai import ConversationAI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Gmail Assistant with Voice Calling")
voice_handler = VoiceHandler()

@app.get("/")
def read_root():
    return {"message": "Gmail Assistant with Voice Calling API"}

@app.get('/read-emails')
def read_emails():
    """REST endpoint to read emails"""
    try:
        gmail_assistant = GmailAssistant()
        results = gmail_assistant.analyze_inbox(max_emails=5)
        return {"message": "Emails read successfully", "emails": results}
    except Exception as e:
        return {"error": f"Failed to read emails: {str(e)}"}

# Voice calling endpoints
@app.post("/make-call")
def make_call(phone_number: str):
    """Initiate an outbound call"""
    try:
        call_sid = voice_handler.initiate_call(phone_number)
        return {"message": "Call initiated successfully", "call_sid": call_sid}
    except Exception as e:
        return {"error": f"Failed to initiate call: {str(e)}"}

@app.post("/voice/greeting")
def voice_greeting(request: Request):
    """Handle the initial voice greeting"""
    twiml_response = voice_handler.handle_greeting(request)
    return Response(content=twiml_response, media_type="application/xml")

@app.post("/voice/process_input")
def voice_process_input(request: Request):
    """Process user voice input"""
    twiml_response = voice_handler.process_user_input(request)
    return Response(content=twiml_response, media_type="application/xml")

@app.post("/voice/read_email")
def voice_read_email(request: Request):
    """Read current email to user"""
    twiml_response = voice_handler.read_current_email(request)
    return Response(content=twiml_response, media_type="application/xml")

@app.post("/voice/status")
def voice_call_status(request: Request):
    """Handle call status updates"""
    result = voice_handler.handle_call_status(request)
    return Response(content=result, media_type="text/plain")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "gmail-assistant-voice"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




