import json  
import os  
  
with open('data/data.json') as f:  
    data = json.load(f)  
  
os.makedirs('md_output', exist_ok=True)  
  
for i, item in enumerate(data['results'][0]['items']):
    br_number = item["br_number"]
    md_data = f"# BR {br_number}\n" + '\n'.join([f'**{k}**: {v}' for k, v in item.items()])
    with open(f'md_output/{br_number}.md', 'w') as f:
        f.write(md_data)
    #print(md_data)