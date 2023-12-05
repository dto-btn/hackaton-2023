import json  
import os  
  
with open('data/data.json') as f:  
    data = json.load(f)  
  
os.makedirs('output', exist_ok=True)  
  
for i, item in enumerate(data['results'][0]['items']):
    with open(f'output/item_{i}.json', 'w') as f:
        json.dump(item, f)