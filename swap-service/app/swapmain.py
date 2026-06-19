from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Literal
import redis
import httpx
import os
import uuid
import time
from datetime import datetime
import json
import logging 


# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("swap-service")

app = FastAPI()

# Redis connection
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

# External user service base
ITEM_SERVICE_BASE = os.getenv("ITEM_SERVICE_BASE", "http://item-service:8000")

# Pydantic models
Status = Literal["Available","Requested","Swapped"]



class SwapCreate(BaseModel):
    requester_user_Id: str
    item_requested: str
    item_offered: str
    status: Status = "Requested"

class SwapUpdate(BaseModel):
    requester_user_Id: str
    item_requested: str
    status: Status = "Swapped"

class SwapResponse(BaseModel):
    id: str 
    requester_user_Id: str
    item_requested: str
    item_offered: str
    status: Status
    created_at: str

#Health 
@app.get("/health")
async def health_check():
 dependencies = {}
 item_service_url = f"{ITEM_SERVICE_BASE}/health"

 start_time = time.perf_counter()
 try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(item_service_url)
        elapsed = (time.perf_counter() - start_time) * 1000

        data = response.json()

        # Make sure data is a dict
        if isinstance(data, list):
            data = data[0]  # take first element if list
        elif not isinstance(data, dict):
            data = {}

        # Determine dependency status
        if response.status_code == 200 and data.get("status") == "healthy":
            dependencies["item-service"] = {
                "status": "healthy",
                "response_time_ms": round(elapsed, 2)
            }
            status = "healthy"
        else:
            dependencies["item-service"] = {
                "status": "unhealthy",
                "response_time_ms": round(elapsed, 2)
            }
            status = "unhealthy"

 except Exception as e:
        elapsed = (time.perf_counter() - start_time) * 1000
        dependencies["item-service"] = {
            "status": "unhealthy",
            "response_time_ms": round(elapsed, 2),
            "error": str(e)
        }
        status = "unhealthy"

 return {
        "service": "swap-service",
        "status": status,
        "dependencies": dependencies
    }


#Endpoints 
#manages the relationship between item-to-item exchanges between users

@app.post("/swaps", status_code=201, response_model=SwapResponse)
async def create_swap(swap: SwapCreate):

    # validate items exist in item service cross service communication 
    for item_id in [swap.item_requested, swap.item_offered]:
        item_url = f"{ITEM_SERVICE_BASE}/items/{item_id}"
        logger.info(f"SERVICE COMMUNICATION: Validating item {item_id} via GET to {item_url}")
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                item_response = await client.get(item_url)
            if item_response.status_code != 200:
                logger.warning(f"Item validation failed for {item_id}. Status: {item_response.status_code}")
                raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
            logger.info(f"Item validation successful for {item_id}.")
        except Exception as e:
            logger.error(f"Item service unavailable during validation: {e}")
            raise HTTPException(status_code=503, detail="Item service unavailable")

    swap_id = str(uuid.uuid4())
    swap_data = SwapResponse(
        id=swap_id,
        requester_user_Id=swap.requester_user_Id,
        item_requested=swap.item_requested,
        item_offered=swap.item_offered,
        status=swap.status,
        created_at=datetime.utcnow().isoformat()
    ).model_dump()

    redis_client.set(f"swap:{swap_id}", json.dumps(swap_data))
    logger.info(f"REDIS WRITE: Created swap {swap_id} (Item Requested: {swap.item_requested}, Item Offered: {swap.item_offered}).")

    return swap_data





#return swap details 
@app.get("/swaps/{id}", response_model=SwapResponse)
async def get_swap(id: str):
    raw = redis_client.get(f"swap:{id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Swap not found")
    return SwapResponse.model_validate_json(raw)


#where the trade happens 
@app.put("/swaps/{id}/Swapped", response_model=SwapResponse)
async def update_swap(id: str, updates: SwapUpdate):

    raw = redis_client.get(f"swap:{id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Swap not found")

    swap = SwapResponse.model_validate_json(raw)

    # Update fields
    swap.status = updates.status
    swap.item_requested = updates.item_requested

    redis_client.set(f"swap:{id}", swap.model_dump_json())

    return swap





@app.put("/swaps/{id}/reject", response_model=SwapResponse)
async def reject_swap(id: str):

    raw = redis_client.get(f"swap:{id}")
    if not raw:
        raise HTTPException(404, "Swap not found")

    swap = SwapResponse.model_validate_json(raw)

    # pending/requested swaps can be rejected not completed 
    if swap.status not in ["Requested"]:
        raise HTTPException(400, "Only requested swaps can be rejected")

    swap.status = "Rejected"

    redis_client.set(f"swap:{id}", swap.model_dump_json())

    return swap