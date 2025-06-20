#!/usr/bin/env python3
"""
Test script to verify the message saving and loading API endpoints.
"""

import asyncio
import logging
import sys
import os
import requests
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api/v1"

def test_message_api():
    """Test the message saving and loading API"""
    
    print("=== Testing Message API ===\n")
    
    # First, get available sessions
    print("1. Getting available sessions...")
    try:
        response = requests.get(f"{BASE_URL}/chat/sessions")
        response.raise_for_status()
        sessions = response.json()
        
        print(f"Found {len(sessions)} sessions:")
        for session in sessions:
            print(f"  - {session['session_uuid']}: {session['title']} ({session['total_messages']} messages)")
        
        if not sessions:
            print("No sessions found! Please create a session first.")
            return
        
        # Use the first session for testing
        test_session = sessions[0]
        session_uuid = test_session['session_uuid']
        print(f"\nUsing session: {session_uuid}")
        
    except Exception as e:
        print(f"Error getting sessions: {e}")
        return
    
    # Test saving a message
    print("\n2. Testing message saving...")
    test_message = {
        "message_content": "Test question from API test",
        "response_content": "Test response from API test",
        "model_provider": "gemini",
        "token_count": 100,
        "processing_time_ms": 1500
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat/sessions/{session_uuid}/messages",
            json=test_message
        )
        response.raise_for_status()
        saved_message = response.json()
        
        print("✅ Message saved successfully:")
        print(f"   ID: {saved_message['id']}")
        print(f"   Content: {saved_message['message_content']}")
        print(f"   Response: {saved_message['response_content']}")
        print(f"   Provider: {saved_message['model_provider']}")
        
    except Exception as e:
        print(f"❌ Error saving message: {e}")
        if hasattr(e, 'response'):
            print(f"   Response: {e.response.text}")
        return
    
    # Test loading messages
    print("\n3. Testing message loading...")
    try:
        response = requests.get(f"{BASE_URL}/chat/sessions/{session_uuid}/messages")
        response.raise_for_status()
        messages = response.json()
        
        print(f"✅ Loaded {len(messages)} messages:")
        for i, msg in enumerate(messages):
            print(f"   {i+1}. {msg['message_content'][:50]}... -> {msg['response_content'][:50] if msg['response_content'] else 'No response'}...")
        
    except Exception as e:
        print(f"❌ Error loading messages: {e}")
        if hasattr(e, 'response'):
            print(f"   Response: {e.response.text}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_message_api()
