#!/usr/bin/env python3
"""
Test script for MCP integration
"""

import asyncio
import httpx
from conversation_ai import ConversationAI, MCPClient

async def test_mcp_direct():
    """Test MCP client directly"""
    print("🧪 Testing MCP Client Direct Communication")
    print("=" * 50)
    
    client = MCPClient("http://localhost:3000")
    
    try:
        # Test initialize credentials
        print("1. Testing credential initialization...")
        result = await client.call_tool("initialize_creds", user_id="test_user")
        print(f"   Result: {result}")
        
        # Test get emails
        print("2. Testing email retrieval...")
        result = await client.call_tool("get_emails", user_id="test_user", max_emails=3)
        print(f"   Result: {result}")
        
        # Test current email reading (subject only)
        print("3. Testing current email reading (subject only)...")
        result = await client.call_tool("get_current_email_for_reading", user_id="test_user")
        print(f"   Result: {result}")
        
        # Test full email reading
        print("4. Testing full email reading...")
        result = await client.call_tool("read_full_current_email", user_id="test_user")
        print(f"   Result: {result[:200]}..." if len(result) > 200 else f"   Result: {result}")
        
        print("\n✅ MCP Direct Test Complete!")
        
    except Exception as e:
        print(f"❌ MCP Direct Test Failed: {e}")
    finally:
        await client.close()

async def test_conversation_ai():
    """Test ConversationAI with MCP integration"""
    print("\n🤖 Testing ConversationAI with MCP Integration")
    print("=" * 50)
    
    async with ConversationAI(user_id="test_user") as conv_ai:
        try:
            # Test greeting mode
            print("1. Testing greeting mode...")
            response = await conv_ai.process_user_input("read my emails")
            print(f"   Response: {response['tts_text'][:200]}...")
            print(f"   Action: {response['action']}")
            
            # Test email reading mode
            if response['action'] == 'start_email_reading':
                print("2. Testing email reading (subject only)...")
                email_text = await conv_ai.get_current_email_for_reading()
                print(f"   Email Subject: {email_text}")
                
                # Test reading full email (simulate user saying "yes")
                print("3. Testing full email reading (simulating 'yes' response)...")
                response = await conv_ai.process_user_input("yes, read it")
                print(f"   Response: {response['tts_text'][:200] if response['tts_text'] else 'None'}...")
                print(f"   Action: {response['action']}")
                
                # Test next email
                print("4. Testing next email...")
                response = await conv_ai.process_user_input("next")
                print(f"   Response: {response['tts_text']}")
                print(f"   Action: {response['action']}")
            
            print("\n✅ ConversationAI Test Complete!")
            
        except Exception as e:
            print(f"❌ ConversationAI Test Failed: {e}")

async def test_http_endpoint():
    """Test HTTP endpoint directly"""
    print("\n🌐 Testing HTTP Endpoint Direct")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        try:
            # Test health endpoint
            print("1. Testing health endpoint...")
            response = await client.get("http://localhost:3000/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            
            # Test tool call endpoint
            print("2. Testing tool call endpoint...")
            response = await client.post(
                "http://localhost:3000/call-tool",
                json={
                    "tool": "initialize_creds",
                    "arguments": {"user_id": "test_user"}
                }
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
            
            print("\n✅ HTTP Endpoint Test Complete!")
            
        except Exception as e:
            print(f"❌ HTTP Endpoint Test Failed: {e}")

async def main():
    """Run all tests"""
    print("🎯 MCP Integration Test Suite")
    print("=" * 50)
    print("Make sure the MCP server is running: python mcp_serve.py")
    print("=" * 50)
    
    await test_http_endpoint()
    await test_mcp_direct()
    await test_conversation_ai()
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 