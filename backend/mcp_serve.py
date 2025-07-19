from fastmcp import FastMCP
from main import GmailAssistant
import json
from typing import List, Dict, Any
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

logger = logging.getLogger(__name__)

# Create MCP server instance
mcp = FastMCP("Gmail Assistant MCP Server")

# Create FastAPI app for HTTP interface
app = FastAPI(title="MCP HTTP Interface")

# Global storage for user sessions (in production, use Redis or database)
user_sessions = {}

class UserSession:
    """User session management for MCP tools"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.gmail_assistant = None
        self.gmail_emails = None
        self.current_email_index = 0
        logger.info(f"📧 User session created for: {user_id}")

class ToolCallRequest(BaseModel):
    """Request model for tool calls"""
    tool: str
    arguments: Dict[str, Any]

class ToolCallResponse(BaseModel):
    """Response model for tool calls"""
    result: str
    success: bool = True

def get_user_session(user_id: str) -> UserSession:
    """Get or create user session"""
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id)
    return user_sessions[user_id]

# HTTP endpoint for tool calls
@app.post("/call-tool", response_model=ToolCallResponse)
async def call_tool_http(request: ToolCallRequest):
    """HTTP endpoint to call MCP tools"""
    try:
        tool_name = request.tool
        args = request.arguments
        
        # Route to appropriate tool function
        if tool_name == "initialize_creds":
            result = await initialize_creds_impl(args.get("user_id"))
        elif tool_name == "get_emails":
            result = await get_emails_impl(args.get("user_id"), args.get("max_emails", 5))
        elif tool_name == "get_current_email_for_reading":
            result = await get_current_email_for_reading_impl(args.get("user_id"))
        elif tool_name == "read_full_current_email":
            result = await read_full_current_email_impl(args.get("user_id"))
        elif tool_name == "next_email":
            result = await next_email_impl(args.get("user_id"))
        elif tool_name == "send_email_reply":
            result = await send_email_reply_impl(
                args.get("user_id"),
                args.get("recipient"),
                args.get("subject"),
                args.get("body")
            )
        elif tool_name == "get_calendar_events":
            result = await get_calendar_events_impl(args.get("user_id"), args.get("days", 7))
        elif tool_name == "create_task":
            result = await create_task_impl(
                args.get("user_id"),
                args.get("title"),
                args.get("description", "")
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
        
        return ToolCallResponse(result=result, success=True)
    
    except Exception as e:
        logger.error(f"Error calling tool {request.tool}: {e}")
        logger.exception("Full exception details:")
        return ToolCallResponse(result=f"Error: {str(e)}", success=False)

# Tool implementation functions
async def initialize_creds_impl(user_id: str) -> str:
    """Initialize Gmail credentials for a user"""
    try:
        logger.info(f"🔐 Initializing Gmail credentials for user {user_id}")
        session = get_user_session(user_id)
        session.gmail_assistant = GmailAssistant()
        logger.info(f"✅ Gmail credentials initialized successfully for user {user_id}")
        return f"✅ Gmail credentials initialized successfully for user {user_id}"
    except Exception as e:
        error_msg = f"❌ Error initializing credentials for user {user_id}: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full exception details:")
        return error_msg

async def get_emails_impl(user_id: str, max_emails: int = 5) -> str:
    """Get and analyze emails for a user"""
    try:
        logger.info(f"📧 Getting emails for user {user_id}, max_emails={max_emails}")
        session = get_user_session(user_id)
        
        if not session.gmail_assistant:
            error_msg = "❌ Please initialize credentials first"
            logger.error(error_msg)
            return error_msg
        
        # Get analyzed emails using GmailAssistant
        logger.info(f"🔍 Analyzing inbox for user {user_id}")
        analyzed_emails = session.gmail_assistant.analyze_inbox(max_emails=max_emails)
        
        if not analyzed_emails:
            logger.info(f"📭 No emails found for user {user_id}")
            return "📭 No emails found in your inbox."
        
        # Store emails for this user session
        session.gmail_emails = analyzed_emails
        session.current_email_index = 0
        
        # Create summary
        high_priority = len([e for e in analyzed_emails if e['analysis']['importance_level'] == 'HIGH'])
        medium_priority = len([e for e in analyzed_emails if e['analysis']['importance_level'] == 'MEDIUM'])
        low_priority = len([e for e in analyzed_emails if e['analysis']['importance_level'] == 'LOW'])
        
        summary = f"📧 Found {len(analyzed_emails)} emails: {high_priority} high priority, {medium_priority} medium priority, {low_priority} low priority"
        logger.info(f"✅ Email analysis complete for user {user_id}: {summary}")
        return summary
        
    except Exception as e:
        error_msg = f"❌ Error getting emails for user {user_id}: {str(e)}"
        logger.error(error_msg)
        logger.exception("Full exception details:")
        return error_msg

async def get_current_email_for_reading_impl(user_id: str) -> str:
    """Get current email subject and ask if user wants to read it"""
    try:
        logger.info(f"🎤 Presenting email subject for user {user_id}")
        session = get_user_session(user_id)
        
        if not session.gmail_emails:
            return "Sorry, no emails loaded. Please get emails first."
        
        if session.current_email_index >= len(session.gmail_emails):
            return "Sorry, no more emails to read."
        
        email = session.gmail_emails[session.current_email_index]
        position = f"{session.current_email_index + 1} of {len(session.gmail_emails)}"
        
        # Format for voice reading
        importance_text = {
            "HIGH": "high priority",
            "MEDIUM": "medium priority", 
            "LOW": "low priority"
        }.get(email['analysis']['importance_level'], "normal priority")
        
        # Clean sender for voice (remove email addresses in brackets)
        sender = email["sender"].split('<')[0].strip()
        if not sender:
            sender = email["sender"]
        
        # Only read subject and ask if they want to continue
        voice_text = f"Email {position}. This is a {importance_text} email from {sender}. Subject: {email['subject']}. Would you like me to read this email or skip to the next one?"
        
        logger.info(f"✅ Presented email subject for user {user_id}")
        return voice_text
        
    except Exception as e:
        error_msg = f"Error reading email: {str(e)}"
        logger.error(f"❌ {error_msg} for user {user_id}")
        logger.exception("Full exception details:")
        return error_msg

async def read_full_current_email_impl(user_id: str) -> str:
    """Read the full content of the current email"""
    try:
        logger.info(f"🎤 Reading full email content for user {user_id}")
        session = get_user_session(user_id)
        
        if not session.gmail_emails:
            return "Sorry, no emails loaded. Please get emails first."
        
        if session.current_email_index >= len(session.gmail_emails):
            return "Sorry, no more emails to read."
        
        email = session.gmail_emails[session.current_email_index]
        
        # Read the full email body
        full_content = email['body'][:1200]  # Limit to reasonable length for voice
        if len(email['body']) > 1200:
            full_content += " ... email content continues. Say 'respond' to reply or 'next' for the next email."
        else:
            full_content += " Say 'respond' to reply to this email or 'next' for the next email."
        
        logger.info(f"✅ Read full email content for user {user_id}")
        return full_content
        
    except Exception as e:
        error_msg = f"Error reading full email: {str(e)}"
        logger.error(f"❌ {error_msg} for user {user_id}")
        logger.exception("Full exception details:")
        return error_msg

async def next_email_impl(user_id: str) -> str:
    """Move to the next email for a user"""
    try:
        logger.info(f"⏭️ Moving to next email for user {user_id}")
        session = get_user_session(user_id)
        
        if not session.gmail_emails:
            error_msg = "No emails loaded"
            logger.error(f"❌ {error_msg} for user {user_id}")
            return error_msg
        
        session.current_email_index += 1
        if session.current_email_index >= len(session.gmail_emails):
            msg = "No more emails to read"
            logger.info(f"📭 {msg} for user {user_id}")
            return msg
        
        result = f"Moved to email {session.current_email_index + 1} of {len(session.gmail_emails)}"
        logger.info(f"✅ {result} for user {user_id}")
        return result
        
    except Exception as e:
        error_msg = f"Error moving to next email: {str(e)}"
        logger.error(f"❌ {error_msg} for user {user_id}")
        logger.exception("Full exception details:")
        return error_msg

async def send_email_reply_impl(user_id: str, recipient: str, subject: str, body: str) -> str:
    """Send email reply from user's account"""
    try:
        logger.info(f"📤 Sending email reply for user {user_id} to {recipient}")
        session = get_user_session(user_id)
        
        if not session.gmail_assistant:
            error_msg = "❌ Please initialize credentials first"
            logger.error(error_msg)
            return error_msg
        
        # TODO: Implement actual email sending via Gmail API
        result = f"✅ Email reply sent to {recipient} with subject: {subject}"
        logger.info(f"✅ Email reply sent for user {user_id}")
        return result
        
    except Exception as e:
        error_msg = f"❌ Error sending email: {str(e)}"
        logger.error(f"❌ {error_msg} for user {user_id}")
        logger.exception("Full exception details:")
        return error_msg

