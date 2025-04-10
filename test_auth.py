import requests
import base64

url = "https://sns-ai-profile-app-tunnel-a9zuz3y7.devinapps.com"

username = "user"
password = "f047be9dc32d4a76824fcbf63823398d"

auth_string = f"{username}:{password}"
auth_bytes = auth_string.encode('ascii')
auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
headers = {'Authorization': f'Basic {auth_b64}'}

print(f"Testing authentication with URL: {url}")
print(f"Using credentials - Username: {username}, Password: {password}")
print(f"Authorization header: {headers['Authorization']}")

response = requests.get(url, headers=headers)
print(f"Response status code: {response.status_code}")
print(f"Response headers: {response.headers}")
print(f"Response content: {response.text[:200]}...")  # Show first 200 chars of response

print("\nTesting without authentication:")
response_no_auth = requests.get(url)
print(f"Response status code: {response_no_auth.status_code}")
