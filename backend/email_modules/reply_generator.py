from typing import List

class ReplyGenerator:
    def generate_reply(self, sender_name: str, subject: str, body: str) -> str:
        """Generate a simple reply message"""
        return f"""Hi {sender_name},

Thanks for your email about "{subject}". I'm Alan, your AI assistant, and I've received your message.

I'm currently in setup mode, but I'll be able to provide detailed, intelligent responses soon! 

Best regards,
Alan

---
Original message:
{body[:200]}{'...' if len(body) > 200 else ''}"""

    def generate_welcome_email(self, name: str, interests: List[str]) -> str:
        """Generate a welcome email for new subscribers"""
        return f"""Hi {name},

Thanks for subscribing! Your interests: {', '.join(interests)}.

Welcome aboard!

Best,
Alan"""
