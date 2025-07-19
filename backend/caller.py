import os
import requests
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv('.env.local')

def make_interactive_call(phone_number: str, test_mode: bool = False):
    """Make an interactive call using the new voice system"""
    
    # First option: Use the FastAPI endpoint
    try:
        base_url = os.environ.get("BASE_URL", "http://localhost:8000")
        response = requests.post(f"{base_url}/make-call", 
                               params={"phone_number": phone_number, "test_mode": test_mode})
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Call initiated successfully!")
            print(f"📞 Call SID: {result.get('call_sid')}")
            return result.get('call_sid')
        else:
            print(f"❌ Error from API: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        # Fallback: Direct Twilio call if API server is not running
        print("⚠️  API server not available, making direct call...")
        return make_direct_call(phone_number, test_mode=test_mode)
    except Exception as e:
        print(f"❌ Error making call through API: {e}")
        return None

def make_direct_call(phone_number: str, test_mode: bool = False):
    """Make a direct Twilio call (fallback)"""
    
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    twilio_number = os.environ["TWILIO_NUMBER"]
    base_url = os.environ.get("BASE_URL", "http://localhost:8000")
    
    client = Client(account_sid, auth_token)
    
    try:
        if test_mode:
            twiml_url = "http://demo.twilio.com/docs/voice.xml"
        else:
            # Add ngrok-skip-browser-warning parameter for free ngrok accounts
            if 'ngrok' in base_url:
                twiml_url = f"{base_url}/voice/greeting?ngrok-skip-browser-warning=true"
                status_callback_url = f"{base_url}/voice/status?ngrok-skip-browser-warning=true"
            else:
                twiml_url = f"{base_url}/voice/greeting"
                status_callback_url = f"{base_url}/voice/status"
        
        call = client.calls.create(
            from_=twilio_number,
            to=phone_number,
            url=twiml_url,
            method="POST",
            status_callback=status_callback_url,
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            status_callback_method="POST"
        )
        
        print(f"✅ Direct call initiated successfully!")
        print(f"📞 Call SID: {call.sid}")
        return call.sid
        
    except Exception as e:
        print(f"❌ Error making direct call: {e}")
        return None

if __name__ == "__main__":
    # Get phone number from environment or user input
    calling_number = os.environ.get("MY_NUMBER")
    
    if not calling_number:
        calling_number = input("Enter phone number to call (include country code, e.g., +1234567890): ")
    
    print(f"📞 Making interactive call to {calling_number}...")
    call_sid = make_interactive_call(calling_number)
    
    if call_sid:
        print("🎉 Call is connecting! You should receive a call shortly.")
        print("💬 When you answer, try saying things like:")
        print("   • 'Read my emails'")
        print("   • 'Check my calendar'")
        print("   • 'Help me with my tasks'")
    else:
        print("❌ Failed to initiate call. Please check your configuration.")



