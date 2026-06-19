from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Literal
import redis
import httpx
import time 
import os
from fastapi.responses import JSONResponse
import uuid
from datetime import datetime
import json
import logging


# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("item-service")

app = FastAPI()

# Redis connection
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# External user service base (for validating userId on create/update)
USER_SERVICE_BASE = os.getenv("USER_SERVICE_BASE", "http://user-service:8000")


class ItemCreate(BaseModel):
    userId: str
    item_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    image_url: Optional[str] = None

class ItemResponse(BaseModel):
    id: str
    userId: str
    item_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    image_url: Optional[str] = None
    


@app.get("/health")
async def health_check():
    dependencies = {}
    #connect to user service to which item service is dependant on 
    user_service_url = f"{USER_SERVICE_BASE}/health"
    start_time = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(user_service_url)
        elapsed = (time.perf_counter() - start_time) * 1000 #count reponse time 
        if response.status_code == 200 and response.json().get("status") == "healthy":
            dependencies["user-service"] = {
                "status": "healthy",
                "response_time_ms": round(elapsed, 2)
            }
            status = "healthy"
            status_code = 200
        else:
            dependencies["user-service"] = {
                "status": "unhealthy",
                "response_time_ms": round(elapsed, 2)
            }
            status = "unhealthy"
            status_code = 503

    except Exception as e: 
        elapsed = (time.perf_counter() - start_time) * 1000
        dependencies["user-service"] = {
            "status": "unhealthy",
            "response_time_ms": round(elapsed, 2),
            "error": str(e)
        }
        status = "unhealthy"
        status_code = 503


    return JSONResponse(
    status_code=status_code,
    content={
        "service": "item-service",
        "status": status,
        "dependencies": dependencies
    }
)

    

    


        

#Endpoints 
@app.post("/items", status_code=201, response_model=ItemResponse)
async def create_item(item: ItemCreate):

    #service communication validate user service it exists 
    user_url = f"{USER_SERVICE_BASE}/users/{item.userId}"
    logger.info(f"SERVICE COMMUNICATION: Validating userId {item.userId} via GET to {user_url}")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            user_response = await client.get(user_url)
        if user_response.status_code != 200:
            logger.warning(f"User validation failed for {item.userId}. Status: {user_response.status_code}")
            raise HTTPException(status_code=404, detail="User not found")
        logger.info(f"User validation successful for {item.userId}.")
    except Exception as e:
        logger.error(f"User service unavailable: {e}")
        raise HTTPException(status_code=503, detail="User service unavailable")

    #Create the item object
    item_id = str(uuid.uuid4())
    item_data = ItemResponse(
        id=item_id,
        userId=item.userId,
        item_name=item.item_name,
        description=item.description,
        category=item.category,
        size=item.size,
        condition=item.condition,
        image_url=item.image_url
    ).model_dump()

    #Save to Redis
    redis_client.set(f"item:{item_id}", json.dumps(item_data))
    redis_client.sadd(f"user_items:{item.userId}", item_id)
    logger.info(f"REDIS WRITE: Created item {item_id} for user {item.userId}.")

    return item_data
    

@app.get("/items/{id}", response_model=ItemResponse)
async def get_item(id: str):
    rawdata = redis_client.get(f"item:{id}")
    if not rawdata:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse.model_validate_json(rawdata)


@app.delete("/items/{id}", status_code=204)
async def delete_item(id: str):

    raw = redis_client.get(f"item:{id}") #build redis key
    if not raw: # cache miss
        return  

    item = ItemResponse.model_validate_json(raw)

    # remove from redis
    redis_client.delete(f"item:{id}")
    redis_client.srem(f"user_items:{item.userId}", id)

    return
