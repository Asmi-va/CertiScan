from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

db = Database()

async def connect_to_mongo():
    """Create database connection and initialize collections."""
    logger.info("Connecting to MongoDB...")
    db.client = AsyncIOMotorClient(settings.MONGO_URL)
    db.db = db.client[settings.MONGO_DB_NAME]
    
    try:
        # Verify the connection
        await db.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Create collections and indexes
        await initialize_database()
        
    except ConnectionFailure:
        logger.error("Failed to connect to MongoDB")
        raise

async def initialize_database():
    """Initialize database collections and indexes."""
    from app.db.indexes import create_indexes
    
    # Create collections if they don't exist
    collections = await db.db.list_collection_names()
    required_collections = [
        "certificates", 
        "institutions", 
        "users",
        "verification_records", 
        "blacklist_entries",
        "certificate_templates",
        "audit_logs",
        "system_configs"
    ]
    
    for collection in required_collections:
        if collection not in collections:
            await db.db.create_collection(collection)
            logger.info(f"Created collection: {collection}")
    
    # Create indexes for optimal performance
    try:
        created_count, error_count = await create_indexes(db.db)
        if error_count > 0:
            logger.warning(f"Some indexes failed to create: {error_count} errors")
        else:
            logger.info(f"All indexes created successfully: {created_count} indexes")
    except Exception as e:
        logger.error(f"Failed to create indexes: {str(e)}")
        # Don't fail startup if index creation fails
        pass

async def close_mongo_connection():
    """Close database connection."""
    logger.info("Closing MongoDB connection...")
    if db.client:
        db.client.close()
        logger.info("MongoDB connection closed")

async def get_database():
    """Return database instance."""
    return db.db

# Helper functions for database operations
async def get_collection(collection_name: str):
    """Get a specific collection from the database."""
    return db.db[collection_name]