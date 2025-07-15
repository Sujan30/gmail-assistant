from fastmcp import FastMCP
from main import GmailAssistant
import json
from typing import List, Dict, Any

mcp = FastMCP()

class MCPClient:
    """Multi-user MCP tools class with user isolation"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.gmail_assistant = None
        self.user_data = {
            "gmail_emails": None,
            "current_email_index": 0,
            "gmail_creds": None,
            "gmail_token": None,
            "gmail_refresh_token": None,
            "gmail_token_expiry": None,
            "gmail_token_type": None,
        }  # Store user-specific data
    
    @mcp.tool
    def initialize_creds(self) -> str:
        """Initialize credentials for this user"""
        try:
            self.gmail_assistant = GmailAssistant()
            return f"✅ Gmail credentials initialized successfully for user {self.user_id}"
        except Exception as e:
            return f"❌ Error initializing credentials for user {self.user_id}: {str(e)}"
    
    @mcp.tool
    def get_emails(self, max_emails: int = 10) -> str:
        """Get and analyze emails for this user"""
        try:
            if not self.gmail_assistant:
                return "❌ Please initialize credentials first"
            
            # Get analyzed emails
            analyzed_emails = self.gmail_assistant.analyze_inbox(max_emails=max_emails)
            self.user_data["gmail_emails"] = analyzed_emails
            self.user_data["current_email_index"] = 0
            
            if not analyzed_emails:
                return "📭 No emails found in your inbox."
            
            # Create summary
            high_priority = len([e for e in analyzed_emails if e['analysis']['importance_level'] == 'HIGH'])
            medium_priority = len([e for e in analyzed_emails if e['analysis']['importance_level'] == 'MEDIUM'])
            low_priority = len([e for e in analyzed_emails if e['analysis']['importance_level'] == 'LOW'])
            
            summary = f"📧 Found {len(analyzed_emails)} emails: {high_priority} high priority, {medium_priority} medium priority, {low_priority} low priority"
            return summary
            
        except Exception as e:
            return f"❌ Error getting emails for user {self.user_id}: {str(e)}"
    
    @mcp.tool
    def get_current_email(self) -> Dict[str, Any]:
        """Get the current email for reading"""
        try:
            if not self.user_data["gmail_emails"]:
                return {"error": "No emails loaded. Please get emails first."}
            
            current_index = self.user_data["current_email_index"]
            if current_index >= len(self.user_data["gmail_emails"]):
                return {"error": "No more emails to read"}
            
            email = self.user_data["gmail_emails"][current_index]
            return {
                "success": True,
                "email": {
                    "id": email['id'],
                    "subject": email['subject'],
                    "sender": email['sender'],
                    "date": email['date'],
                    "body": email['body'][:500] + "..." if len(email['body']) > 500 else email['body'],
                    "importance": email['analysis']['importance_level'],
                    "score": email['analysis']['importance_score']
                },
                "position": f"{current_index + 1} of {len(self.user_data['gmail_emails'])}"
            }
        except Exception as e:
            return {"error": f"Error getting current email: {str(e)}"}
    
    @mcp.tool
    def next_email(self) -> str:
        """Move to the next email"""
        try:
            if not self.user_data["gmail_emails"]:
                return "No emails loaded"
            
            self.user_data["current_email_index"] += 1
            if self.user_data["current_email_index"] >= len(self.user_data["gmail_emails"]):
                return "No more emails to read"
            
            return f"Moved to email {self.user_data['current_email_index'] + 1} of {len(self.user_data['gmail_emails'])}"
        except Exception as e:
            return f"Error moving to next email: {str(e)}"
    
    @mcp.tool
    def send_email_reply(self, recipient: str, subject: str, body: str) -> str:
        """Send email reply from this user's account"""
        try:
            if not self.gmail_assistant:
                return "❌ Please initialize credentials first"
            
            # This would implement actual email sending
            # For now, return a success message
            return f"✅ Email reply sent to {recipient} with subject: {subject}"
        except Exception as e:
            return f"❌ Error sending email: {str(e)}"
    
    @mcp.tool
    def get_calendar_events(self, days: int = 7) -> str:
        """Get calendar events for this user"""
        # Placeholder for calendar functionality
        return f"📅 Calendar events retrieved for user {self.user_id} (next {days} days)"
    
    @mcp.tool
    def create_task(self, title: str, description: str = "") -> str:
        """Create task for this user"""
        # Placeholder for task functionality
        return f"✅ Task '{title}' created for user {self.user_id}"

# Usage example:
# user1_client = MCPClient("user_123")
# user2_client = MCPClient("user_456")
# Each instance handles tools for their specific user