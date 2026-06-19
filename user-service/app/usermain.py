from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional, Annotated, AsyncGenerator
from sqlmodel import SQLModel, Field, create_engine, Session, select
from contextlib import asynccontextmanager # New import for modern startup
import redis
import os
import uuid
import json
import logging 
import time 



# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("user-service")

#database setup 
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://user:password@user-db:5432/user_db")
engine = create_engine(DATABASE_URL, echo=False)
CACHE_EXPIRY_SECONDS = 300 # 5 minutes


#sqlModel def 
class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[str] = Field(default=None, primary_key=True, index=True)
    name: str
    email: str = Field(index=True, unique=True)
    location: str
    item_preference: str # For SQLModel only option 


#initalize database and tables in SQL Model
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

#session dependancy for database 
async def get_session() -> AsyncGenerator[Session, None]:
    with Session(engine) as session:
        yield session


#pydantic models request/response 
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    location: str
    item_preference:str 


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    location: str
    item_preference:str 



#redis client 
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)



# --- FastAPI Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # start.sh handles create_db_and_tables()
    
    print("Startup complete. Uvicorn is running application endpoints.")
    yield
    print("Shutdown complete.")

# --- FastAPI App Setup ---
app = FastAPI(lifespan=lifespan)




#health check 
@app.get("/health")
async def health_check():
     return {
        "service": "user-service",
        "status": "healthy",
        "dependencies": {}
    }



#endpoints 


#create user profile and save to databse 
@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, session: Annotated[Session, Depends(get_session)]):
    # generate ID
    db_user = User(**user_in.model_dump(), id=str(uuid.uuid4()))
    
    # Check for existing user
    existing_user = session.exec(select(User).where(User.email == db_user.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    try:
        # Add to session and commit 
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        logger.info(f"DB WRITE: Created user with ID: {db_user.id}") # Log DB write
   
        
       
        # Cache Write after db write 
        user_response = UserResponse(
            id=db_user.id,
            name=db_user.name,
            email=db_user.email,
            location=db_user.location,
            item_preference=db_user.item_preference
        )
        redis_client.setex(
            f"user:{db_user.id}", 
            CACHE_EXPIRY_SECONDS, 
            user_response.model_dump_json()
        )

        logger.info(f"CACHE WRITE: User {db_user.id} set in Redis.") # Log Cache write
        return user_response
        
    except Exception as e: # Catch 
        session.rollback()

        logger.error(f"FATAL DATABASE ERROR DURING CREATE for email {db_user.email}: {e}") # Log error

        raise HTTPException(status_code=500, detail=f"Database commit failed.")

#get user details 
@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, session: Annotated[Session, Depends(get_session)]):
#caching check -> cache hit 
    cache_key = f"user:{user_id}"
    cached_user = redis_client.get(cache_key)

    if cached_user:
        logger.info(f"CACHE HIT: User ID: {user_id}")
        return UserResponse.model_validate_json(cached_user)

    logger.info(f"CACHE MISS: User ID: {user_id}. Querying DB.")
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        logger.warning(f"User not found for ID: {user_id}")
        raise HTTPException(status_code=404, detail="User not found")
    

#cache write set into redis - convert json response model
    user_data = UserResponse.model_validate(user.model_dump()) 
    redis_client.setex(cache_key, CACHE_EXPIRY_SECONDS, json.dumps(user_data))
    logger.info(f"CACHE WRITE (miss resolution): User {user_id} set in Redis.")

    return UserResponse.model_validate(user)



#get all users 
@app.get("/users", response_model=list[UserResponse])
async def list_users(session: Annotated[Session, Depends(get_session)]):
    users = session.exec(select(User)).all()
    
    # SQLModel objects to Pydantic Response
    return [
        UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            location=user.location,
            item_preference=user.item_preference
        )
        for user in users
    ]

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, session: Annotated[Session, Depends(get_session)]):

    db_user = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        return
        
    session.delete(db_user)
    session.commit()
    
    # Remove from cache kg6
    redis_client.delete(f"user:{user_id}")
    
    return

