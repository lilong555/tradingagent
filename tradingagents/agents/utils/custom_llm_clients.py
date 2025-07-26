import requests
import logging
import json
import uuid
import time
from langchain_core.messages import AIMessage, ToolCall

class CustomGoogleGenAIClient:
    """
    A custom client to communicate directly with the Google Generative AI API,
    with basic support for tool calling. It returns standard LangChain message objects.
    """
    def __init__(self, model: str, api_key: str):
        """
        Initializes the client.
        Args:
            model (str): The name of the model to use (e.g., "gemini-1.5-flash").
            api_key (str): The Google AI API key.
        """
        if not api_key:
            raise ValueError("Google API key is required.")
        self.model = model
        self.api_key = api_key
        self.base_url = "https://pslscrosyutd.ap-northeast-1.clawcloudrun.com/v1beta/models"
        self.tools = None

    def bind_tools(self, tools: list):
        """
        Formats and binds a list of LangChain tools for use with the Google API.
        Args:
            tools (list): A list of LangChain tool objects.
        Returns:
            self: The client instance for chaining.
        """
        if not tools:
            return self
        
        function_declarations = []
        for tool in tools:
            if not hasattr(tool, 'name') or not hasattr(tool, 'description') or not hasattr(tool, 'args_schema'):
                logging.warning(f"Tool {tool} is missing required attributes (name, description, args_schema). Skipping.")
                continue

            schema = tool.args_schema.schema()
            function_declarations.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", []),
                }
            })
        
        # The API expects a list containing a single tool object, which in turn contains the list of function declarations.
        self.tools = [{"functionDeclarations": function_declarations}]
        logging.info(f"Bound {len(function_declarations)} tools to the client.")
        logging.debug(f"Formatted tools for Google API: {json.dumps(self.tools, indent=2)}")
        return self

    def invoke(self, messages: list) -> AIMessage:
        """
        Sends a list of messages to the Google Generative AI API and gets a response.
        Args:
            messages (list): A list of LangChain message objects.
        Returns:
            AIMessage: A standard LangChain AIMessage object.
        """
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        # Convert LangChain messages to Google's content format
        contents = []
        for msg in messages:
            role = "user" # Default role
            if msg.type == "human" or msg.type == "system":
                role = "user"
                parts = [{"text": msg.content}]
            elif msg.type == "ai":
                role = "model"
                if msg.tool_calls:
                    parts = [{"functionCall": {"name": tc.get("name"), "args": tc.get("args")}} for tc in msg.tool_calls]
                else:
                    parts = [{"text": msg.content}]
            elif msg.type == "tool":
                role = "user"  # In Google's API, tool responses are sent with the 'user' role
                parts = [{
                    "functionResponse": {
                        "name": msg.name,
                        "response": {
                            "name": msg.name,
                            "content": msg.content,
                        },
                    }
                }]
            else:
                logging.warning(f"Unsupported message type: {msg.type}. Skipping.")
                continue
            
            contents.append({"role": role, "parts": parts})

        payload = {"contents": contents}

        if self.tools:
            payload["tools"] = self.tools

        max_retries = 5
        base_delay = 1  # seconds
        for attempt in range(max_retries):
            try:
                logging.info(f"Sending request to Google AI API for model: {self.model} (Attempt {attempt + 1})")
                logging.debug(f"Request Payload to Google AI: {json.dumps(payload, indent=2)}")
                response = requests.post(url, headers=headers, json=payload, timeout=180)
                
                logging.debug(f"Google AI API Response Status: {response.status_code}")
                logging.debug(f"Google AI API Response Body: {response.text}")

                response.raise_for_status()
                
                data = response.json()
                
                # Check for tool calls in the response
                first_candidate = data.get("candidates", [{}])[0]
                first_part = first_candidate.get("content", {}).get("parts", [{}])[0]

                if "functionCall" in first_part:
                    tool_call_data = first_part["functionCall"]
                    tool_name = tool_call_data.get("name")
                    tool_args = tool_call_data.get("args", {})
                    tool_id = f"tool_{uuid.uuid4().hex}"
                    
                    logging.info(f"Google AI model requested to call tool: {tool_name} with args: {tool_args}")
                    
                    tool_call = ToolCall(name=tool_name, args=tool_args, id=tool_id)
                    return AIMessage(content="", tool_calls=[tool_call])

                # Otherwise, get the text content
                content = first_part.get("text", "")
                logging.info("Successfully received text response from Google AI API.")
                return AIMessage(content=content)

            except requests.exceptions.RequestException as e:
                logging.warning(f"Attempt {attempt + 1} of {max_retries} failed with connection error: {e}")
                if attempt + 1 == max_retries:
                    logging.error(f"Final attempt failed. Error calling Google AI API: {e}")
                    return AIMessage(content=f"Error: Could not get response from Google AI. Details: {e}")
            except (KeyError, IndexError, requests.exceptions.HTTPError) as e:
                logging.warning(f"Attempt {attempt + 1} of {max_retries} failed with HTTP/parsing error: {e}")
                if attempt + 1 == max_retries:
                    logging.error(f"Final attempt failed. Error processing Google AI API response: {response.text if 'response' in locals() else 'No response'}")
                    return AIMessage(content="Error: Could not parse the response from Google AI.")
            
            # Incremental backoff
            delay = base_delay * (attempt + 1)
            logging.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)
