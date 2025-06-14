from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid
import json

class UserProfile(BaseModel):
    id: Optional[uuid.UUID] = None
    user_id: str  # This will be the phone number
    username: str
    location: Optional[str] = None
    bio: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    embedding: Optional[List[float]] = Field(
        default=None,
        description="Vector embedding for similarity search",
        min_items=1536,
        max_items=1536
    )
    
    # Extended profile fields (these will be stored in the application logic
    # but not directly in the Supabase 'profiles' table)
    education: Optional[str] = None
    occupation: Optional[str] = None
    current_projects: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    
    def to_supabase_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,  # Phone number as user_id
            "username": self.username,
            "location": self.location,
            "bio": self.bio,
            "embedding": self.embedding,  # Include embedding in Supabase dict
        }
    
    @classmethod
    def from_supabase_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        return cls(**data)

class UserState(BaseModel):
    id: Optional[uuid.UUID] = None
    phone_number: str
    step: int = 0
    profile: Dict[str, Any] = Field(default_factory=dict)
    accumulated_messages: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_supabase_dict(self) -> Dict[str, Any]:
        return {
            "phone_number": self.phone_number,
            "step": self.step,
            "profile": json.dumps(self.profile),  # Convert dict to JSON string
            "accumulated_messages": json.dumps(self.accumulated_messages),  # Convert list to JSON string
            "updated_at": datetime.now(timezone.utc)
        }
    
    @classmethod
    def from_supabase_dict(cls, data: Dict[str, Any]) -> 'UserState':
        # Convert JSON strings back to Python objects
        if isinstance(data.get('profile'), str):
            data['profile'] = json.loads(data['profile'])
        if isinstance(data.get('accumulated_messages'), str):
            data['accumulated_messages'] = json.loads(data['accumulated_messages'])
        return cls(**data)

class UserConversation(BaseModel):
    id: Optional[uuid.UUID] = None
    user_id: str
    item_id: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    messages: List[Dict[str, Any]] = Field(default_factory=list)

class UserFeedback(BaseModel):
    id: Optional[uuid.UUID] = None
    user_id: str
    item_id: str
    feedback_type: str
    confidence: Optional[float] = None
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class UserRecommendation(BaseModel):
    user_id: str
    item_id: str
    recommended_score: Optional[float] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None

class Opportunity(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    type: Optional[str] = None
    deadline: Optional[datetime] = None
    state: Optional[str] = None
    city: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    embedding: Optional[List[float]] = Field(
        default=None,
        description="Vector embedding for similarity search",
        min_items=1536,
        max_items=1536
    )
    location: Optional[Dict[str, Any]] = None  # You can define a more specific type if needed

class SpatialRefSys(BaseModel):
    srid: int
    auth_name: Optional[str] = None
    auth_srid: Optional[int] = None
    srtext: Optional[str] = None
    proj4text: Optional[str] = None

class ConversationArchive(BaseModel):
    id: Optional[uuid.UUID] = None
    user_id: str
    item_id: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    messages: List[Dict[str, Any]] = Field(default_factory=list)

class RecentRecommendation(BaseModel):
    user_id: str
    recommendations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    created_at: Optional[datetime] = None