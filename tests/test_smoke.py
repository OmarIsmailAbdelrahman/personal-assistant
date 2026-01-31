"""
Smoke test for the LangGraph Chat Backend.

This is a minimal test to verify the complete flow works:
1. Register user
2. Create conversation
3. Post message
4. Poll messages
5. Check run status

NOTE: This requires the API to be running (docker-compose up)
"""
import time
import httpx
import pytest


# Configuration
BASE_URL = "http://localhost:8000"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "testpass123"


@pytest.fixture
def client():
    """HTTP client for API calls"""
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


@pytest.fixture
def auth_token(client):
    """Register a test user and get auth token"""
    # Register
    response = client.post(
        "/v1/auth/register",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    
    # If user exists, login instead
    if response.status_code == 400:
        response = client.post(
            "/v1/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
    
    assert response.status_code in [200, 201]
    data = response.json()
    return data["access_token"]


def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_complete_flow(client, auth_token):
    """Test the complete message flow"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # 1. Create conversation
    response = client.post(
        "/v1/conversations",
        headers=headers,
        json={"title": "Test Conversation"}
    )
    assert response.status_code == 201
    conversation_id = response.json()["id"]
    print(f"Created conversation: {conversation_id}")
    
    # 2. Post message
    response = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={"text": "Hello, agent!"}
    )
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    print(f"Posted message, run_id: {run_id}")
    
    # 3. Check run status (wait for completion)
    max_attempts = 10
    for attempt in range(max_attempts):
        response = client.get(f"/v1/runs/{run_id}", headers=headers)
        assert response.status_code == 200
        
        status = response.json()["status"]
        print(f"Attempt {attempt + 1}: Run status = {status}")
        
        if status in ["succeeded", "failed"]:
            assert status == "succeeded", f"Run failed: {response.json().get('last_error')}"
            break
        
        time.sleep(2)
    else:
        pytest.fail(f"Run did not complete after {max_attempts} attempts")
    
    # 4. Poll messages
    response = client.get(
        f"/v1/conversations/{conversation_id}/messages",
        headers=headers
    )
    assert response.status_code == 200
    messages = response.json()
    
    # Should have user message + assistant response
    assert len(messages) >= 2
    assert messages[0]["sender"] == "user"
    assert messages[1]["sender"] == "assistant"
    
    print(f"Received {len(messages)} messages")
    print(f"Assistant response: {messages[1]['content_json']}")


def test_visualization_flow(client, auth_token):
    """Test message with visualization request"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Create conversation
    response = client.post(
        "/v1/conversations",
        headers=headers,
        json={"title": "Viz Test"}
    )
    conversation_id = response.json()["id"]
    
    # Post message with plot keyword
    response = client.post(
        f"/v1/conversations/{conversation_id}/messages",
        headers=headers,
        json={"text": "plot: create a chart"}
    )
    run_id = response.json()["run_id"]
    
    # Wait for completion
    for _ in range(10):
        response = client.get(f"/v1/runs/{run_id}", headers=headers)
        if response.json()["status"] in ["succeeded", "failed"]:
            break
        time.sleep(2)
    
    # Get messages
    response = client.get(
        f"/v1/conversations/{conversation_id}/messages",
        headers=headers
    )
    messages = response.json()
    
    # Should have user message + assistant text + assistant image
    assert len(messages) >= 3
    
    # Find image message
    image_messages = [m for m in messages if m["content_json"].get("type") == "image"]
    assert len(image_messages) >= 1
    
    # Get the image
    media_url = image_messages[0]["content_json"]["url"]
    media_id = media_url.split("/")[-1]
    
    response = client.get(f"/v1/media/{media_id}", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    
    print(f"Successfully retrieved image: {media_id}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
