import requests

# Replace with your actual IDs and Tokens
AD_ACCOUNT_ID = '848678964306043'
ACCESS_TOKEN = '5e2c6ee2420ad115a59b3b3baea7b94b'
API_VERSION = 'v20.0'

url = f"https://graph.facebook.com/{API_VERSION}/act_{AD_ACCOUNT_ID}/insights"
params = {
    'fields': 'campaign_name,spend,impressions,clicks',
    'time_range': '{"since":"2026-06-01","until":"2026-06-30"}',
    'level': 'campaign',
    'access_token': ACCESS_TOKEN
}

response = requests.get(url, params=params)
data = response.json()

print(data)