async def get_calendar_events_impl(user_id: str, days: int = 7) -> str:
    """Get calendar events for a user"""
    try:
        logger.info(f"📅 Getting calendar events for user {user_id}")
        # TODO: Implement calendar functionality
        result = f"📅 Calendar events retrieved for user {user_id} (next {days} days)"
        logger.info(f"✅ Calendar events retrieved for user {user_id}")
        return result
    except Exception as e:
        error_msg = f"❌ Error getting calendar events: {str(e)}"
        logger.error(f"❌ {error_msg} for user {user_id}")
        return error_msg

async def create_task_impl(user_id: str, title: str, description: str = "") -> str:
    """Create task for a user"""
    try:
        logger.info(f"✅ Creating task for user {user_id}: {title}")
        # TODO: Implement task functionality
        result = f"✅ Task '{title}' created for user {user_id}"
        logger.info(f"✅ Task created for user {user_id}")
        return result
    except Exception as e:
        error_msg = f"❌ Error creating task: {str(e)}"
        logger.error(f"❌ {error_msg} for user {user_id}")
        return error_msg

# Keep the original MCP tools for FastMCP compatibility
@mcp.tool
def initialize_creds(user_id: str) -> str:
    """Initialize Gmail credentials for a user"""
    import asyncio
    return asyncio.run(initialize_creds_impl(user_id))

