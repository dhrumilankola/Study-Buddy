import requests
import json
import sseclient

def test_query():
    url = "http://localhost:8000/api/v1/query/"
    
    headers = {
        'Accept': 'text/event-stream',
        'Content-Type': 'application/json'
    }
    
    query = {
        "question": "What is this document about?",
        "context_window": 3
    }
    
    try:
        response = requests.post(url, json=query, headers=headers, stream=True)
        client = sseclient.SSEClient(response)
        
        for event in client.events():
            try:
                data = json.loads(event.data)
                if data["type"] == "response":
                    print(f"Response: {data['content']}")
                elif data["type"] == "error":
                    print(f"Error: {data['content']}")
                elif data["type"] == "done":
                    print("\nResponse complete.")
                    break
            except json.JSONDecodeError as e:
                print(f"Error parsing response: {e}")
                print(f"Raw data: {event.data}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'response' in locals():
            response.close()

if __name__ == "__main__":
    test_query()