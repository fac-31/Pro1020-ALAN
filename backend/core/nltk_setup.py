import nltk
import logging

logger = logging.getLogger(__name__)

def setup_nltk_data():
    """
    Ensure that the NLTK 'punkt' tokenizer data is available (and download if missing).
    """
    resource = 'tokenizers/punkt/english.pickle'
    try:
        nltk.data.find(resource)
        logger.info(f"NLTK resource '{resource}' already available.")
    except LookupError:
        logger.info(f"NLTK resource '{resource}' not found. Downloading 'punkt'...")
        try:
            success = nltk.download('punkt', quiet=False)
            if not success:
                logger.error("NLTK download returned False — resource may not be available.")
            else:
                logger.info("NLTK 'punkt' tokenizer downloaded successfully.")
        except Exception as e:
            logger.error(f"Failed to download NLTK 'punkt' tokenizer: {e}")
            raise  # or handle appropriately
    except Exception as e:
        logger.error(f"Unexpected error during NLTK data setup: {e}")
        raise
