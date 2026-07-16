import re
import unicodedata
import logging
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# Set detector seed to ensure consistent language detection results
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)

# List of common comment spam and promotional keywords
SPAM_KEYWORDS = [
    "subscribe to",
    "my channel",
    "check out my",
    "giveaway",
    "free gift",
    "make money",
    "passive income",
    "earn $",
    "invest in",
    "forex",
    "crypto doubling",
    "guaranteed profit",
    "join my telegram",
    "whatsapp me",
    "contact me on",
    "text me on",
    "click the link",
    "best way to earn",
    "telegram:",
    "whatsapp:"
]

# Regex patterns for links, contact info, and bot signatures
SPAM_PATTERNS = [
    # Telegram handles
    r"t\.me/\w+",
    r"telegram\s*:\s*@?\w+",
    # WhatsApp / Phone numbers
    r"wa\.me/\d+",
    r"(?:whatsapp|ph|phone)\s*:\s*\+?\d+",
    # Generic phone number match (7-15 digits with common separators)
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
]

def clean_comment_text(text: str) -> str:
    """
    Cleans raw comment text:
    - Normalizes unicode characters using NFKC.
    - Strips HTML tags.
    - Strips URL links.
    - Collapses multiple whitespace characters and newlines into a single space.
    - Strips leading and trailing whitespaces.
    """
    if not text:
        return ""
    
    # 1. Unicode normalization (NFKC)
    cleaned = unicodedata.normalize("NFKC", text)
    
    # 2. Remove HTML tags (replace with space to prevent words from gluing together)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    
    # 3. Remove URLs
    cleaned = re.sub(r"https?://\S+|www\.\S+", " ", cleaned)
    
    # 4. Collapse spaces and newlines
    cleaned = re.sub(r"\s+", " ", cleaned)
    
    return cleaned.strip()

def is_emoji_or_noise(text: str) -> bool:
    """
    Checks if the comment contains only emojis, whitespace, and punctuation.
    Uses .isalnum() Unicode logic which returns False for emojis and punctuation.
    """
    return not any(char.isalnum() for char in text)

def is_spam_or_promo(text: str) -> bool:
    """
    Checks if the comment matches common spam/bot signatures or contains
    promotional call-to-actions.
    """
    text_lower = text.lower()
    
    # 1. Check for spam keywords
    for keyword in SPAM_KEYWORDS:
        if keyword in text_lower:
            return True
            
    # 2. Check for spam regex patterns
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text_lower):
            return True
            
    return False

def detect_lang(text: str) -> str:
    """
    Detects the language of the comment text using the langdetect library.
    Cathes and logs exceptions, returning 'unknown' as fallback.
    """
    # Exclude empty or punctuation-only strings from detection to avoid exceptions
    clean_alpha = "".join(c for c in text if c.isalnum())
    if not clean_alpha:
        return "unknown"
        
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"

def preprocess_comments_list(
    comments: list[dict], 
    english_only: bool = True, 
    min_words: int = 5,
    similarity_threshold: float = 0.8
) -> list[dict]:
    """
    Runs the full preprocessing and cleaning pipeline on a list of comments:
    1. Removes exact duplicates and filters out near-duplicates.
    2. Removes HTML tags, URLs, and collapses extra whitespaces.
    3. Filters out comments with less than `min_words` words.
    4. Filters out emoji-only / punctuation-only comments.
    5. Filters out promotional/bot spam.
    6. Filters out non-English comments (if `english_only=True`).
    """
    cleaned_comments = []
    accepted_word_sets = []
    
    for comment in comments:
        raw_text = comment.get("text", "")
        if not raw_text:
            continue
            
        # Step 2: Clean the comment text
        cleaned_text = clean_comment_text(raw_text)
        
        # Step 3: Filter out comments with less than min_words words
        words = [w for w in cleaned_text.split() if w]
        if len(words) < min_words:
            continue
            
        # Step 4: Filter out emoji-only or punctuation-only comments
        if is_emoji_or_noise(cleaned_text):
            continue
            
        # Step 5: Filter out spam and promotional text
        if is_spam_or_promo(cleaned_text):
            continue
            
        # Step 6: Filter out non-English comments if requested
        if english_only:
            lang = detect_lang(cleaned_text)
            if lang != "en":
                continue
                
        # Step 1: Deduplication (Exact and near-duplicates)
        # Strip punctuation from start/end of each word for clean token comparison
        words_set = set(re.sub(r"^\W+|\W+$", "", w.lower()) for w in words)
        words_set = {w for w in words_set if w}
        
        is_duplicate = False
        for seen_set in accepted_word_sets:
            # Jaccard similarity of word tokens
            intersection = words_set.intersection(seen_set)
            union = words_set.union(seen_set)
            jaccard = len(intersection) / len(union) if union else 0
            if jaccard >= similarity_threshold:
                is_duplicate = True
                break
                
        if not is_duplicate:
            # Return updated dictionary copy with cleaned text representation
            comment_copy = dict(comment)
            comment_copy["text"] = cleaned_text
            cleaned_comments.append(comment_copy)
            accepted_word_sets.append(words_set)
            
    return cleaned_comments
