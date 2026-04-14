import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from app.models import Base, User, SocialAccount, Video, Comment, Analysis, Insight, Question
    from app.schemas import (
        UserCreate, UserRead,
        SocialAccountCreate, SocialAccountRead,
        VideoCreate, VideoRead,
        CommentCreate, CommentRead,
        AnalysisCreate, AnalysisRead,
        InsightCreate, InsightRead,
        QuestionCreate, QuestionRead
    )
    print("Successfully imported all models and schemas!")
    
    # Check relationships (basic check)
    assert hasattr(User, "social_accounts")
    assert hasattr(Video, "comments")
    assert hasattr(Analysis, "insights")
    print("Relationship attributes verified.")
    
except Exception as e:
    print(f"Error during verification: {e}")
    sys.exit(1)
