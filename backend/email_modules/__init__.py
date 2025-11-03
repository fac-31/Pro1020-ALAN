# Email client package initialization
from .connection import EmailConnection
from .parser import EmailParser
from .message_tracker import MessageTracker
from .reply_generator import ReplyGenerator
from .utils import clean_str, setup_utf8_encoding

__all__ = ['EmailConnection', 'EmailParser', 'MessageTracker', 'ReplyGenerator', 'clean_str', 'setup_utf8_encoding']
