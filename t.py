#%%
import asyncio
import nest_asyncio
nest_asyncio.apply()
from supabase.client import AsyncClient
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types import responses
import partial_json_parser
import json
import time
import tools
import prompts
from langchain_openai import ChatOpenAI
from browser_use import Agent
from browser_use import Browser
from browser_use import BrowserConfig
import asyncio
import nest_asyncio 
from dotenv import load_dotenv
import watchdog.events
import watchdog.observers

load_dotenv()
nest_asyncio.apply()
config = BrowserConfig(
    cdp_url="ws://0.0.0.0:9223/playwright?sessionId=4c44a102-1f6d-4e85-86ea-d049c40f5761"
    
)
browser = Browser(config=config)

# gpt-4o, ...
MODEL = "gpt-4o-mini"

# Load environment variables from .env file
load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = AsyncOpenAI(api_key=openai_api_key)

async def process_with_openai(supabase, message_content, username, chat_id, conversation_messages, workflow_steps, chat):
    """Process a message with OpenAI and stream the response"""
    print(f"Processing message with OpenAI: {message_content}")
    print("chat", chat)
    
    # Query OPENAI
    response = ""
    function_call_arguments = ""
    system_message_content = prompts.system_message_content_template.format()
    state_message_content = prompts.state_message_template.format(workflow_steps=workflow_steps, input_schema=chat["input_schema"], multi_input=chat["multi_input"])
    print("-"*100)
    print("SYSTEM_PROMPT\n", system_message_content)
    print("-"*100)
    print("STATE_PROMPT\n", state_message_content)
    print("-"*100)
    system_message = {"role": "system", "content": system_message_content}
    state_message = {"role": "user", "content": state_message_content}
    previous_messages = conversation_messages[:-1]
    last_user_message = conversation_messages[-1]
    stream = await client.responses.create(
        model=MODEL,
        input=[system_message, *previous_messages, state_message, last_user_message],
        stream=True,
        tools=tools.tools,
        tool_choice="auto",
        parallel_tool_calls=False,
    )
    
    # Create a new assistant message in the database
    # and get its id
    async def create_assistant_message(supabase_client, content=""):
        result = await supabase_client.table("messages").insert({
            "role": "assistant",
            "content": content,
            "chat_id": chat_id,
            "username": username,
            "is_currently_streaming": True
        }).execute()
        return result.data[0]["id"] if result.data else None
    
    # Update an existing assistant message
    async def update_assistant_message(supabase_client, message_id, update_data):
        try:
            result = await supabase_client.from_("messages").update(update_data,
                returning="representation").eq("id", message_id).execute()
            if not result.data:
                print(f"Update may have failed. Result: {result}")
        except Exception as e:
            print(f"Error updating message: {e}")

    async def add_workflow_step(supabase_client, step_number):
        result = await supabase_client.table("workflow_steps").insert({
            "step_number": step_number,
            "chat_id": chat_id,
            "status": "waiting",
            "title": "",
            "description": ""
        }).execute()
        if not result.data:
            print(f"Update may have failed. Result: {result}")
        return result.data[0]
    async def update_workflow_step(supabase_client, step_id, update_data):
        result = await supabase_client.table("workflow_steps").update(update_data).eq("id", step_id).execute()
        if not result.data:
            print(f"Update may have failed. Result: {result}")
    async def remove_workflow_step(supabase_client, step_id):
        print(f"Removing workflow step {step_id}")
        result = await supabase_client.table("workflow_steps").delete().eq("id", step_id).execute()
        if not result.data:
            print(f"Update may have failed. Result: {result}")
    async def set_multi_input(supabase_client, chat_id, multi_input):
        result = await supabase_client.table("chats").update({"multi_input": multi_input}).eq("id", chat_id).execute()
        if not result.data:
            print(f"Update may have failed. Result: {result}")
    async def change_input_fields(supabase_client, chat_id, input_schema):
        result = await supabase_client.table("chats").update({"input_schema": input_schema}).eq("id", chat_id).execute()
        if not result.data:
            print(f"Update may have failed. Result: {result}")
    
    # Create the initial assistant message
    assistant_message_id = await create_assistant_message(supabase)
    
    function_name = None
    new_step_created = False
    new_step_id = None
    async for event in stream:
        if type(event) == responses.response_output_item_added_event.ResponseOutputItemAddedEvent:
            item = event.item
            if item.type == "function_call":
                function_name = item.name
                print(f"Function name: {function_name}")
                update_data = {
                    "function_name": function_name
                }
                await update_assistant_message(supabase, assistant_message_id, update_data)
        # FUNCTION CALL DELTAS
        if event.type == "response.function_call_arguments.delta":
            delta = event.delta or ""  # stop token has delta=None?
            function_call_arguments += delta
            partial_call = partial_json_parser.loads(function_call_arguments)
            # ADD WORKFLOW STEP
            if function_name == "add_workflow_step":
                step_number_json_completed = "title" in partial_call
                if step_number_json_completed and not new_step_created:
                    new_step = await add_workflow_step(supabase, partial_call["step_number"])
                    new_step_created = True
                    new_step_id = new_step["id"]
                if new_step_created:
                    update_data = {
                        "title": partial_call["title"],
                        "description": partial_call["description"] if "description" in partial_call else ""
                    }
                    await update_workflow_step(supabase, new_step_id, update_data)
            # EDIT WORKFLOW STEP
            elif function_name == "edit_workflow_step":
                step_id_json_completed = "new_title" in partial_call or "new_description" in partial_call
                if step_id_json_completed:
                    update_data = {}
                    if "new_title" in partial_call and partial_call["new_title"] != "":
                        update_data["title"] = partial_call["new_title"]
                    if "new_description" in partial_call and partial_call["new_description"] != "":
                        update_data["description"] = partial_call["new_description"]
                    await update_workflow_step(supabase, partial_call["step_id"], update_data)
        # COMPLETE FUNCTION CALL
        if event.type == "response.function_call_arguments.done":
            print("Function call arguments done")
            print("function_name", function_name)
            if function_name == "remove_workflow_step":
                print("step_id", partial_call["step_id"])
                await remove_workflow_step(supabase, partial_call["step_id"])
                # await update_assistant_message(supabase, assistant_message_id, update_data)
            elif function_name == "set_multi_input":
                print("multi_input", partial_call["multi_input"])
                await set_multi_input(supabase, chat_id, partial_call["multi_input"])
            elif function_name == "change_input_fields":
                print("input_schema", partial_call["input_schema"])
                await change_input_fields(supabase, chat_id, partial_call["input_schema"])
        # TEXT RESPONSE DELTAS
        if event.type == "response.output_text.delta":
            # is_currently_streaming = chunk.choices[0].finish_reason is None
            is_currently_streaming = True
            content = event.delta or ""  # stop token has content=None
            response += content
            update_data = {
                "content": response,
                "is_currently_streaming": is_currently_streaming
            }
            await update_assistant_message(supabase, assistant_message_id, update_data)
    await update_assistant_message(supabase, assistant_message_id, {"is_currently_streaming": False})


    print("\nFull response:", response)
    return response

