import pytest
from app.modules.comments.preprocessing import (
    clean_comment_text,
    is_emoji_or_noise,
    is_spam_or_promo,
    detect_lang,
    preprocess_comments_list
)

def test_clean_comment_text():
    # Test HTML removal
    assert clean_comment_text("This is <b>bold</b> text.") == "This is bold text."
    assert clean_comment_text("Line break<br>here.") == "Line break here."
    
    # Test URL removal
    assert clean_comment_text("Check https://google.com for details.") == "Check for details."
    assert clean_comment_text("Visit www.youtube.com/watch?v=123.") == "Visit"
    
    # Test space collapsing
    assert clean_comment_text("Too    many    spaces.") == "Too many spaces."
    assert clean_comment_text("Newlines\n\n\nand tabs\t\twork.") == "Newlines and tabs work."
    
    # Test unicode normalization
    # NFKC converts full-width characters to standard representation
    full_width = "Ｈｅｌｌｏ Ｗｏｒｌｄ"
    assert clean_comment_text(full_width) == "Hello World"
    
    # Empty string
    assert clean_comment_text("") == ""
    assert clean_comment_text(None) == ""

def test_is_emoji_or_noise():
    # Emoji-only should be True
    assert is_emoji_or_noise("😊🔥❤️") is True
    # Punctuation-only should be True
    assert is_emoji_or_noise("!!! ??? ...") is True
    # Mixed noise and emojis should be True
    assert is_emoji_or_noise("🔥!! ❤️") is True
    
    # Standard text should be False
    assert is_emoji_or_noise("Hello") is False
    assert is_emoji_or_noise("Hello 😊") is False
    assert is_emoji_or_noise("123") is False

def test_is_spam_or_promo():
    # Spam keyword checks
    assert is_spam_or_promo("Please subscribe to my channel!") is True
    assert is_spam_or_promo("Make money fast, guaranteed profit here") is True
    assert is_spam_or_promo("Contact me on telegram for crypto investment") is True
    
    # Regex pattern checks
    assert is_spam_or_promo("Join my t.me/doubler channel now") is True
    assert is_spam_or_promo("Call my whatsapp on +1 (234) 567-8901") is True
    assert is_spam_or_promo("My telegram: @helper_bot") is True
    
    # Legit comments
    assert is_spam_or_promo("This is the best tutorial on Next.js I have seen so far.") is False
    assert is_spam_or_promo("How do I connect the database in FastAPI?") is False

def test_detect_lang():
    assert detect_lang("This is a simple English comment.") == "en"
    assert detect_lang("Este es un comentario escrito en español.") == "es"
    assert detect_lang("C'est un comentario en français.") == "fr"
    # Punctuation / noise should return unknown
    assert detect_lang("!!!") == "unknown"

def test_preprocess_comments_list():
    comments = [
        # Normal English comment (Keep)
        {"id": 1, "text": "This is a very helpful tutorial on database migrations."},
        # HTML tag and URL in English comment (Keep but Clean)
        {"id": 2, "text": "Nice video! Check <b>FastAPI docs</b> at https://fastapi.tiangolo.com."},
        # Short comment (Filter: < 5 words)
        {"id": 3, "text": "Great tutorial!"},
        # Emoji only comment (Filter)
        {"id": 4, "text": "🔥🔥🔥😊😊😊"},
        # Spam comment (Filter)
        {"id": 5, "text": "Subscribe to my channel for doubling your crypto t.me/investor"},
        # Spanish comment (Filter: English only)
        {"id": 6, "text": "Muchas gracias por el video interactivo."},
        # Exact duplicate of comment 1 (Filter)
        {"id": 7, "text": "This is a very helpful tutorial on database migrations."},
        # Near-duplicate of comment 1 (Filter Jaccard similarity > 0.8)
        {"id": 8, "text": "This is a very helpful tutorial on database migrations indeed."}
    ]
    
    preprocessed = preprocess_comments_list(comments, english_only=True, min_words=5, similarity_threshold=0.8)
    
    # Should only keep comment 1 and comment 2 (cleaned)
    assert len(preprocessed) == 2
    
    # Verify ID 1 is kept with unchanged text (since it was already clean)
    assert preprocessed[0]["id"] == 1
    assert preprocessed[0]["text"] == "This is a very helpful tutorial on database migrations."
    
    # Verify ID 2 is kept and cleaned of HTML/URLs
    assert preprocessed[1]["id"] == 2
    assert preprocessed[1]["text"] == "Nice video! Check FastAPI docs at"