@mcp.tool
def get_emails(user_id: str, max_emails: int = 5) -> str:
    """Get and analyze emails for a user"""
    import asyncio
    return asyncio.run(get_emails_impl(user_id, max_emails))

@mcp.tool
def get_current_email_for_reading(user_id: str) -> str:
    """Get current email subject and ask if user wants to read it"""
    import asyncio
    return asyncio.run(get_current_email_for_reading_impl(user_id))

@mcp.tool
def read_full_current_email(user_id: str) -> str:
    """Read the full content of the current email"""
    import asyncio
    return asyncio.run(read_full_current_email_impl(user_id))

@mcp.tool
def next_email(user_id: str) -> str:
    """Move to the next email for a user"""
    import asyncio
    return asyncio.run(next_email_impl(user_id))

@mcp.tool
def send_email_reply(user_id: str, recipient: str, subject: str, body: str) -> str:
    """Send email reply from user's account"""
    import asyncio
    return asyncio.run(send_email_reply_impl(user_id, recipient, subject, body))

@mcp.tool
def get_calendar_events(user_id: str, days: int = 7) -> str:
    """Get calendar events for a user"""
    import asyncio
    return asyncio.run(get_calendar_events_impl(user_id, days))

@mcp.tool
def create_task(user_id: str, title: str, description: str = "") -> str:
    """Create task for a user"""
    import asyncio
    return asyncio.run(create_task_impl(user_id, title, description))

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mcp-http-server"}

if __name__ == "__main__":
    # Run the HTTP server for MCP tools
    uvicorn.run(app, host="0.0.0.0", port=3000)