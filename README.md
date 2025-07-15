# Gmail Assistant with Interactive Voice Calling

An AI-powered voice assistant that can read your emails, help you respond to them, and manage tasks through phone calls using Twilio and conversational AI.

## Features

🎤 **Interactive Voice Calls**: Call in and have natural conversations with your AI assistant
📧 **Email Management**: Get your emails read aloud with AI-powered importance analysis  
✍️ **Voice-to-Email**: Dictate responses that get automatically composed and sent
🧠 **Smart AI**: Uses OpenAI GPT-4 for natural conversation and Google Gemini for email analysis
📱 **Multi-Platform**: Works with any phone that can make/receive calls

## How It Works

1. **Call Your Assistant**: Use the calling system to dial into your AI assistant
2. **Natural Conversation**: Say "Read my emails" or ask for specific help
3. **Interactive Email Reading**: Listen to emails one by one with importance scoring
4. **Voice Responses**: Say "respond" during any email to dictate a reply
5. **AI-Powered Composition**: Your voice gets turned into professional email responses

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:

- **Twilio**: Get from [Twilio Console](https://console.twilio.com/)
- **OpenAI**: Get from [OpenAI API Keys](https://platform.openai.com/api-keys)
- **Google**: Set up Gmail API and download credentials JSON

### 3. Configure Google Services

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Gmail API and Vertex AI API
3. Create OAuth 2.0 credentials
4. Download the credentials JSON file
5. Update `CREDENTIALS_PATH` in your `.env` file

### 4. Set Up Twilio

1. Sign up at [Twilio](https://twilio.com)
2. Get a phone number with voice capabilities
3. Configure webhook URLs (see Deployment section)

### 5. Run the Server

```bash
python app.py
```

The server will start on `http://localhost:8000`

### 6. Make a Test Call

```bash
python caller.py
```

## Usage Examples

### Voice Commands

- **"Read my emails"** - Start reading emails with AI importance analysis
- **"Respond"** - Reply to the current email being read
- **"Next"** - Skip to the next email
- **"Stop"** - Stop reading emails
- **"Check my calendar"** - Get calendar information
- **"Create a task"** - Add tasks to your todo list
- **"Goodbye"** - End the call

### Email Reading Flow

1. Say "Read my emails"
2. AI fetches and analyzes your emails
3. Emails are read one by one with importance scores
4. During any email, say "respond" to reply
5. Dictate your response naturally
6. AI composes and sends a professional email

## API Endpoints

### REST Endpoints
- `GET /` - API status
- `GET /read-emails` - Get emails via REST
- `POST /make-call` - Initiate an outbound call
- `GET /health` - Health check

### Voice Endpoints (used by Twilio)
- `POST /voice/greeting` - Initial call greeting
- `POST /voice/process_input` - Process user speech
- `POST /voice/read_email` - Read current email
- `POST /voice/status` - Call status updates

## Architecture

```
User's Phone ↔ Twilio ↔ FastAPI Server ↔ OpenAI/Google Services
                           ↓
                    MCP Tools (Email, Calendar, Tasks)
```

### Components

- **VoiceHandler**: Manages Twilio interactions and TwiML responses
- **ConversationAI**: Handles natural language processing with OpenAI
- **MCPClient**: Manages email and other service integrations
- **GmailAssistant**: Google services integration with AI analysis

## Deployment

### For Production Use

1. **Deploy to a cloud service** (Heroku, Railway, etc.)
2. **Update BASE_URL** in your `.env` to your public URL
3. **Configure Twilio webhooks** to point to your server:
   - Voice URL: `https://your-domain.com/voice/greeting`
   - Status Callback: `https://your-domain.com/voice/status`

### Webhook Configuration

In your Twilio phone number configuration:
- **Voice Configuration**: `https://your-domain.com/voice/greeting` (POST)
- **Status Callback**: `https://your-domain.com/voice/status` (POST)

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | Yes |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | Yes |
| `TWILIO_NUMBER` | Your Twilio phone number | Yes |
| `MY_NUMBER` | Your personal phone for testing | Yes |
| `OPENAI_API_KEY` | OpenAI API key for conversation | Yes |
| `GOOGLE_PROJECT_ID` | Google Cloud Project ID | Yes |
| `CREDENTIALS_PATH` | Path to Google credentials JSON | Yes |
| `BASE_URL` | Your server's public URL | Yes |

## Extending the System

### Adding New MCP Tools

Add new tools to `mcp_serve.py`:

```python
@mcp.tool
def your_new_tool(self, param: str) -> str:
    """Description of your tool"""
    # Your implementation
    return "Tool result"
```

### Customizing Conversation Flow

Modify conversation logic in `conversation_ai.py`:

- Update `_handle_greeting_mode()` for new intents
- Add new conversation modes
- Customize AI prompts and responses

## Troubleshooting

### Common Issues

1. **Call doesn't connect**: Check Twilio webhook URLs and credentials
2. **AI doesn't respond**: Verify OpenAI API key and internet connection
3. **Emails not loading**: Check Google credentials and Gmail API permissions
4. **Voice not working**: Ensure Twilio number has voice capabilities

### Debug Mode

Set `DEBUG=true` in `.env` to enable detailed logging.

### Testing Locally

Use a tool like [ngrok](https://ngrok.com) to expose your local server:

```bash
ngrok http 8000
```

Then update your Twilio webhook URLs to the ngrok URL.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with phone calls
5. Submit a pull request

## License

MIT License - feel free to use this for your own projects!

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Twilio and OpenAI documentation
3. Open an issue on GitHub

---

**Happy Calling! 📞🤖** 