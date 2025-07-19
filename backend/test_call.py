#!/usr/bin/env python3
"""
Test script for the Gmail Assistant Interactive Calling System
"""

import os
import sys
from dotenv import load_dotenv
from caller import make_interactive_call
import requests

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN', 
        'TWILIO_NUMBER',
        'OPENAI_API_KEY',
        'GOOGLE_PROJECT_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Please check your .env file and add these variables.")
        return False
    
    print("✅ All required environment variables are set!")
    return True

def check_server_running():
    """Check if the FastAPI server is running"""
    try:
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Server is running at {base_url}")
            return True
        else:
            print(f"⚠️  Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running!")
        print("💡 Please start the server with: python app.py")
        return False
    except Exception as e:
        print(f"❌ Error checking server: {e}")
        return False

def test_call():
    """Test making a call"""
    print("\n🎤 Gmail Assistant Interactive Calling Test")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv('.env.local')
    
    # Check environment
    if not check_environment():
        return False
    
    # Check server
    server_running = check_server_running()
    
    # Get phone number
    phone_number = os.getenv('MY_NUMBER')
    if not phone_number:
        phone_number = input("\n📞 Enter your phone number (with country code, e.g., +1234567890): ")
    
    if not phone_number:
        print("❌ No phone number provided!")
        return False
    
    # Ask for test mode
    if not server_running:
        print("\n⚠️  Server not running - enabling test mode automatically")
        test_mode = True
    else:
        test_choice = input("\n🧪 Use test mode? (y/n) [Test mode uses demo TwiML instead of webhooks]: ").lower()
        test_mode = test_choice.startswith('y')
    
    print(f"\n📞 Initiating call to {phone_number}...")
    
    if test_mode:
        print("🧪 Using TEST MODE (demo TwiML - will just say hello)")
    elif server_running:
        print("🚀 Using API server method with full assistant features...")
    else:
        print("⚠️  Using direct Twilio method (server not running)...")
    
    # Make the call
    call_sid = make_interactive_call(phone_number, test_mode=test_mode)
    
    if call_sid:
        print(f"\n🎉 SUCCESS! Call initiated with SID: {call_sid}")
        print("\n📱 You should receive a call shortly!")
        
        if test_mode:
            print("\n🧪 TEST MODE: The call will just play a demo message")
            print("💡 To use full features, set up ngrok and restart without test mode")
        else:
            print("\n💬 When you answer, try saying:")
            print("   • 'Hello' or 'Hi'")
            print("   • 'Read my emails'")
            print("   • 'Check my calendar'")
            print("   • 'Help me with tasks'")
            print("\n🔄 During email reading:")
            print("   • Say 'read it' to hear the full email")
            print("   • Say 'next' to skip to the next email")
            print("   • Say 'respond' to reply to an email")
            print("   • Say 'stop' to finish reading")
            print("\n✋ To end the call:")
            print("   • Say 'goodbye', 'bye', or 'done'")
        
        return True
    else:
        print("\n❌ FAILED to initiate call!")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check your Twilio credentials in .env")
        print("2. Make sure your Twilio number has voice capabilities")
        print("3. Verify your phone number format (+1234567890)")
        print("4. Check your Twilio account balance")
        
        if not server_running and not test_mode:
            print("5. Start the server: python app.py")
            print("6. Set up webhooks for production use")
        
        print("\n💡 For webhook issues, use ngrok or try test mode")
        
        return False

if __name__ == "__main__":
    try:
        success = test_call()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1) 