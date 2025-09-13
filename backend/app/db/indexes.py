"""
Database indexes for optimal query performance.
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Index definitions for each collection
INDEXES = {
    "certificates": [
        # Primary lookup indexes
        {"keys": [("certificate_id", 1)], "unique": True},
        {"keys": [("certificate_number", 1)], "unique": True},
        {"keys": [("file_hash", 1)]},
        
        # Search and filter indexes
        {"keys": [("institution_id", 1), ("verification_status", 1)]},
        {"keys": [("student_name", 1), ("roll_number", 1)]},
        {"keys": [("course_name", 1), ("degree_type", 1)]},
        {"keys": [("graduation_date", -1)]},
        {"keys": [("issue_date", -1)]},
        {"keys": [("created_at", -1)]},
        {"keys": [("verification_score", -1)]},
        
        # Compound indexes for common queries
        {"keys": [("institution_id", 1), ("graduation_date", -1)]},
        {"keys": [("verification_status", 1), ("verification_score", -1)]},
        {"keys": [("student_name", 1), ("institution_id", 1)]},
        
        # Text search index
        {"keys": [("student_name", "text"), ("course_name", "text"), ("certificate_number", "text")]},
    ],
    
    "institutions": [
        # Primary lookup indexes
        {"keys": [("institution_id", 1)], "unique": True},
        {"keys": [("name", 1)]},
        
        # Filter indexes
        {"keys": [("type", 1), ("is_active", 1)]},
        {"keys": [("accreditation_status", 1)]},
        {"keys": [("verification_enabled", 1)]},
        {"keys": [("created_at", -1)]},
        
        # Text search index
        {"keys": [("name", "text"), ("short_name", "text")]},
    ],
    
    "users": [
        # Primary lookup indexes
        {"keys": [("user_id", 1)], "unique": True},
        {"keys": [("email", 1)], "unique": True},
        
        # Filter indexes
        {"keys": [("role", 1), ("is_active", 1)]},
        {"keys": [("institution_id", 1)]},
        {"keys": [("organization", 1)]},
        {"keys": [("is_verified", 1)]},
        {"keys": [("last_login", -1)]},
        {"keys": [("created_at", -1)]},
        
        # Security indexes
        {"keys": [("failed_login_attempts", 1)]},
        {"keys": [("locked_until", 1)]},
    ],
    
    "verification_records": [
        # Primary lookup indexes
        {"keys": [("verification_id", 1)], "unique": True},
        {"keys": [("certificate_id", 1)]},
        
        # Filter indexes
        {"keys": [("requester_id", 1), ("verification_date", -1)]},
        {"keys": [("requester_type", 1)]},
        {"keys": [("status", 1)]},
        {"keys": [("verification_date", -1)]},
        {"keys": [("confidence_score", -1)]},
        
        # Compound indexes for analytics
        {"keys": [("certificate_id", 1), ("verification_date", -1)]},
        {"keys": [("requester_type", 1), ("status", 1)]},
        {"keys": [("verification_date", -1), ("status", 1)]},
        
        # Performance indexes
        {"keys": [("processing_time", -1)]},
        {"keys": [("ip_address", 1)]},
    ],
    
    "blacklist_entries": [
        # Primary lookup indexes
        {"keys": [("entry_id", 1)], "unique": True},
        {"keys": [("identifier", 1), ("type", 1)]},
        
        # Filter indexes
        {"keys": [("type", 1), ("status", 1)]},
        {"keys": [("status", 1)]},
        {"keys": [("severity", 1)]},
        {"keys": [("created_at", -1)]},
        {"keys": [("expires_at", 1)]},
        
        # Administrative indexes
        {"keys": [("reported_by", 1)]},
        {"keys": [("reviewed_by", 1)]},
        {"keys": [("approved_by", 1)]},
        
        # Compound indexes
        {"keys": [("type", 1), ("status", 1), ("severity", 1)]},
    ],
    
    "certificate_templates": [
        # Primary lookup indexes
        {"keys": [("template_id", 1)], "unique": True},
        {"keys": [("institution_id", 1), ("is_active", 1)]},
        
        # Filter indexes
        {"keys": [("name", 1)]},
        {"keys": [("version", 1)]},
        {"keys": [("created_at", -1)]},
    ],
    
    "audit_logs": [
        # Primary lookup indexes
        {"keys": [("log_id", 1)], "unique": True},
        
        # Filter indexes
        {"keys": [("user_id", 1), ("timestamp", -1)]},
        {"keys": [("action", 1)]},
        {"keys": [("resource_type", 1), ("resource_id", 1)]},
        {"keys": [("timestamp", -1)]},
        
        # Compound indexes for queries
        {"keys": [("resource_type", 1), ("action", 1)]},
        {"keys": [("user_id", 1), ("action", 1)]},
        
        # TTL index for log retention (30 days)
        {"keys": [("timestamp", 1)], "expireAfterSeconds": 2592000},
    ],
    
    "system_configs": [
        # Primary lookup indexes
        {"keys": [("config_id", 1)], "unique": True},
        {"keys": [("category", 1), ("key", 1)], "unique": True},
        
        # Filter indexes
        {"keys": [("category", 1)]},
        {"keys": [("is_system", 1)]},
        {"keys": [("is_sensitive", 1)]},
    ],
}

async def create_indexes(database):
    """Create all database indexes."""
    logger.info("Creating database indexes...")
    
    created_count = 0
    error_count = 0
    
    for collection_name, indexes in INDEXES.items():
        collection = database[collection_name]
        
        for index_def in indexes:
            try:
                keys = index_def["keys"]
                options = {k: v for k, v in index_def.items() if k != "keys"}
                
                # Create the index
                await collection.create_index(keys, **options)
                created_count += 1
                
                logger.debug(f"Created index on {collection_name}: {keys}")
                
            except Exception as e:
                logger.error(f"Failed to create index on {collection_name}: {keys} - {str(e)}")
                error_count += 1
    
    logger.info(f"Index creation completed: {created_count} created, {error_count} errors")
    return created_count, error_count

async def drop_indexes(database, collection_name: str = None):
    """Drop indexes for a specific collection or all collections."""
    if collection_name:
        collections = [collection_name]
    else:
        collections = INDEXES.keys()
    
    dropped_count = 0
    
    for coll_name in collections:
        try:
            collection = database[coll_name]
            await collection.drop_indexes()
            dropped_count += 1
            logger.info(f"Dropped indexes for collection: {coll_name}")
        except Exception as e:
            logger.error(f"Failed to drop indexes for {coll_name}: {str(e)}")
    
    return dropped_count

async def list_indexes(database, collection_name: str) -> List[Dict[str, Any]]:
    """List all indexes for a specific collection."""
    try:
        collection = database[collection_name]
        indexes = []
        
        async for index in collection.list_indexes():
            indexes.append(index)
        
        return indexes
    except Exception as e:
        logger.error(f"Failed to list indexes for {collection_name}: {str(e)}")
        return []

async def get_index_stats(database) -> Dict[str, Any]:
    """Get index statistics for all collections."""
    stats = {}
    
    for collection_name in INDEXES.keys():
        try:
            collection = database[collection_name]
            
            # Get collection stats
            coll_stats = await database.command("collStats", collection_name)
            
            # Get index information
            indexes = await list_indexes(database, collection_name)
            
            stats[collection_name] = {
                "document_count": coll_stats.get("count", 0),
                "index_count": len(indexes),
                "total_index_size": coll_stats.get("totalIndexSize", 0),
                "indexes": [
                    {
                        "name": idx.get("name"),
                        "keys": idx.get("key"),
                        "unique": idx.get("unique", False),
                        "sparse": idx.get("sparse", False)
                    }
                    for idx in indexes
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get stats for {collection_name}: {str(e)}")
            stats[collection_name] = {"error": str(e)}
    
    return stats