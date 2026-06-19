
NO NGINX YET 
Still Need to seperate the pytandic models into the models file. 

Sustainable Fashion Swapping 

Github: https://github.com/ellieelehmann/Sustainable-Fashion-Swapping

System Purpose: This Microservice allows users to post and swap secondhand items within their community. It promotes sustainable consumption by encouraging item exchange and tracks system health across services. 

Architecture Overview 
user-service: handles user registration and profile. 
Endpoints: 
Data: user name, email, location, item preference 
POST/users (create user profile) 
GET/users/{user_id} (get user details) 
GET/health (service health) 

item-service: clothing items available for exchange.
Data: item name,description, category, size, condition, image url 
Endpoints: 
POST/items (list new clothing item available for swap) 
GET/items (search for item)
DELETE/items/{item_id} (remove an item) 
GET/health (service health) 

swap-service: manages swap requests between users.
Data:requester id, item requested, item offered,status
Endpoints:
POST/swaps (create new swap request)
GET/swaps/{id}(check swap status)
PUT/swaps/{id}/complete(mark swap completed)
GET/health(health check)


Prerequisites: 
FASTAPI : asynch backend framework 
DOCKER: containers 
DOCKER COMPOSE: service orchestration 
NGINX: API gateway
REDIS:caching and health data storage 
PYTHON :programming language 
PYDANTIC: data validation/models
POSTGRES: database 

Installation & Setup: 

Clone repository: 
git clone <your-repo-url> 
cd fashion-swap

Build and start services with Docker: 
docker-compose up -d --build

Check all containers are running: 
docker ps 

Clean up: 
docker-compose down -v
docker container prune -f
docker volume prune -f


API Documentation: 
Health Endpoints

User-Serivce: 
curl http://localhost:8000/health 

Response: 
{
  "service": "user-service",
  "status": "healthy",
  "dependencies": {}
}

Item-Service: 
curl http://localhost:8001/health

Response: 
{
  "service": "item-service",
  "status": "healthy",
  "dependencies": {
    "user-service": {
      "status": "healthy",
      "response_time_ms": 13.4
    }
  }
}


Swap-Serivce: 
curl http://localhost:8002/health

Response: 
{
  "service": "swap-service",
  "status": "healthy",
  "dependencies": {
    "item-service": {
      "status": "healthy",
      "response_time_ms": 22.5
    }
  }
}


Test the system:
run in terminal: 

python3 test_system.py 

NGINX API GATEWAY:
Testing curl commands 
curl -i http://localhost/
curl -i http://localhost/users/health
curl -i http://localhost/items/health
curl -i http://localhost/swap/health

docker exec -it api-gateway sh
curl -i http://user-service:8000/health
curl -i http://item-service:8000/health
curl -i http://swap-service:8000/health

docker exec -it api-gateway nginx -t
docker logs api-gateway



Testing: 
Manual Testing: 
Service Health: 
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health


Project Structure:

MILESTONE1/
│
├── item-service/              
│   ├── app/
│   │   ├── main.py               # FastAPI app entry point for item service
│   │  
│   ├── Dockerfile                # Builds the item service container
│   └── requirements.txt         
│
├── swap-service/                 # Handles swap exchange logic between users
│   ├── app/
│   │   ├── main.py               # FastAPI app entry point for swap service
│   │ 
│   ├── Dockerfile                # Builds the swap service container
│   └── requirements.txt          # Python dependencies for the swap service
│
├── user-service/                 # Handles user registration and data
│   ├── app/
│   │   ├── main.py               # FastAPI app entry point for user service
│   │   
│   ├── Dockerfile                # Builds the user service container
│   └── requirements.txt          # Python dependencies for the user service
    |_______ start.sh              #starts the postgres db up and running
│
├── docker-compose.yml            # Orchestrates all three microservices
│
├── architecture-diagram.png      # Visual overview of the system architecture
│
│
├── README.md                     # Project documentation and setup guide
|----- nginx.conf                 #API Gateway and Loadbalancing of services 
│

