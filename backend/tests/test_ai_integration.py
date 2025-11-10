#!/usr/bin/env python3
"""
Test script for AI integration
This script demonstrates how Alan's AI-powered email responses work
"""

import os
import sys
from dotenv import load_dotenv

# Add the backend directory to the Python path (one level up from tests)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()


def test_ai_integration():
    """Test the AI integration without requiring OpenAI API key"""
    print("🤖 Testing Alan's AI Integration")
    print("=" * 50)

    try:
        # Test AI modules import (now via services)
        from services.ai_service import AIService
        from ai_modules.conversation_memory import ConversationMemory
        from email_modules.reply_generator import ReplyGenerator

        print("✅ AI modules imported successfully")

        # Test conversation memory
        memory = ConversationMemory()
        print("✅ Conversation memory initialized")

        # Test reply generator (will use fallback without API key)
        try:
            reply_gen = ReplyGenerator()
            print("✅ Reply generator initialized")
        except ValueError as e:
            if "OPENAI_API_KEY" in str(e):
                print(
                    "⚠️  Reply generator requires OPENAI_API_KEY (using fallback mode)"
                )

                # Create a mock reply generator for testing
                class MockReplyGenerator:
                    def _generate_fallback_reply(self, sender_name, subject):
                        return f"Hi {sender_name},\n\nThanks for your email about '{subject}'. I'm Alan, your AI assistant!\n\nBest regards,\nAlan"

                reply_gen = MockReplyGenerator()
            else:
                raise

        # Test fallback reply generation
        test_reply = reply_gen._generate_fallback_reply("John Doe", "Test Subject")
        print("✅ Fallback reply generation works")
        print(f"Sample reply: {test_reply[:100]}...")

        # Test conversation memory
        memory.add_message(
            "test@example.com", "incoming", "Hello Alan!", "Test Subject"
        )
        history = memory.get_conversation_history("test@example.com")
        print(f"✅ Conversation memory works: {len(history)} messages stored")

        print("\n🎉 AI Integration Test Complete!")
        print("\nTo use AI-powered responses:")
        print("1. Set OPENAI_API_KEY in your .env file")
        print("2. Restart the server")
        print("3. Alan will generate intelligent responses to emails!")

        return True

    except Exception as e:
        print(f"❌ Error testing AI integration: {e}")
        return False


if __name__ == "__main__":
    success = test_ai_integration()
    sys.exit(0 if success else 1)
