from flask import Flask, jsonify, request, render_template
import json
from openai import AzureOpenAI
import os
import re

client = AzureOpenAI(
  azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), # type: ignore
  api_key=os.getenv("AZURE_OPENAI_KEY"),
  api_version="2023-12-01-preview"
)

app = Flask(__name__)

_limit = 100

tools = [
        {
            "type": "function",
            "function": {
                "name": "get_records_req_impl_by_year",
                "description": "Get the Business Request (BR) records that are due to be implemented by given year",
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
        },
        {
            "type": "function",
            "function": {
                "name": "get_br_count_with_target_impl_date",
                "description": "Get the amount of business records (BR) that have a valid (or not) target implementation date (TID). Returns an amount of BRs that matches the criteria",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "valid": {
                            "type": "boolean",
                            "description": "If we are checking for BRs with valid target implementation dates (TID) or not.",
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_forecasted_br_for_month",
                "description": "Get the Business Request (BR) records that are forecasted for a given month (and optionally a year, else uses the current year)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "month": {
                            "type": "string",
                            "description": "The month the Business Request (BR) is forecasted to be implemented in, e.g. April, March, Jun, Dec, FEB, etc.",
                        },
                        "year": {
                            "type": "string",
                            "description": "The year the Business Request (BR) is forecasted to be implemented in, e.g. 2024.",
                        }
                    },
                    "required": ["month"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_br_information",
                "description": "Gets information on a specific business request (BR) via it's BR number. It's a 5 or 6 digit number that can frequently be prepended by the letters BR, e.g. BR654321",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "br_number": {
                            "type": "integer",
                            "description": "The busines request (BR) number, it can consist of 5 or 6 digits, can sometimes be pre-pended by BR12345 for instance.",
                        },
                    },
                    "required": ["br_number"],
                },
            },
        },
    ]

# Load the records into memory from the file data/data.json
with open('data/data.json', 'r') as file:
    data = json.load(file)
    # Assuming there is only one element in the 'results' list
    records = data['results'][0]['items']

def pretty_print_br(json_br):
    return f"{json_br['br_number']} ({json_br['long_title']}) Required Implementation date: {json_br['req_implement_date']}, Forecasted Impl Date: {json_br['implement_target_date']}, Status: {json_br['status_name']}, Client name: {json_br['client_name']}"

def get_records_req_impl_by_year(year):
    """
    Required implementation date for BR
    """
    print("calling function to get records req implementation date.")
    # Extract the last two digits of the year
    year_suffix = '-' + year[2:]
    
    # Filter records that have a 'req_implement_date' ending with the specified year_suffix
    filtered_records = [record for record in records if record.get('req_implement_date', '').endswith(year_suffix)]
    
    # Return the filtered records as a JSON response
    return [pretty_print_br(br) for br in filtered_records[:_limit]]

def get_forecasted_br_for_month(month, year: str="2024"):
    """
    get the forcasted BRs information for a given month (and year)
    """
    print("calling BR forecast for month")
    # Extract the last two digits of the year
    year_suffix = '-' + year[2:]
    month_suffix = '-' + str.upper(month[:3])
    pattern = r"\b\d{2}"+ month_suffix + year_suffix + r"\b"
    filtered_records = [record for record in records if re.match(pattern, record['implement_target_date'])]
    
    # Return the filtered records as a JSON response
    return [pretty_print_br(br) for br in filtered_records[:_limit]]

def get_br_count_with_target_impl_date(valid: bool=True):
    """
    returns the BR counts of all the BRs with either a valid/invalid TID (target impl date)
    """
    print(f"checking VALID BRs ({valid}). Current total records to filter is {len(records)}")
    # Define the regex pattern  
    pattern = r"\b\d{2}-[A-Z]{3}-\d{2}\b"
    valid_records = 0
    not_valid_records = 0
    for record in records:
        if record['implement_target_date']:
            if re.match(pattern, record['implement_target_date']):
                valid_records += 1
            else:
                not_valid_records += 1
        else:
            not_valid_records += 1
    
    return valid_records if valid else not_valid_records

def get_br_information(br_number: int):
    """
    get information about a specific BR number
    """
    print(f"getting info for BR -> {br_number}")
    for record in records:
        if record['br_number'] == br_number:
            return pretty_print_br(record)
    # didn't find the record.
    return "Didn't find any matching Business Request (BR) matching that number."

@app.route('/chat', methods=['POST'])
def chat() -> str:
    data = request.get_json()
    content = data.get('content')
    messages = [
        {"role": "system", "content": "You are a Shared Services Canada (SSC) assistant that helps to find information about Business Request (BR) in the BITS system."},
        {"role": "user", "content": content}]

    response = client.chat.completions.create(
        model="gpt-4-1106",
        messages=messages, # type: ignore
        tools=tools, # type: ignore
        tool_choice="auto",  # auto is default, but we'll be explicit
    )
    response_message = response.choices[0].message

    tool_calls = response_message.tool_calls
    # Step 2: check if the model wanted to call a function
    if tool_calls:
        # Step 3: call the function
        # Note: the JSON response may not always be valid; be sure to handle errors
        available_functions = {
            "get_records_req_impl_by_year": get_records_req_impl_by_year,
            "get_br_count_with_target_impl_date": get_br_count_with_target_impl_date,
            "get_forecasted_br_for_month": get_forecasted_br_for_month,
            "get_br_information": get_br_information
        }

        # Step 4: send the info for each function call and function response to the model
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)

            # Prepare the arguments for the function call
            prepared_args = {}
            # Check if the function requires any arguments and add them to the prepared_args dictionary
            if "year" in function_args:
                prepared_args["year"] = function_args["year"]
            if "valid" in function_args:
                prepared_args["valid"] = function_args["valid"]
            if "month" in function_args:
                prepared_args["month"] = function_args["month"]
            if "br_number" in function_args:
                prepared_args["br_number"] = function_args["br_number"]
            
            # Call the function with the prepared arguments
            function_response = function_to_call(**prepared_args)
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
            response_as_string = "\n".join(function_response) if function_response is list else str(function_response)
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

@app.route('/')  
def index():  
    return render_template('index.html')  

if __name__ == '__main__':
    app.run(debug=True)