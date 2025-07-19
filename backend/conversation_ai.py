import openai
import os
import json
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv('.env.local')

class MCPClient:
    """MCP Client for communicating with the MCP server"""
    
    def __init__(self, server_url: str = "http://localhost:3000"):
        self.server_url = server_url
        self.client = httpx.AsyncClient()
    
    async def call_tool(self, tool_name: str, **kwargs) -> str:
        """Call an MCP tool via HTTP"""
        try:
            response = await self.client.post(
                f"{self.server_url}/call-tool",
                json={
                    "tool": tool_name,
                    "arguments": kwargs
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json().get("result", "No result")
        except Exception as e:
            return f"Error calling MCP tool {tool_name}: {str(e)}"
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

class ConversationAI:
    """AI conversation handler for voice calls - MCP Client Integration"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.mcp_client = MCPClient()
        self.conversation_state = {
            "mode": "greeting",  # greeting, email_reading, responding, general
            "context": {},
            "conversation_history": []
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.mcp_client.close()
    
    async def process_user_input(self, user_speech: str) -> Dict[str, Any]:
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
                return await self._handle_greeting_mode(user_speech)
            elif self.conversation_state["mode"] == "email_reading":
                return await self._handle_email_reading_mode(user_speech)
            elif self.conversation_state["mode"] == "responding":
                return await self._handle_responding_mode(user_speech)
            else:
                return await self._handle_general_mode(user_speech)
                
        except Exception as e:
            return {
                "response_text": f"I'm sorry, I encountered an error: {str(e)}. Could you please try again?",
                "action": "continue",
                "tts_text": "I'm sorry, I encountered an error. Could you please try again?"
            }
    
    async def _handle_greeting_mode(self, user_speech: str) -> Dict[str, Any]:
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
                # Initialize credentials and get emails via MCP
                cred_result = await self.mcp_client.call_tool("initialize_creds", user_id=self.user_id)
                email_result = await self.mcp_client.call_tool("get_emails", user_id=self.user_id, max_emails=5)
                
                response_text = f"Sure! Let me check your emails. {email_result}. I'll present each email's subject first, then you can choose whether to read the full email or skip to the next one."
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
    
    async def _handle_email_reading_mode(self, user_speech: str) -> Dict[str, Any]:
        """Handle user input during email reading"""
        
        user_lower = user_speech.lower()
        
        if any(keyword in user_lower for keyword in ["read", "read it", "read full", "read full email", "yes", "sure", "okay"]):
            # Read the full email content
            full_email = await self.mcp_client.call_tool("read_full_current_email", user_id=self.user_id)
            response_text = full_email
            action = "continue"
        
        elif any(keyword in user_lower for keyword in ["next", "skip", "continue"]):
            # Move to next email
            next_result = await self.mcp_client.call_tool("next_email", user_id=self.user_id)
            
            if "No more emails" in next_result:
                self.conversation_state["mode"] = "general"
                response_text = "That's all your emails! Is there anything else I can help you with?"
                action = "continue"
            else:
                response_text = f"{next_result}. Here's the next email."
                action = "read_next_email"
        
        elif any(keyword in user_lower for keyword in ["respond", "reply", "answer"]):
            # Switch to responding mode
            self.conversation_state["mode"] = "responding"
            response_text = "What would you like me to say in your reply?"
            action = "wait_for_response_content"
        
        elif any(keyword in user_lower for keyword in ["stop", "done", "finish"]):
            # Stop reading emails
            self.conversation_state["mode"] = "general"
            response_text = "Finished reading emails. How else can I help you?"
            action = "continue"
        
        else:
            # Continue reading current email or ask for clarification
            response_text = "I can read this email, skip to the next one, help you respond to this one, or stop reading. What would you like to do?"
            action = "continue"
        
        return {
            "response_text": response_text,
            "action": action,
            "tts_text": response_text
        }
    
    async def _handle_responding_mode(self, user_speech: str) -> Dict[str, Any]:
        """Handle composing email responses"""
        
        # Store the response content
        self.conversation_state["context"]["response_content"] = user_speech
        
        # Get current email info for reply
        current_email = await self.mcp_client.call_tool("get_current_email_for_reading", user_id=self.user_id)
        
        # For now, simulate sending
        reply_result = await self.mcp_client.call_tool(
            "send_email_reply",
            user_id=self.user_id,
            recipient="sender@example.com",  # This would be extracted from current email
            subject="Re: Email Subject",      # This would be from current email
            body=user_speech
        )
        
        # Switch back to email reading mode
        self.conversation_state["mode"] = "email_reading"
        
        response_text = f"{reply_result}. Would you like me to continue reading emails or do something else?"
        
        return {
            "response_text": response_text,
            "action": "continue",
            "tts_text": response_text
        }
    
    async def _handle_general_mode(self, user_speech: str) -> Dict[str, Any]:
        """Handle general conversation and commands"""
        
        user_lower = user_speech.lower()
        
        if any(keyword in user_lower for keyword in ["email", "emails", "read email", "check email"]):
            self.conversation_state["mode"] = "greeting"
            return await self._handle_greeting_mode(user_speech)
        
        elif any(keyword in user_lower for keyword in ["calendar", "schedule", "appointments"]):
            calendar_result = await self.mcp_client.call_tool("get_calendar_events", user_id=self.user_id)
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
    
    async def get_current_email_for_reading(self) -> Optional[str]:
        """Get the current email formatted for text-to-speech reading"""
        try:
            # Use the MCP client to get voice-optimized email reading
            reading_text = await self.mcp_client.call_tool("get_current_email_for_reading", user_id=self.user_id)
            
            # Add instructions for user interaction (this now presents just the subject)
            if not reading_text.startswith("Sorry,"):
                reading_text += " Say 'read it' to hear the full email, 'next' to skip to the next one, 'respond' to reply, or 'stop' to finish."
            
            return reading_text
        except Exception as e:
            return f"Error reading email: {str(e)}" 