import requests
import json

url = "https://graphql.bitquery.io"

payload = json.dumps({
   "query": "query MyQuery {\n  bitcoin {\n    transactions(any: {txHash: {is: \"d41f5de48325e79070ccd3a23005f7a3b405f3ce1faa4df09f6d71770497e9d5\"}})\n  }\n}\n",
   "variables": "{}"
})
headers = {
   'Content-Type': 'application/json',
   'X-API-KEY': 'BQYcBUTsyvgrFrO7ASNpXOohdv6dwTGC'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
