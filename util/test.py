import openai, os, requests
from dotenv import load_dotenv

load_dotenv()

openai.api_type = "azure"
# Azure OpenAI on your own data is only supported by the 2023-08-01-preview API version
openai.api_version = "2023-08-01-preview"

# Azure OpenAI setup
openai.api_base = "https://scsc-cio-ect-hackaton-oai.openai.azure.com/" # Add your endpoint here # type: ignore
openai.api_key = os.getenv("OPENAI_API_KEY") # Add your OpenAI API key here
deployment_id = "gpt-4-32k" # Add your deployment ID here

# Azure AI Search setup
search_endpoint = "https://scsc-cio-ect-hackaton-ss.search.windows.net"; # Add your Azure AI Search endpoint here
search_key = os.getenv("SEARCH_KEY"); # Add your Azure AI Search admin key here
search_index_name = "demoall-index"; # Add your Azure AI Search index name here

def setup_byod(deployment_id: str) -> None:
    """Sets up the OpenAI Python SDK to use your own data for the chat endpoint.

    :param deployment_id: The deployment ID for the model to use with your own data.

    To remove this configuration, simply set openai.requestssession to None.
    """

    class BringYourOwnDataAdapter(requests.adapters.HTTPAdapter): # type: ignore

        def send(self, request, **kwargs):
            request.url = f"{openai.api_base}/openai/deployments/{deployment_id}/extensions/chat/completions?api-version={openai.api_version}" # type: ignore
            return super().send(request, **kwargs)

    session = requests.Session()

    # Mount a custom adapter which will use the extensions endpoint for any call using the given `deployment_id`
    session.mount(
        prefix=f"{openai.api_base}/openai/deployments/{deployment_id}", # type: ignore
        adapter=BringYourOwnDataAdapter()
    )

    openai.requestssession = session # type: ignore

setup_byod(deployment_id)


message_text = [{"role": "user", "content": "Give me a couple of client names from the records you have please, the top 10."}]

completion = openai.ChatCompletion.create( # type: ignore
    messages=message_text,
    deployment_id=deployment_id,
    dataSources=[  # camelCase is intentional, as this is the format the API expects
        {
            "type": "AzureCognitiveSearch",
            "parameters": {
                "endpoint": search_endpoint,
                "key": search_key,
                "indexName": search_index_name,
            }
        }
    ]
)
print(completion)