async def get_workflow_steps(supabase, chat_id):
    result = await supabase.table("workflow_steps").select("*").eq("chat_id", chat_id).order("step_number").execute()
    return result.data if result.data else []

async def main():
    # Instantiate the async client directly

    
    supabase = AsyncClient(supabase_url, supabase_key)
    await supabase.realtime.connect()
    
    # Define a callback for new record events
    async def on_new_record(payload):
        # Extract the message content from the payload
        try:
            record = payload['data']['record']
            print("PAYLOAD", payload)
            print("RECORD", record)
            # Check that it is a user message
            is_user_role = record['role'] == "user"
            is_system_user = record['username'] == "system"
            is_from_template = record['from_template'] == True
            has_content = 'content' in record and record['content']
            should_respond = is_user_role and not is_system_user and not is_from_template and has_content
            if should_respond:
                username = record['username']
                chat_id = record['chat_id']
                
                # Fetch all messages in this conversation from supabase
                result = await supabase.table("messages").select("role,content").eq("chat_id", chat_id).order("created_at").execute()
                conversation_messages = result.data if result.data else []

                # Fetch the workflow steps from supabase
                workflow_steps = await get_workflow_steps(supabase, chat_id)

                # Fetch the chat itself from supabase
                result = await supabase.table("chats").select("*").eq("id", chat_id).execute()
                chat = result.data[0] if result.data else None
                
                # # Pass the list of messages to process_with_openai
                await process_with_openai(supabase, record['content'], username, chat_id, conversation_messages, workflow_steps, chat)
            
        except (KeyError, TypeError) as e:
            print(f"Error processing message: {e}")
            raise e
    async def on_new_run(payload):
        try:
            record = payload['data']['record']
            run_id = record['id']
            chat_id = record['chat_id']
            dashboard_id = record['dashboard_id']
            # post a message requesting the dashboard to spawn a window with the chrome extension.
            await supabase.table("run_messages").insert({
                "run_id": run_id,
                "type": "spawn_window",
                "chat_id": chat_id,
                "sender_type": "backend",
                "display_text": "Requesting dashboard to launch extension..."
            }).execute()
            print("new run", run_id)
        except (KeyError, TypeError) as e:
            print(f"Error processing message: {e}")
            raise e
    async def on_run_message(payload):
        try:
            record = payload['data']['record']
            print("RUN MESSAGE", record)
            sender_type = record['sender_type']
            type = record['type']
            if sender_type == "extension" and type != "abort":
                workflow_steps = await get_workflow_steps(supabase, record['chat_id'])
                task = ""
                for step in workflow_steps:
                    task += step["description"] + "\n"
                
                run_id = record['run_id']
                # Clean up logs directory before starting
                log_dir = "logs"
                for file in os.listdir(log_dir):
                    if file.endswith('.txt'):
                        os.remove(os.path.join(log_dir, file))
                browser_context = await browser.new_context()

                await browser_context.switch_to_tab(0)
                agent = Agent(
                    task=task + "IMPORTANT: Just use GO TO URL to navigate the page and don't open new tabs. Note: after email is entered in gmail it may pop up the same email and ask to click it again.", #The available tabs are wrong and the tab ids are 1+ whatever the id is. Keep this in mind while switching tabs.", #+"IMPORTANT: Load the first page within the first tab. Don't open new tab initially. When new tab is added it's index will be 2 and so on.",
                    llm=ChatOpenAI(model="gpt-4o"),
                    browser=browser,
                    save_conversation_path="logs/conversation"  
                )

                # Set up file system event handler
                class LogHandler(watchdog.events.FileSystemEventHandler):
                    def __init__(self, supabase_client, run_id, queue):
                        self.supabase = supabase_client
                        self.run_id = run_id
                        self.queue = queue
                        super().__init__()

                    async def process_log_file(self, file_path):
                        try:
                            with open(file_path, 'r') as f:
                                content = f.read()
                                if 'RESPONSE' in content:
                                    response_data = json.loads(content.split('RESPONSE\n')[1])
                                    print("response_data", response_data)
                                    # Update run message with current state and action
                                    await self.supabase.table("run_messages").insert({
                                        "run_id": self.run_id,
                                        "type": "command",
                                        "sender_type": "backend",
                                        "display_text": response_data["current_state"]["next_goal"],
                                        "payload": {
                                            "current_state": response_data["current_state"],
                                            "action": response_data["action"]
                                        }
                                    }).execute()

                                    # If task is complete, send final message
                                    if "done" in response_data["action"][0]:
                                        await self.supabase.table("run_messages").insert({
                                            "run_id": self.run_id,
                                            "type": "result",
                                            "sender_type": "backend",
                                            "display_text": "Task completed successfully",
                                            "payload": response_data["action"][0]["done"]
                                        }).execute()
                                        
                                        # Update run status
                                        await self.supabase.table("runs").update({
                                            "in_progress": False
                                        }).eq("id", self.run_id).execute()

                        except Exception as e:
                            print(f"Error processing log file: {e}")

                    def on_created(self, event):
                        if event.is_directory:
                            return
                        if event.src_path.endswith('.txt'):
                            self.queue.put_nowait(event.src_path)

                # Set up async queue and worker
                queue = asyncio.Queue()
                
                async def process_queue():
                    while True:
                        file_path = await queue.get()
                        await event_handler.process_log_file(file_path)
                        queue.task_done()

                # Start the queue processor
                queue_processor = asyncio.create_task(process_queue())

                # Set up the observer
                path = "logs"
                event_handler = LogHandler(supabase, run_id, queue)
                observer = watchdog.observers.Observer()
                observer.schedule(event_handler, path, recursive=False)
                observer.start()

                # Run the agent
                result = await agent.run()
                print("result", result)

                # Stop the observer
                observer.stop()
                observer.join()

        except (KeyError, TypeError) as e:
            print(f"Error processing message: {e}")
            raise e
    
    # Create a wrapper that handles the async callback properly
    def handle_record(payload):
        asyncio.create_task(on_new_record(payload))
        return
    def handle_new_run(payload):
        asyncio.create_task(on_new_run(payload))
    def handle_run_message(payload):
        asyncio.create_task(on_run_message(payload))
        return
    
    # Subscribe to changes using the async realtime client
    messages_channel = supabase.realtime.channel("messages-changes")
    messages_channel.on_postgres_changes(
        "*",               # Listen for all event types
        schema="public",
        table="messages",
        callback=handle_record  # Use the wrapper function instead
    )
    runs_channel = supabase.realtime.channel("runs-changes")
    runs_channel.on_postgres_changes(
        "INSERT",         # Listen for only new record events
        schema="public",
        table="runs",
        callback=handle_new_run
    )
    run_messages_channel = supabase.realtime.channel("run_messages-changes")
    run_messages_channel.on_postgres_changes(
        "*",
        schema="public",
        table="run_messages",
        callback=handle_run_message
    )
    
    await messages_channel.subscribe()
    await runs_channel.subscribe()
    await run_messages_channel.subscribe()
    
    # Instead of relying on listen() to block, run an infinite loop
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    # async def test_agent():
    #     agent = Agent(
    #         task="SF weather",
    #         llm=ChatOpenAI(model="gpt-4o"),
    #         browser=browser,
    #         save_conversation_path="logs/conversation"  
    #     )
    #     result = await agent.run()
    #     print("result", result)

    # # Run both the test agent and main function
    # async def run_all():
    #     await asyncio.gather(test_agent())

    asyncio.run(main())
# %%
