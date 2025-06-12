"""
Post data model
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class PostStatus(Enum):
    """Post status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    SCHEDULED = "scheduled"
    FAILED = "failed"


class PostCategory(Enum):
    """Post category enumeration"""
    SNEAKERS = "sneakers"
    FASHION = "fashion"
    THOUGHTS = "thoughts"


@dataclass
class Post:
    """Post data model"""
    id: str
    title: str
    link: str
    source: str
    category: str = "sneakers"
    timestamp: str = ""
    
    # Content
    context: str = ""
    description: str = ""
    
    # Images
    images: List[str] = field(default_factory=list)
    original_images: List[str] = field(default_factory=list)
    generated_images: List[str] = field(default_factory=list)
    
    # Tags
    tags: Dict[str, List[str]] = field(default_factory=dict)
    
    # Status
    status: str = PostStatus.PENDING.value
    needs_parsing: bool = True
    
    # Scheduling
    scheduled_time: Optional[str] = None
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    published_at: Optional[str] = None
    
    # Analytics
    views: int = 0
    likes: int = 0
    
    def __post_init__(self):
        """Validate and normalize data after initialization"""
        # Ensure lists are lists
        if not isinstance(self.images, list):
            self.images = []
        if not isinstance(self.original_images, list):
            self.original_images = []
        if not isinstance(self.generated_images, list):
            self.generated_images = []
        
        # Ensure tags is a dict
        if not isinstance(self.tags, dict):
            self.tags = {}
        
        # Set timestamp if not provided
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        """Create Post from dictionary"""
        # Handle legacy field names
        if 'id' not in data and 'uid' in data:
            data['id'] = data['uid']
        
        # Extract only known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in known_fields}
        
        return cls(**filtered_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Post to dictionary"""
        data = {
            'id': self.id,
            'title': self.title,
            'link': self.link,
            'source': self.source,
            'category': self.category,
            'timestamp': self.timestamp,
            'context': self.context,
            'description': self.description,
            'images': self.images,
            'original_images': self.original_images,
            'generated_images': self.generated_images,
            'tags': self.tags,
            'status': self.status,
            'needs_parsing': self.needs_parsing,
            'scheduled_time': self.scheduled_time,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'published_at': self.published_at,
            'views': self.views,
            'likes': self.likes
        }
        
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}
    
    def to_json(self) -> str:
        """Convert Post to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Post':
        """Create Post from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.utcnow().isoformat()
    
    def mark_as_published(self):
        """Mark post as published"""
        self.status = PostStatus.PUBLISHED.value
        self.published_at = datetime.utcnow().isoformat()
        self.update_timestamp()
    
    def mark_as_scheduled(self, scheduled_time: datetime):
        """Mark post as scheduled"""
        self.status = PostStatus.SCHEDULED.value
        self.scheduled_time = scheduled_time.isoformat()
        self.update_timestamp()
    
    def add_generated_image(self, image_url: str):
        """Add generated image to post"""
        if image_url not in self.generated_images:
            self.generated_images.append(image_url)
            self.update_timestamp()
    
    def remove_generated_images(self):
        """Remove all generated images"""
        self.generated_images.clear()
        self.update_timestamp()
    
    def get_all_images(self) -> List[str]:
        """Get all images (generated + original)"""
        # Generated images take priority
        return self.generated_images + self.original_images
    
    def get_display_images(self, max_count: int = 10) -> List[str]:
        """Get images for display (limited count)"""
        all_images = self.get_all_images()
        return all_images[:max_count]
    
    def has_images(self) -> bool:
        """Check if post has any images"""
        return bool(self.images or self.original_images or self.generated_images)
    
    def get_hashtags(self) -> str:
        """Get hashtags for post"""
        from bot.utils.tags import get_hashtags
        return get_hashtags(self.title, self.category)
    
    def get_formatted_tags(self) -> str:
        """Get formatted tags for display"""
        from bot.utils.tags import format_tags_for_display
        return format_tags_for_display(self.tags)
    
    def get_age_days(self) -> int:
        """Get post age in days"""
        try:
            post_date = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            age = datetime.utcnow() - post_date.replace(tzinfo=None)
            return age.days
        except Exception as e:
            logger.error(f"Error calculating post age: {e}")
            return 0
    
    def is_old(self, max_age_days: int = 7) -> bool:
        """Check if post is too old"""
        return self.get_age_days() > max_age_days
    
    def get_preview_text(self, max_length: int = 200) -> str:
        """Get preview text for post"""
        text = self.description or self.context or self.title
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def __str__(self) -> str:
        """String representation"""
        return f"Post({self.id}, {self.title[:50]}..., {self.status})"
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return f"Post(id={self.id}, title={self.title[:30]}..., source={self.source}, status={self.status})"


@dataclass
class ThoughtPost(Post):
    """Special post type for thoughts/personal posts"""
    category: str = field(default=PostCategory.THOUGHTS.value)
    topic: str = ""
    image_description: str = ""
    is_personal: bool = True
    
    def __post_init__(self):
        """Initialize thought post"""
        super().__post_init__()
        self.category = PostCategory.THOUGHTS.value
        
        # Thoughts don't have links
        if not self.link:
            self.link = f"thought://{self.id}"


class PostCollection:
    """Collection of posts with helper methods"""
    
    def __init__(self):
        self.posts: Dict[str, Post] = {}
    
    def add(self, post: Post) -> None:
        """Add post to collection"""
        self.posts[post.id] = post
    
    def remove(self, post_id: str) -> Optional[Post]:
        """Remove post from collection"""
        return self.posts.pop(post_id, None)
    
    def get(self, post_id: str) -> Optional[Post]:
        """Get post by ID"""
        return self.posts.get(post_id)
    
    def get_all(self) -> List[Post]:
        """Get all posts"""
        return list(self.posts.values())
    
    def get_by_status(self, status: PostStatus) -> List[Post]:
        """Get posts by status"""
        return [p for p in self.posts.values() if p.status == status.value]
    
    def get_pending(self) -> List[Post]:
        """Get pending posts"""
        return self.get_by_status(PostStatus.PENDING)
    
    def get_scheduled(self) -> List[Post]:
        """Get scheduled posts"""
        return self.get_by_status(PostStatus.SCHEDULED)
    
    def get_by_source(self, source: str) -> List[Post]:
        """Get posts by source"""
        return [p for p in self.posts.values() if p.source == source]
    
    def get_by_category(self, category: str) -> List[Post]:
        """Get posts by category"""
        return [p for p in self.posts.values() if p.category == category]
    
    def get_recent(self, days: int = 1) -> List[Post]:
        """Get recent posts"""
        return [p for p in self.posts.values() if not p.is_old(days)]
    
    def clean_old(self, max_age_days: int = 7) -> int:
        """Remove old posts"""
        old_posts = [p.id for p in self.posts.values() if p.is_old(max_age_days)]
        for post_id in old_posts:
            self.remove(post_id)
        return len(old_posts)
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert collection to dictionary"""
        return {post_id: post.to_dict() for post_id, post in self.posts.items()}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Dict[str, Any]]) -> 'PostCollection':
        """Create collection from dictionary"""
        collection = cls()
        for post_id, post_data in data.items():
            try:
                post = Post.from_dict(post_data)
                collection.add(post)
            except Exception as e:
                logger.error(f"Error loading post {post_id}: {e}")
        return collection
    
    def __len__(self) -> int:
        """Get collection size"""
        return len(self.posts)
    
    def __contains__(self, post_id: str) -> bool:
        """Check if post exists in collection"""
        return post_id in self.posts
