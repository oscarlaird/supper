#%%
import json
with open('logs/conversation_2.txt', 'r') as f:
    content = f.read()
    if 'RESPONSE' in content:
        response_data = json.loads(content.split('RESPONSE\n')[1])
#%%
response_data
#%%
