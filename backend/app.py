from fastapi import FastAPI, Form, Request
from fastapi.responses import Response
from main import GmailAssistant
from voice_handler import VoiceHandler
from conversation_ai import ConversationAI
import os
import logging
from dotenv import load_dotenv

load_dotenv('.env.local')

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gmail Assistant with Voice Calling")

# Initialize voice_handler with error handling
try:
    voice_handler = VoiceHandler()
    logger.info("✅ VoiceHandler initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize VoiceHandler: {e}")
    voice_handler = None

@app.get("/")
def read_root():
    return {"message": "Gmail Assistant with Voice Calling API"}

@app.get('/read-emails')
def read_emails():
    """REST endpoint to read emails"""
    try:
        logger.info("📧 Received read emails request")
        gmail_assistant = GmailAssistant()
        results = gmail_assistant.analyze_inbox(max_emails=5)
        logger.info("✅ Emails read successfully")
        return {"message": "Emails read successfully", "emails": results}
    except Exception as e:
        logger.error(f"❌ Error reading emails: {e}")
        logger.exception("Full exception details:")
        return {"error": f"Failed to read emails: {str(e)}"}

# Voice calling endpoints
@app.post("/make-call")
def make_call(phone_number: str, test_mode: bool = False):
    """Initiate an outbound call"""
    try:
        logger.info(f"📞 Initiating call to {phone_number}, test_mode={test_mode}")
        if not voice_handler:
            logger.error("❌ VoiceHandler not initialized")
            return {"error": "Voice handler not available"}
        
        call_sid = voice_handler.initiate_call(phone_number, test_mode=test_mode)
        logger.info(f"✅ Call initiated successfully with SID: {call_sid}")
        return {"message": "Call initiated successfully", "call_sid": call_sid}
    except Exception as e:
        logger.error(f"❌ Error in make_call: {e}")
        logger.exception("Full exception details:")
        return {"error": f"Failed to initiate call: {str(e)}"}

@app.post("/voice/greeting")
async def voice_greeting(request: Request):
    """Handle the initial voice greeting"""
    try:
        logger.info("🎤 Received voice greeting request")
        if not voice_handler:
            logger.error("❌ VoiceHandler not initialized")
            return Response(content="<Response><Say>Sorry, service unavailable</Say></Response>", media_type="application/xml")
        
        twiml_response = await voice_handler.handle_greeting(request)
        logger.info("✅ Generated TwiML response successfully")
        response = Response(content=twiml_response, media_type="application/xml")
        # Add headers to help with ngrok
        response.headers["ngrok-skip-browser-warning"] = "true"
        response.headers["Cache-Control"] = "no-cache"
        return response
    except Exception as e:
        logger.error(f"❌ Error in voice_greeting: {e}")
        logger.exception("Full exception details:")
        return Response(content="<Response><Say>Sorry, an error occurred</Say></Response>", media_type="application/xml")

@app.post("/voice/process_input")
async def voice_process_input(request: Request):
    """Process user voice input"""
    try:
        logger.info("🎤 Received voice input processing request")
        if not voice_handler:
            logger.error("❌ VoiceHandler not initialized")
            return Response(content="<Response><Say>Sorry, service unavailable</Say></Response>", media_type="application/xml")
        
        twiml_response = await voice_handler.process_user_input(request)
        logger.info("✅ Processed user input successfully")
        response = Response(content=twiml_response, media_type="application/xml")
        # Add headers to help with ngrok
        response.headers["ngrok-skip-browser-warning"] = "true"
        response.headers["Cache-Control"] = "no-cache"
        return response
    except Exception as e:
        logger.error(f"❌ Error in voice_process_input: {e}")
        logger.exception("Full exception details:")
        return Response(content="<Response><Say>Sorry, an error occurred</Say></Response>", media_type="application/xml")

@app.post("/voice/read_email")
async def voice_read_email(request: Request):
    """Read current email to user"""
    try:
        logger.info("📧 Received read email request")
        if not voice_handler:
            logger.error("❌ VoiceHandler not initialized")
            return Response(content="<Response><Say>Sorry, service unavailable</Say></Response>", media_type="application/xml")
        
        twiml_response = await voice_handler.read_current_email(request)
        logger.info("✅ Generated email reading response successfully")
        response = Response(content=twiml_response, media_type="application/xml")
        # Add headers to help with ngrok
        response.headers["ngrok-skip-browser-warning"] = "true"
        response.headers["Cache-Control"] = "no-cache"
        return response
    except Exception as e:
        logger.error(f"❌ Error in voice_read_email: {e}")
        logger.exception("Full exception details:")
        return Response(content="<Response><Say>Sorry, an error occurred reading emails</Say></Response>", media_type="application/xml")

@app.post("/voice/status")
async def voice_call_status(request: Request):
    """Handle call status updates"""
    try:
        logger.info("📊 Received call status update")
        if not voice_handler:
            logger.error("❌ VoiceHandler not initialized")
            return Response(content="OK", media_type="text/plain")
        
        result = await voice_handler.handle_call_status(request)
        logger.info("✅ Processed call status successfully")
        response = Response(content=result, media_type="text/plain")
        # Add headers to help with ngrok
        response.headers["ngrok-skip-browser-warning"] = "true"
        response.headers["Cache-Control"] = "no-cache"
        return response
    except Exception as e:
        logger.error(f"❌ Error in voice_call_status: {e}")
        logger.exception("Full exception details:")
        return Response(content="OK", media_type="text/plain")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "gmail-assistant-voice"}

@app.get("/debug")
def debug_status():
    """Debug endpoint to check component status"""
    try:
        status = {
            "voice_handler": "initialized" if voice_handler else "not_initialized",
            "environment_variables": {
                "TWILIO_ACCOUNT_SID": "set" if os.getenv("TWILIO_ACCOUNT_SID") else "missing",
                "TWILIO_AUTH_TOKEN": "set" if os.getenv("TWILIO_AUTH_TOKEN") else "missing",
                "TWILIO_NUMBER": "set" if os.getenv("TWILIO_NUMBER") else "missing",
                "OPENAI_API_KEY": "set" if os.getenv("OPENAI_API_KEY") else "missing",
                "GOOGLE_PROJECT_ID": "set" if os.getenv("GOOGLE_PROJECT_ID") else "missing",
                "BASE_URL": os.getenv("BASE_URL", "not_set"),
            }
        }
        
        # Test GmailAssistant initialization
        try:
            gmail_assistant = GmailAssistant()
            status["gmail_assistant"] = "initialized"
        except Exception as e:
            status["gmail_assistant"] = f"failed: {str(e)}"
        
        # Test ConversationAI initialization
        try:
            conversation_ai = ConversationAI(user_id="test")
            status["conversation_ai"] = "initialized"
        except Exception as e:
            status["conversation_ai"] = f"failed: {str(e)}"
        
        return status
    except Exception as e:
        logger.error(f"❌ Error in debug endpoint: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




