from flask import Flask, jsonify, request
import json
from openai import AzureOpenAI
import os

client = AzureOpenAI(
  azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), # type: ignore
  api_key=os.getenv("AZURE_OPENAI_KEY"),
  api_version="2023-12-01-preview"
)

app = Flask(__name__)

# Load the records into memory from the file data/data.json
with open('data/data.json', 'r') as file:
    data = json.load(file)
    # Assuming there is only one element in the 'results' list
    records = data['results'][0]['items']

def pretty_print_br(json_br):
    return f"{json_br['br_number']} ({json_br['long_title']}) Required Implementation date: {json_br['req_implement_date']}"

def get_records_implemented_by_year(year):
    print("calling function to get records by year implemented ...")
    # Extract the last two digits of the year
    year_suffix = '-' + year[2:]
    
    # Filter records that have a 'req_implement_date' ending with the specified year_suffix
    filtered_records = [record for record in records if record.get('req_implement_date', '').endswith(year_suffix)]
    
    # Return the filtered records as a JSON response
    return [pretty_print_br(br) for br in filtered_records[:10]]

@app.route('/implemented', methods=['GET'])
def get_records_by_year_api():
    '''
    just a fake API to mimick the BITs (BRs) system's API that is modifiable by their team so it should be 
    flexible enough to mimick the sort of request
    '''
    # Extract the year parameter from the query string
    year_suffix = request.args.get('year', '')
    
    # Validate if the year parameter is provided correctly
    if not year_suffix or len(year_suffix) != 4 or not year_suffix.isdigit():
        return jsonify({'error': 'Invalid year parameter. Please specify a 4-digit year.'}), 400
    
    # Return the filtered records as a JSON response
    return get_records_implemented_by_year(year_suffix)

@app.route('/chat', methods=['POST'])
def chat() -> str:
    data = request.get_json()
    content = data.get('content')
    messages = [{"role": "user", "content": content}]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_records_implemented_by_year",
                "description": "Get the Business Request (BR) records that were implemented in a given year",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "year": {
                            "type": "string",
                            "description": "The year the Business Request (BR) was implemented in, e.g. 2024.",
                        },
                    },
                    "required": ["year"],
                },
            },
        }
    ]
    response = client.chat.completions.create(
        model="gpt-4-1106",
        messages=messages, # type: ignore
        tools=tools, # type: ignore
        tool_choice="auto",  # auto is default, but we'll be explicit
    )
    response_message = response.choices[0].message
    print(response)
    tool_calls = response_message.tool_calls
    # Step 2: check if the model wanted to call a function
    if tool_calls:
        # Step 3: call the function
        # Note: the JSON response may not always be valid; be sure to handle errors
        available_functions = {
            "get_records_implemented_by_year": get_records_implemented_by_year,
        }  # only one function in this example, but you can have multiple
        # Append the assistant's response to the messages list  
        # Step 4: send the info for each function call and function response to the model
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            function_response = function_to_call(
                year=function_args.get("year"), # type: ignore
            ) 
            # Append a message to indicate the assistant is calling the function  
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": function_name,
                            "arguments": json.dumps(function_args)
                        }
                    }
                ]
            })
            response_as_string = "\n".join(function_response)
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": response_as_string,
                }
            )  # extend conversation with function response
        print(messages)
        second_response = client.chat.completions.create(
            model="gpt-4-1106",
            messages=messages, # type: ignore
        )  # get a new response from the model where it can see the function response
        return second_response.choices[0].message.content # type: ignore
    return response_message.content # type: ignore

if __name__ == '__main__':
    app.run(debug=True)

