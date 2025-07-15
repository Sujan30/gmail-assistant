import os.path
import base64
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import aiplatform
import vertexai
from vertexai.generative_models import GenerativeModel

from dotenv import load_dotenv
load_dotenv('.env.local')

project_id = os.getenv("GOOGLE_PROJECT_ID")


class GmailAssistant:
    """AI-powered Gmail assistant for email importance analysis."""
    
    def __init__(self, credentials_path: str = None, project_id: str = None, location: str = "us-central1"):
        """
        Initialize the Gmail Assistant.
        
        Args:
            credentials_path: Path to OAuth credentials file
            project_id: Google Cloud project ID
            location: Vertex AI location
        """
        self.credentials_path = credentials_path or os.getenv("CREDENTIALS_PATH")
        self.project_id = project_id or os.getenv("GOOGLE_PROJECT_ID")
        self.location = location
        self.scopes = ['https://www.googleapis.com/auth/gmail.modify']
        
        # Services
        self.creds = None
        self.gmail_service = None
        self.vertex_model = None
        
        # Initialize services
        self._initialize_credentials()
        self._initialize_gmail_service()
        self._initialize_vertex_ai()
    
    def _initialize_credentials(self) -> None:
        """Initialize OAuth credentials for Google services."""
        if os.path.exists("token.json"):
            self.creds = Credentials.from_authorized_user_file("token.json", self.scopes)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.scopes
                )
                self.creds = flow.run_local_server(port=0)
            
            with open("token.json", "w") as token:
                token.write(self.creds.to_json())
    
    def _initialize_gmail_service(self) -> None:
        """Initialize Gmail API service."""
        try:
            self.gmail_service = build("gmail", "v1", credentials=self.creds)
            print("✅ Gmail service initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing Gmail service: {e}")
            raise
    
    def _initialize_vertex_ai(self) -> None:
        """Initialize Vertex AI with OAuth credentials."""
        try:
            # Initialize Vertex AI with the same credentials
            vertexai.init(
                project=self.project_id, 
                location=self.location,
                credentials=self.creds
            )
            self.vertex_model = GenerativeModel('gemini-1.5-flash')
            print("✅ Vertex AI (Gemini) initialized successfully")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize Vertex AI: {e}")
            print("📋 Will use fallback analysis instead")
            self.vertex_model = None
    
    def get_message_details(self, msg_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific email message.
        
        Args:
            msg_id: Gmail message ID
            
        Returns:
            Dictionary containing email details or None if error
        """
        try:
            message = self.gmail_service.users().messages().get(
                userId="me", id=msg_id
            ).execute()
            
            # Extract headers
            headers = message['payload'].get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Extract body
            body = self._extract_message_body(message['payload'])
            
            # Get labels
            labels = message.get('labelIds', [])
            
            return {
                'id': msg_id,
                'threadId': message['threadId'],
                'subject': subject,
                'sender': sender,
                'date': date,
                'body': body,
                'labels': labels,
                'snippet': message.get('snippet', '')
            }
        except Exception as error:
            print(f"❌ Error getting message {msg_id}: {error}")
            return None
    
    def _extract_message_body(self, payload: Dict) -> str:
        """Extract the body text from email payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
                elif part['mimeType'] == 'text/html':
                    data = part['body']['data']
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                    # Strip HTML tags for basic text
                    body = re.sub('<[^<]+?>', '', html_body)
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body.strip()
    
    def analyze_email_with_ai(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use Gemini AI to analyze email importance.
        
        Args:
            email_data: Dictionary containing email information
            
        Returns:
            Dictionary containing analysis results
        """
        if not self.vertex_model:
            return self._analyze_email_fallback(email_data)
        
        try:
            # Prepare email content for analysis
            email_content = f"""
            EMAIL ANALYSIS REQUEST:
            
            From: {email_data['sender']}
            Subject: {email_data['subject']}
            Date: {email_data['date']}
            Body: {email_data['body'][:1500]}
            Snippet: {email_data['snippet']}
            Gmail Labels: {', '.join(email_data['labels'])}
            
            Please analyze this email and provide an importance score and reasoning.
            
            ANALYSIS CRITERIA:
            - Sender reputation and relationship (personal vs automated)
            - Subject urgency and keywords
            - Content urgency and action items
            - Professional vs personal context
            - Time sensitivity
            - Financial or legal implications
            
            RESPONSE FORMAT (JSON only):
            {{
                "importance_score": <number 0-100>,
                "importance_level": "<HIGH|MEDIUM|LOW>",
                "reasoning": [
                    "Primary reason for this score",
                    "Secondary reason",
                    "Additional context"
                ],
                "urgency_indicators": [
                    "List any urgent keywords or phrases found"
                ],
                "action_required": <true|false>,
                "estimated_response_time": "<IMMEDIATE|WITHIN_HOUR|WITHIN_DAY|WHEN_CONVENIENT>"
            }}
            
            Score Guidelines:
            - 80-100: Critical/Urgent (HIGH) - Immediate attention required
            - 50-79: Important (MEDIUM) - Should respond within hours
            - 20-49: Routine (LOW) - Can wait 1-2 days  
            - 0-19: Low priority (LOW) - Can wait or ignore
            """
            
            response = self.vertex_model.generate_content(email_content)
            
            # Try to parse JSON response
            try:
                response_text = response.text
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start != -1 and json_end != -1:
                    json_text = response_text[json_start:json_end]
                    analysis = json.loads(json_text)
                    
                    # Validate required fields
                    required_fields = ['importance_score', 'importance_level', 'reasoning']
                    if all(field in analysis for field in required_fields):
                        return analysis
                    else:
                        print(f"⚠️  Incomplete AI response, using fallback for email {email_data['id']}")
                        return self._analyze_email_fallback(email_data)
                else:
                    print(f"⚠️  No JSON found in AI response, using fallback for email {email_data['id']}")
                    return self._analyze_email_fallback(email_data)
                    
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON parsing error: {e}, using fallback for email {email_data['id']}")
                return self._analyze_email_fallback(email_data)
                
        except Exception as e:
            print(f"⚠️  Vertex AI error: {e}, using fallback for email {email_data['id']}")
            return self._analyze_email_fallback(email_data)
    
    def _analyze_email_fallback(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback analysis when AI is unavailable."""
        importance_score = 0
        reasons = []
        
        sender_email = self._extract_email_from_sender(email_data['sender'])
        
        # Check for automated emails
        if 'noreply' not in sender_email.lower() and 'no-reply' not in sender_email.lower():
            importance_score += 20
            reasons.append("Personal email (not automated)")
        
        # Subject keywords
        urgent_keywords = ['urgent', 'asap', 'important', 'deadline', 'action required', 
                          'invoice', 'payment', 'security', 'verify', 'expire']
        
        subject_lower = email_data['subject'].lower()
        urgent_found = [keyword for keyword in urgent_keywords if keyword in subject_lower]
        if urgent_found:
            importance_score += 30
            reasons.append(f"Urgent keywords: {', '.join(urgent_found)}")
        
        # Gmail's importance markers
        if 'IMPORTANT' in email_data['labels']:
            importance_score += 25
            reasons.append("Gmail marked as important")
        
        if 'CATEGORY_PRIMARY' in email_data['labels']:
            importance_score += 15
            reasons.append("Primary inbox")
        
        # Determine level
        if importance_score >= 50:
            level = "HIGH"
        elif importance_score >= 25:
            level = "MEDIUM"
        else:
            level = "LOW"
        
        return {
            'importance_score': importance_score,
            'importance_level': level,
            'reasoning': reasons,
            'urgency_indicators': urgent_found,
            'action_required': importance_score >= 50,
            'estimated_response_time': 'WITHIN_DAY' if importance_score >= 50 else 'WHEN_CONVENIENT'
        }
    
    def _extract_email_from_sender(self, sender: str) -> str:
        """Extract email address from sender string."""
        match = re.search(r'<([^>]+)>', sender)
        if match:
            return match.group(1)
        return sender
    
    def get_inbox_messages(self, max_results: int = 10, label_ids: List[str] = None) -> List[Dict[str, str]]:
        """
        Get messages from inbox.
        
        Args:
            max_results: Maximum number of messages to retrieve
            label_ids: List of label IDs to filter by
            
        Returns:
            List of message dictionaries
        """
        try:
            if label_ids is None:
                label_ids = ['INBOX']
                
            results = self.gmail_service.users().messages().list(
                userId="me", 
                maxResults=max_results,
                labelIds=label_ids
            ).execute()
            
            return results.get('messages', [])
        except HttpError as error:
            print(f"❌ Error retrieving messages: {error}")
            return []
    
    def analyze_inbox(self, max_emails: int = 5) -> List[Dict[str, Any]]:
        """
        Analyze importance of emails in inbox.
        
        Args:
            max_emails: Maximum number of emails to analyze
            
        Returns:
            List of email analysis results
        """
        print("🤖 AI-POWERED EMAIL IMPORTANCE ANALYSIS")
        print("=" * 60)
        if self.vertex_model:
            print("🔮 Using Vertex AI (Gemini) for intelligent analysis")
        else:
            print("📋 Using fallback rule-based analysis")
        print("=" * 60)
        
        messages = self.get_inbox_messages(max_results=max_emails)
        
        if not messages:
            print("📭 No messages found in inbox.")
            return []
        
        analysis_results = []
        
        for i, msg in enumerate(messages, 1):
            email_data = self.get_message_details(msg['id'])
            if email_data:
                print(f"\n📧 Analyzing email {i}/{len(messages)}...")
                analysis = self.analyze_email_with_ai(email_data)
                
                # Combine email data with analysis
                result = {
                    **email_data,
                    'analysis': analysis
                }
                analysis_results.append(result)
                
                # Display results
                self._display_analysis_result(email_data, analysis)
        
        return analysis_results
    
    def _display_analysis_result(self, email_data: Dict[str, Any], analysis: Dict[str, Any]) -> None:
        """Display formatted analysis result."""
        importance_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
        action_emoji = "⚡" if analysis.get('action_required', False) else "📋"
        
        print(f"\n{action_emoji} Email ID: {email_data['id']}")
        print(f"📤 From: {email_data['sender']}")
        print(f"📑 Subject: {email_data['subject']}")
        print(f"{importance_emoji.get(analysis['importance_level'], '⚪')} Importance: {analysis['importance_level']} (Score: {analysis['importance_score']})")
        print(f"⏰ Response Time: {analysis.get('estimated_response_time', 'N/A')}")
        
        if analysis.get('urgency_indicators'):
            print(f"🚨 Urgency Indicators: {', '.join(analysis['urgency_indicators'])}")
        
        print(f"💭 AI Reasoning:")
        for reason in analysis['reasoning']:
            print(f"   • {reason}")
        
        print(f"📄 Snippet: {email_data['snippet'][:150]}...")
        print("-" * 50)
    
    def get_high_priority_emails(self, max_emails: int = 20) -> List[Dict[str, Any]]:
        """
        Get only high priority emails from analysis.
        
        Args:
            max_emails: Maximum number of emails to analyze
            
        Returns:
            List of high priority email analysis results
        """
        all_results = self.analyze_inbox(max_emails)
        return [
            result for result in all_results 
            if result['analysis']['importance_level'] == 'HIGH'
        ]


def main():
    """Main function for standalone execution."""
    try:
        # Initialize the Gmail Assistant
        assistant = GmailAssistant()
        
        # Analyze inbox
        results = assistant.analyze_inbox(max_emails=5)
        
        # Summary
        if results:
            high_priority = len([r for r in results if r['analysis']['importance_level'] == 'HIGH'])
            medium_priority = len([r for r in results if r['analysis']['importance_level'] == 'MEDIUM'])
            low_priority = len([r for r in results if r['analysis']['importance_level'] == 'LOW'])
            
            print(f"\n📊 SUMMARY:")
            print(f"🔴 High Priority: {high_priority}")
            print(f"🟡 Medium Priority: {medium_priority}")
            print(f"🟢 Low Priority: {low_priority}")
            print(f"📧 Total Analyzed: {len(results)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
