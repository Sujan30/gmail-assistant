import openai
import os
import json
from typing import Dict, Any, List, Optional
from mcp_serve import MCPClient
from dotenv import load_dotenv

load_dotenv()

class ConversationAI:
    """AI conversation handler for voice calls"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.mcp_client = MCPClient(user_id)
        self.conversation_state = {
            "mode": "greeting",  # greeting, email_reading, responding, general
            "context": {},
            "conversation_history": []
        }
    
    def process_user_input(self, user_speech: str) -> Dict[str, Any]:
        """
        Process user's speech input and return appropriate response
        
        Args:
            user_speech: User's transcribed speech
            
        Returns:
            Dictionary with response text and action to take
        """
        try:
            # Add user input to conversation history
            self.conversation_state["conversation_history"].append({
                "role": "user",
                "content": user_speech
            })
            
            # Determine intent and generate response
            if self.conversation_state["mode"] == "greeting":
                return self._handle_greeting_mode(user_speech)
            elif self.conversation_state["mode"] == "email_reading":
                return self._handle_email_reading_mode(user_speech)
            elif self.conversation_state["mode"] == "responding":
                return self._handle_responding_mode(user_speech)
            else:
                return self._handle_general_mode(user_speech)
                
        except Exception as e:
            return {
                "response_text": f"I'm sorry, I encountered an error: {str(e)}. Could you please try again?",
                "action": "continue",
                "tts_text": "I'm sorry, I encountered an error. Could you please try again?"
            }
    
    def _handle_greeting_mode(self, user_speech: str) -> Dict[str, Any]:
        """Handle the initial greeting and user request"""
        
        # Use OpenAI to understand the user's intent
        system_prompt = """You are a helpful voice assistant for managing emails and tasks. 
        The user just called in. Analyze their request and determine what they want to do.
        
        Available actions:
        - read_emails: User wants to read their emails
        - calendar: User wants calendar information
        - tasks: User wants to manage tasks
        - general: General conversation or unclear intent
        
        Respond with a friendly acknowledgment and ask for clarification if needed.
        Always be conversational and natural, as this is a voice call.
        
        If they want to read emails, acknowledge and offer to start reading.
        If unclear, ask what they'd like help with today.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_speech}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Determine action based on user input
            user_lower = user_speech.lower()
            if any(keyword in user_lower for keyword in ["email", "emails", "read email", "check email"]):
                self.conversation_state["mode"] = "email_reading"
                # Initialize credentials and get emails
                cred_result = self.mcp_client.initialize_creds()
                email_result = self.mcp_client.get_emails(max_emails=5)
                
                response_text = f"Sure! Let me check your emails. {email_result}. I'll start reading them one by one. You can say 'respond' during any email if you'd like to reply to it."
                action = "start_email_reading"
            else:
                response_text = ai_response
                action = "continue"
            
            return {
                "response_text": response_text,
                "action": action,
                "tts_text": response_text
            }
            
        except Exception as e:
            return {
                "response_text": "Hello! I'm your email assistant. How can I help you today? You can ask me to read your emails, check your calendar, or manage tasks.",
                "action": "continue",
                "tts_text": "Hello! I'm your email assistant. How can I help you today?"
            }
    
    def _handle_email_reading_mode(self, user_speech: str) -> Dict[str, Any]:
        """Handle user input while reading emails"""
        
        user_lower = user_speech.lower()
        
        # Check for specific commands
        if "respond" in user_lower or "reply" in user_lower:
            self.conversation_state["mode"] = "responding"
            current_email = self.mcp_client.get_current_email()
            if current_email.get("success"):
                self.conversation_state["context"]["responding_to"] = current_email["email"]
                response_text = "What would you like me to say in your response?"
                return {
                    "response_text": response_text,
                    "action": "wait_for_response_content",
                    "tts_text": response_text
                }
            else:
                response_text = "I couldn't get the current email details. Let me continue reading."
                return {
                    "response_text": response_text,
                    "action": "continue_reading",
                    "tts_text": response_text
                }
        
        elif any(word in user_lower for word in ["next", "skip", "continue"]):
            next_result = self.mcp_client.next_email()
            if "No more emails" in next_result:
                self.conversation_state["mode"] = "general"
                response_text = "That's all your emails! Is there anything else I can help you with?"
            else:
                response_text = f"{next_result}. Moving to the next email."
                return {
                    "response_text": response_text,
                    "action": "read_next_email",
                    "tts_text": response_text
                }
        
        elif any(word in user_lower for word in ["stop", "done", "enough"]):
            self.conversation_state["mode"] = "general"
            response_text = "Okay, I've stopped reading emails. Is there anything else I can help you with?"
        
        else:
            # Default: continue reading current or next email
            response_text = "I'll continue reading. Say 'next' to skip to the next email, or 'respond' if you'd like to reply to this one."
        
        return {
            "response_text": response_text,
            "action": "continue_reading",
            "tts_text": response_text
        }
    
    def _handle_responding_mode(self, user_speech: str) -> Dict[str, Any]:
        """Handle user input for composing email responses"""
        
        responding_to = self.conversation_state["context"].get("responding_to")
        if not responding_to:
            self.conversation_state["mode"] = "email_reading"
            return {
                "response_text": "I lost track of which email you wanted to respond to. Let me continue reading emails.",
                "action": "continue_reading",
                "tts_text": "Let me continue reading emails."
            }
        
        # Use OpenAI to help compose a professional response
        system_prompt = f"""You are helping compose an email response. 
        
        Original email details:
        From: {responding_to['sender']}
        Subject: {responding_to['subject']}
        Content: {responding_to['body']}
        
        The user said: "{user_speech}"
        
        Create a professional email response based on what the user wants to say.
        Keep it concise but polite. Return just the email body text.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_speech}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            composed_response = response.choices[0].message.content
            
            # Send the email reply
            reply_result = self.mcp_client.send_email_reply(
                recipient=responding_to['sender'],
                subject=f"Re: {responding_to['subject']}",
                body=composed_response
            )
            
            self.conversation_state["mode"] = "email_reading"
            response_text = f"I've sent your reply: {composed_response}. {reply_result}. Would you like me to continue reading more emails?"
            
            return {
                "response_text": response_text,
                "action": "continue_reading",
                "tts_text": f"I've sent your reply. Would you like me to continue reading more emails?"
            }
            
        except Exception as e:
            self.conversation_state["mode"] = "email_reading"
            return {
                "response_text": f"I had trouble sending that response. Let me continue reading emails.",
                "action": "continue_reading",
                "tts_text": "I had trouble sending that response. Let me continue reading emails."
            }
    
    def _handle_general_mode(self, user_speech: str) -> Dict[str, Any]:
        """Handle general conversation and commands"""
        
        user_lower = user_speech.lower()
        
        if any(keyword in user_lower for keyword in ["email", "emails", "read email", "check email"]):
            self.conversation_state["mode"] = "greeting"
            return self._handle_greeting_mode(user_speech)
        
        elif any(keyword in user_lower for keyword in ["calendar", "schedule", "appointments"]):
            calendar_result = self.mcp_client.get_calendar_events()
            response_text = calendar_result
        
        elif any(keyword in user_lower for keyword in ["task", "tasks", "todo"]):
            response_text = "I can help you create tasks. What task would you like me to add?"
        
        elif any(keyword in user_lower for keyword in ["goodbye", "bye", "done", "thank you", "thanks"]):
            response_text = "You're welcome! Have a great day. Goodbye!"
            return {
                "response_text": response_text,
                "action": "end_call",
                "tts_text": response_text
            }
        
        else:
            # Use OpenAI for general conversation
            system_prompt = """You are a helpful voice assistant. Be conversational and friendly.
            Keep responses brief since this is a voice call. Offer to help with emails, calendar, or tasks."""
            
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_speech}
                    ],
                    max_tokens=100,
                    temperature=0.7
                )
                
                response_text = response.choices[0].message.content
            except:
                response_text = "I can help you with reading emails, checking your calendar, or managing tasks. What would you like to do?"
        
        return {
            "response_text": response_text,
            "action": "continue",
            "tts_text": response_text
        }
    
    def get_current_email_for_reading(self) -> Optional[str]:
        """Get the current email formatted for text-to-speech reading"""
        try:
            current_email = self.mcp_client.get_current_email()
            if current_email.get("success"):
                email = current_email["email"]
                
                # Format for natural speech
                reading_text = f"""
                Email {current_email['position']}:
                From {email['sender']}.
                Subject: {email['subject']}.
                
                {email['body']}
                
                This email has {email['importance']} priority with a score of {email['score']}.
                
                Say 'respond' if you'd like to reply, 'next' for the next email, or 'stop' to finish reading.
                """
                
                return reading_text.strip()
            else:
                return "No more emails to read."
        except Exception as e:
            return f"Error reading email: {str(e)}" 