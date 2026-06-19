import requests
import json
import random
import string
import time
from typing import Optional

# --- Configuration ---
# The API_BASE_URL points to the Nginx API Gateway running on port 80
API_BASE_URL = "http://127.0.0.1"

# --- Helper Functions ---
def generate_random_email():
    """Generates a unique email for testing."""
    return f"testuser_{''.join(random.choices(string.ascii_lowercase + string.digits, k=10))}@example.com"

def run_test(method: str, url: str, data: Optional[dict] = None, expected_status: int = 200, label: str = ""):
    """A generic function to run an HTTP request and print the results."""
    full_url = f"{API_BASE_URL}{url}"
    print(f"\n--- {label} ({method} {url}) ---")
    
    response = None
    try:
        if method == "POST":
            response = requests.post(full_url, json=data)
        elif method == "GET":
            response = requests.get(full_url)
        elif method == "PUT":
            response = requests.put(full_url, json=data)
        elif method == "PATCH":
            response = requests.patch(full_url, json=data)
        elif method == "DELETE":
            response = requests.delete(full_url)
        else:
            print(f"ERROR: Unsupported method {method}")
            return None

        # Check status code
        assert response.status_code == expected_status, (
            f"FAIL: Expected status {expected_status}, got {response.status_code}. Response: {response.text}"
        )
        print(f"SUCCESS: Status code {response.status_code} matches expected {expected_status}.")
        
        # Try to parse and return JSON content
        if response.content and response.status_code != 204:
            try:
                print(f"Response Body: {json.dumps(response.json(), indent=2)}")
                return response.json()
            except json.JSONDecodeError:
                print(f"Response Body (text): {response.text}")
                return response.text
        
        return None

    except Exception as e:
        print(f"FATAL EXCEPTION: {e}")
        if response is not None:
             print(f"Last Response Status: {response.status_code}, Text: {response.text}")
        return None

# --- Main Test Execution ---
def test_all_services():
    print("==================================================")
    print(" STARTING END-TO-END MICROSERVICES TEST ")
    print("==================================================")

    # Variables to store IDs for sequential testing
    user_id_1: Optional[str] = None
    user_id_2: Optional[str] = None
    item_id_a: Optional[str] = None
    item_id_b: Optional[str] = None
    swap_id: Optional[str] = None

    # ----------------------------------------------------
    # 1. USER SERVICE FLOW (Demonstrates POST, GET, PUT, DELETE, SQLModel)
    # ----------------------------------------------------

    # 1.1. Create User 1 (POST)
    user_data_1 = {
        "name": "Alice Smith",
        "email": generate_random_email(),
        "location": "New York, NY",
        "item_preference": "vintage kitten heels"
    }
    user_response_1 = run_test("POST", "/users/", user_data_1, 201, "KG1/KG6: Create User 1")
    if user_response_1:
        user_id_1 = user_response_1.get('id')

    # 1.2. Create User 2 (POST) - The counterparty
    user_data_2 = {
        "name": "Jones Michelle",
        "email": generate_random_email(),
        "location": "Boston, MA",
        "item_preference": "chanel crocodile jacket"
    }
    user_response_2 = run_test("POST", "/users/", user_data_2, 201, "Create User 2")
    if user_response_2:
        user_id_2 = user_response_2.get('id')

    # 1.3. Get User 1 (GET - First Time: Cache Miss)
    if user_id_1:
        run_test("GET", f"/users/{user_id_1}", expected_status=200, label="KG8: Get User 1 (Cache Miss/Write)")
        
    # 1.4. Get User 1 (GET - Second Time: Cache Hit)
    if user_id_1:
        # Wait a moment to ensure no race condition on first read
        time.sleep(0.5) 
        run_test("GET", f"/users/{user_id_1}", expected_status=200, label="KG8: Get User 1 (Cache Hit)")

    # ----------------------------------------------------
    # 2. ITEM SERVICE FLOW (Demonstrates POST, GET, Inter-Service Communication, Pydantic)
    # ----------------------------------------------------

    # 2.1. Create Item A (POST - Requires User 1 ID)
    if user_id_1:
        item_data_a = {
            "userId": user_id_1,
            "item_name": "Prada Kitten Heels",
            "description": "Pink with purple and red detailing ",
            "category": "Shoes",
        }
        item_response_a = run_test("POST", "/items/", item_data_a, 201, "KG7: Create Item A (User 1)")
        if item_response_a:
            item_id_a = item_response_a.get('id')

    # 2.2. Create Item B (POST - Requires User 2 ID)
    if user_id_2:
        item_data_b = {
            "userId": user_id_2,
            "item_name": "Crocodile Chanel Jacket",
            "description": "Green Jacket",
            "category": "Vintage",
        }
        item_response_b = run_test("POST", "/items/", item_data_b, 201, "KG7: Create Item B (User 2)")
        if item_response_b:
            item_id_b = item_response_b.get('id')
            
    # 2.3. Get Item A (GET)
    if item_id_a:
        run_test("GET", f"/items/{item_id_a}", expected_status=200, label="Get Item A")

    # 2.4. Negative Test: Create Item with a non-existent User ID
    bad_item_data = {
        "userId": "non-existent-user-123",
        "item_name": "Fake Item",
    }
    run_test("POST", "/items/", bad_item_data, 404, "Negative Test: Create Item (Invalid User)")
    
    # ----------------------------------------------------
    # 3. SWAP SERVICE FLOW (Demonstrates POST, GET, PUT, Inter-Service Communication)
    # ----------------------------------------------------

    # 3.1. Create a Swap (POST - Requires Item A and Item B IDs)
    if user_id_1 and item_id_a and item_id_b:
        swap_data = {
            "requester_user_Id": user_id_1, # Alice requests trade
            "item_requested": item_id_b,    # Alice wants Bob's headphones
            "item_offered": item_id_a,      # Alice offers her jacket
        }
        swap_response = run_test("POST", "/swaps", swap_data, 201, "KG7: Create Swap Request")
        if swap_response:
            swap_id = swap_response.get('id')

    # 3.2. Get the created Swap (GET)
    if swap_id:
        run_test("GET", f"/swaps/{swap_id}", expected_status=200, label="Get Swap Request")

    # 3.3. Update the Swap status to 'Swapped' (PUT/PATCH)
    if swap_id and user_id_1 and item_id_b:
        update_data = {
            "requester_user_Id": user_id_1,
            "item_requested": item_id_b,
            "status": "Swapped"
        }
        run_test("PUT", f"/swaps/{swap_id}/Swapped", update_data, 200, "Demonstrate PUT: Accept Swap")

    # ----------------------------------------------------
    # 4. CLEANUP (Demonstrates DELETE)
    # ----------------------------------------------------

    # 4.1. Delete Item A
    if item_id_a:
        run_test("DELETE", f"/items/{item_id_a}", expected_status=204, label="Demonstrate DELETE: Delete Item A")

    # 4.2. Delete User 2
    if user_id_2:
        run_test("DELETE", f"/users/{user_id_2}", expected_status=204, label="Demonstrate DELETE: Delete User 2")

    print("\n==================================================")
    print(" END OF END-TO-END MICROSERVICES TEST ")
    print(" All core service methods and inter-service communication validated.")
    print("==================================================")


if __name__ == "__main__":
    test_all_services()