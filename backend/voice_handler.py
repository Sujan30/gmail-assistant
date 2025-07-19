from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
from fastapi import Request
from conversation_ai import ConversationAI
import os
from dotenv import load_dotenv
from typing import Dict, Any
import logging

load_dotenv('.env.local')

class VoiceHandler:
    """Handles Twilio voice interactions and TwiML responses"""
    
    def __init__(self):
        self.twilio_client = Client(
            os.environ["TWILIO_ACCOUNT_SID"],
            os.environ["TWILIO_AUTH_TOKEN"]
        )
        self.conversation_sessions = {}  # Store conversation states per call
        
    def initiate_call(self, to_number: str, test_mode: bool = False) -> str:
        """Initiate an outbound call"""
        try:
            if test_mode:
                # For testing: use a simple TwiML that just says hello
                twiml_url = "http://demo.twilio.com/docs/voice.xml"
            else:
                base_url = os.environ.get('BASE_URL', 'http://localhost:8000')
                # Add ngrok-skip-browser-warning parameter for free ngrok accounts
                if 'ngrok' in base_url:
                    twiml_url = f"{base_url}/voice/greeting?ngrok-skip-browser-warning=true"
                else:
                    twiml_url = f"{base_url}/voice/greeting"
            
            call = self.twilio_client.calls.create(
                from_=os.environ["TWILIO_NUMBER"],
                to=to_number,
                url=twiml_url,
                method="POST"
            )
            
            return call.sid
        except Exception as e:
            logging.error(f"Error initiating call: {e}")
            raise
    
    async def handle_greeting(self, request: Request) -> str:
        """Handle initial call greeting"""
        response = VoiceResponse()
        
        # Get or create conversation session
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        caller_number = form_data.get('From')
        
        if call_sid not in self.conversation_sessions:
            # Note: ConversationAI is now an async context manager, but we'll manage it manually
            # in the voice handler since we need to persist sessions across requests
            self.conversation_sessions[call_sid] = ConversationAI(user_id=caller_number)
        
        # Welcome message
        response.say(
            "Hello! I'm your personal email assistant. How can I help you today? "
            "You can ask me to read your emails, check your calendar, or manage tasks.",
            voice='alice',
            language='en-US'
        )
        
        # Gather user input
        gather = Gather(
            input='speech',
            action='/voice/process_input',
            method='POST',
            speech_timeout='auto',
            language='en-US'
        )
        response.append(gather)
        
        # Fallback if no input
        response.say("I didn't hear anything. Please let me know how I can help you.", voice='alice')
        response.redirect('/voice/greeting')
        
        return str(response)
    
    async def process_user_input(self, request: Request) -> str:
        """Process user speech input and generate appropriate response"""
        response = VoiceResponse()
        
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        speech_result = form_data.get('SpeechResult', '')
        
        if call_sid not in self.conversation_sessions:
            # Session lost, restart
            response.say("I'm sorry, I lost our conversation. Let me restart.", voice='alice')
            response.redirect('/voice/greeting')
            return str(response)
        
        conversation_ai = self.conversation_sessions[call_sid]
        
        try:
            # Process the user input with async call
            ai_response = await conversation_ai.process_user_input(speech_result)
            
            # Handle different actions
            if ai_response["action"] == "end_call":
                response.say(ai_response["tts_text"], voice='alice')
                response.hangup()
                # Clean up session
                if call_sid in self.conversation_sessions:
                    del self.conversation_sessions[call_sid]
            
            elif ai_response["action"] == "start_email_reading":
                response.say(ai_response["tts_text"], voice='alice')
                response.redirect('/voice/read_email')
            
            elif ai_response["action"] == "read_next_email":
                response.say(ai_response["tts_text"], voice='alice')
                response.redirect('/voice/read_email')
            
            elif ai_response["action"] == "continue_reading":
                response.say(ai_response["tts_text"], voice='alice')
                response.redirect('/voice/read_email')
            
            elif ai_response["action"] == "wait_for_response_content":
                response.say(ai_response["tts_text"], voice='alice')
                
                gather = Gather(
                    input='speech',
                    action='/voice/process_input',
                    method='POST',
                    speech_timeout='auto',
                    language='en-US'
                )
                response.append(gather)
                
                response.say("I didn't hear your response. What would you like me to say?", voice='alice')
                response.redirect('/voice/process_input')
            
            else:  # continue or other actions
                response.say(ai_response["tts_text"], voice='alice')
                
                gather = Gather(
                    input='speech',
                    action='/voice/process_input',
                    method='POST',
                    speech_timeout='auto',
                    language='en-US'
                )
                response.append(gather)
                
                response.say("How else can I help you?", voice='alice')
                response.redirect('/voice/process_input')
        
        except Exception as e:
            logging.error(f"Error processing user input: {e}")
            logging.exception("Full exception details:")
            response.say("I'm sorry, I encountered an error. Let me try again.", voice='alice')
            response.redirect('/voice/greeting')
        
        return str(response)
    
    async def read_current_email(self, request: Request) -> str:
        """Read the current email to the user"""
        response = VoiceResponse()
        
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        
        if call_sid not in self.conversation_sessions:
            response.say("I'm sorry, I lost our conversation. Let me restart.", voice='alice')
            response.redirect('/voice/greeting')
            return str(response)
        
        conversation_ai = self.conversation_sessions[call_sid]
        
        try:
            # Get current email for reading with async call
            email_text = await conversation_ai.get_current_email_for_reading()
            
            if email_text:
                # Read the email
                response.say(email_text, voice='alice')
                
                # Wait for user input (respond, next, stop, etc.)
                gather = Gather(
                    input='speech',
                    action='/voice/process_input',
                    method='POST',
                    speech_timeout='auto',
                    language='en-US'
                )
                response.append(gather)
                
                # Fallback
                response.say("Say 'respond' to reply, 'next' for the next email, or 'stop' to finish.", voice='alice')
                response.redirect('/voice/read_email')
            else:
                response.say("No more emails to read. Is there anything else I can help you with?", voice='alice')
                
                gather = Gather(
                    input='speech',
                    action='/voice/process_input',
                    method='POST',
                    speech_timeout='auto',
                    language='en-US'
                )
                response.append(gather)
                
                response.say("How else can I help you?", voice='alice')
                response.redirect('/voice/process_input')
        
        except Exception as e:
            logging.error(f"Error reading email: {e}")
            logging.exception("Full exception details:")
            response.say("I had trouble reading that email. Let me try the next one.", voice='alice')
            response.redirect('/voice/process_input')
        
        return str(response)
    
    async def handle_call_status(self, request: Request) -> str:
        """Handle call status updates"""
        form_data = await request.form()
        call_sid = form_data.get('CallSid')
        call_status = form_data.get('CallStatus')
        
        logging.info(f"Call {call_sid} status: {call_status}")
        
        # Clean up session when call ends
        if call_status in ['completed', 'failed', 'busy', 'no-answer'] and call_sid in self.conversation_sessions:
            conversation_ai = self.conversation_sessions[call_sid]
            # Properly close the async context manager
            try:
                await conversation_ai.__aexit__(None, None, None)
            except Exception as e:
                logging.error(f"Error closing ConversationAI session: {e}")
            
            del self.conversation_sessions[call_sid]
            logging.info(f"Cleaned up session for call {call_sid}")
        
        return "OK" 