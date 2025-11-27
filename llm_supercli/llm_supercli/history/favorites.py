"""
Favorites management for llm_supercli.
Handles saving and organizing favorite sessions and messages.
"""
import json
import time
from dataclasses import dataclass
from typing import Optional

from .db import Database, get_database


@dataclass
class Favorite:
    """Represents a favorited item."""
    id: Optional[int]
    type: str  # 'session' or 'message'
    reference_id: str
    title: str
    notes: str
    created_at: float
    tags: list[str]
    
    @classmethod
    def from_row(cls, row: dict) -> 'Favorite':
        """Create Favorite from database row."""
        return cls(
            id=row['id'],
            type=row['type'],
            reference_id=row['reference_id'],
            title=row['title'],
            notes=row['notes'] or '',
            created_at=row['created_at'],
            tags=json.loads(row['tags']) if row['tags'] else []
        )


class FavoritesManager:
    """
    Manages favorite sessions and messages.
    
    Provides functionality for starring, tagging, and organizing favorites.
    """
    
    def __init__(self, db: Optional[Database] = None) -> None:
        """
        Initialize favorites manager.
        
        Args:
            db: Optional database instance
        """
        self._db = db or get_database()
    
    def add_favorite(
        self,
        item_type: str,
        reference_id: str,
        title: str = "",
        notes: str = "",
        tags: Optional[list[str]] = None
    ) -> Favorite:
        """
        Add an item to favorites.
        
        Args:
            item_type: Type of item ('session' or 'message')
            reference_id: ID of the item
            title: Display title
            notes: Optional notes
            tags: Optional tags
            
        Returns:
            Created Favorite object
        """
        tags = tags or []
        created_at = time.time()
        
        existing = self._db.fetch_one(
            "SELECT id FROM favorites WHERE type = ? AND reference_id = ?",
            (item_type, reference_id)
        )
        
        if existing:
            self._db.update(
                "favorites",
                {
                    "title": title,
                    "notes": notes,
                    "tags": json.dumps(tags)
                },
                "id = ?",
                (existing['id'],)
            )
            fav_id = existing['id']
        else:
            fav_id = self._db.insert("favorites", {
                "type": item_type,
                "reference_id": reference_id,
                "title": title,
                "notes": notes,
                "created_at": created_at,
                "tags": json.dumps(tags)
            })
        
        if item_type == "session":
            self._db.update(
                "sessions",
                {"is_favorite": 1},
                "id = ?",
                (reference_id,)
            )
        
        return Favorite(
            id=fav_id,
            type=item_type,
            reference_id=reference_id,
            title=title,
            notes=notes,
            created_at=created_at,
            tags=tags
        )
    
    def remove_favorite(self, item_type: str, reference_id: str) -> bool:
        """
        Remove an item from favorites.
        
        Args:
            item_type: Type of item
            reference_id: ID of the item
            
        Returns:
            True if removed
        """
        rows = self._db.delete(
            "favorites",
            "type = ? AND reference_id = ?",
            (item_type, reference_id)
        )
        
        if item_type == "session":
            self._db.update(
                "sessions",
                {"is_favorite": 0},
                "id = ?",
                (reference_id,)
            )
        
        return rows > 0
    
    def is_favorite(self, item_type: str, reference_id: str) -> bool:
        """
        Check if an item is favorited.
        
        Args:
            item_type: Type of item
            reference_id: ID of the item
            
        Returns:
            True if favorited
        """
        row = self._db.fetch_one(
            "SELECT id FROM favorites WHERE type = ? AND reference_id = ?",
            (item_type, reference_id)
        )
        return row is not None
    
    def get_favorite(self, item_type: str, reference_id: str) -> Optional[Favorite]:
        """
        Get a favorite by reference.
        
        Args:
            item_type: Type of item
            reference_id: ID of the item
            
        Returns:
            Favorite or None
        """
        row = self._db.fetch_one(
            "SELECT * FROM favorites WHERE type = ? AND reference_id = ?",
            (item_type, reference_id)
        )
        return Favorite.from_row(dict(row)) if row else None
    
    def list_favorites(
        self,
        item_type: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50
    ) -> list[Favorite]:
        """
        List favorites with optional filtering.
        
        Args:
            item_type: Optional type filter
            tag: Optional tag filter
            limit: Maximum results
            
        Returns:
            List of Favorite objects
        """
        query = "SELECT * FROM favorites"
        conditions = []
        params: list = []
        
        if item_type:
            conditions.append("type = ?")
            params.append(item_type)
        
        if tag:
            conditions.append("tags LIKE ?")
            params.append(f'%"{tag}"%')
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        rows = self._db.fetch_all(query, tuple(params))
        return [Favorite.from_row(dict(row)) for row in rows]
    
    def update_favorite(
        self,
        item_type: str,
        reference_id: str,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[list[str]] = None
    ) -> Optional[Favorite]:
        """
        Update a favorite's metadata.
        
        Args:
            item_type: Type of item
            reference_id: ID of the item
            title: New title (if provided)
            notes: New notes (if provided)
            tags: New tags (if provided)
            
        Returns:
            Updated Favorite or None if not found
        """
        existing = self.get_favorite(item_type, reference_id)
        if not existing:
            return None
        
        updates = {}
        if title is not None:
            updates["title"] = title
        if notes is not None:
            updates["notes"] = notes
        if tags is not None:
            updates["tags"] = json.dumps(tags)
        
        if updates:
            self._db.update(
                "favorites",
                updates,
                "type = ? AND reference_id = ?",
                (item_type, reference_id)
            )
        
        return self.get_favorite(item_type, reference_id)
    
    def add_tag(self, item_type: str, reference_id: str, tag: str) -> bool:
        """
        Add a tag to a favorite.
        
        Args:
            item_type: Type of item
            reference_id: ID of the item
            tag: Tag to add
            
        Returns:
            True if added
        """
        favorite = self.get_favorite(item_type, reference_id)
        if not favorite:
            return False
        
        if tag not in favorite.tags:
            favorite.tags.append(tag)
            self._db.update(
                "favorites",
                {"tags": json.dumps(favorite.tags)},
                "type = ? AND reference_id = ?",
                (item_type, reference_id)
            )
        
        return True
    
    def remove_tag(self, item_type: str, reference_id: str, tag: str) -> bool:
        """
        Remove a tag from a favorite.
        
        Args:
            item_type: Type of item
            reference_id: ID of the item
            tag: Tag to remove
            
        Returns:
            True if removed
        """
        favorite = self.get_favorite(item_type, reference_id)
        if not favorite or tag not in favorite.tags:
            return False
        
        favorite.tags.remove(tag)
        self._db.update(
            "favorites",
            {"tags": json.dumps(favorite.tags)},
            "type = ? AND reference_id = ?",
            (item_type, reference_id)
        )
        
        return True
    
    def get_all_tags(self) -> list[str]:
        """
        Get all unique tags.
        
        Returns:
            List of unique tags
        """
        rows = self._db.fetch_all("SELECT tags FROM favorites WHERE tags IS NOT NULL")
        all_tags = set()
        
        for row in rows:
            if row['tags']:
                tags = json.loads(row['tags'])
                all_tags.update(tags)
        
        return sorted(all_tags)
    
    def get_favorite_count(self, item_type: Optional[str] = None) -> int:
        """
        Get count of favorites.
        
        Args:
            item_type: Optional type filter
            
        Returns:
            Count of favorites
        """
        if item_type:
            row = self._db.fetch_one(
                "SELECT COUNT(*) as count FROM favorites WHERE type = ?",
                (item_type,)
            )
        else:
            row = self._db.fetch_one("SELECT COUNT(*) as count FROM favorites")
        
        return row['count'] if row else 0


_favorites_manager: Optional[FavoritesManager] = None


def get_favorites_manager() -> FavoritesManager:
    """Get the global favorites manager instance."""
    global _favorites_manager
    if _favorites_manager is None:
        _favorites_manager = FavoritesManager()
    return _favorites_manager
