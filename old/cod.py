#%%
import asyncio
import os
from dotenv import load_dotenv
from supabase.client import AsyncClient
from openai import AsyncOpenAI
import nest_asyncio
nest_asyncio.apply()
import json
import time
import sys
import traceback
from io import StringIO
from functools import wraps
import inspect
import pandas as pd
import time
import tqdm
import uuid
old_tqdm = tqdm.tqdm

# local
import prompts
from use_aider import apply_aider_edit_with_diff

# Load environment variables
load_dotenv()
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize clients
client = AsyncOpenAI(api_key=openai_api_key)
supabase = AsyncClient(supabase_url, supabase_key)

# Model to use
MODEL = "gpt-4o-mini"


async def get_conversation_messages(supabase, chat_id):
    """Fetch all messages for a chat"""
    result = await supabase.table("messages").select("*").eq("chat_id", chat_id).order("created_at").execute()
    return result.data if result.data else []

async def get_code(supabase, chat_id):
    """Fetch the code for a chat"""
    result = await supabase.table("messages") \
    .select("script") \
    .eq("chat_id", chat_id) \
    .neq("script", None) \
    .order("created_at", desc=True) \
    .limit(1) \
    .execute()
    return result.data[0]['script'] if result.data else None

def gather_param_dict(f, args, kwargs):
    ex_in = {}
    sig = inspect.signature(f)
    param_names = list(sig.parameters.keys())
    for i, arg in enumerate(args):
        if i < len(param_names):
            ex_in[param_names[i]] = arg
        else:
            ex_in[f'arg{i}'] = arg
    ex_in.update(kwargs)
    return ex_in

def serialize_if_dataframe(ret):
    if type(ret) == pd.DataFrame:
        # The 'orient="records"' parameter converts the DataFrame to a list of dictionaries
        # where each dictionary represents a row with column names as keys
        # This format is useful for JSON serialization of tabular data
        return ret.to_dict(orient="records")
    return ret

def serialize_pandas(ret):
    """Serialize pandas Series or DataFrame to a list of dictionaries."""
    if isinstance(ret, pd.Series):
        ret = ret.to_frame() # Convert Series to DataFrame with one column
    if isinstance(ret, pd.DataFrame):
        return serialize_if_dataframe(ret)
    return ret

def serialize_ret(ret):
    """ Serialize the return value of a function to a dictionary. Valid types are: string, number,
    boolean, df or tuple or dict thereof. Nested tuples and dicts are not allowed. """
    valid_types = (str, int, float, bool, pd.DataFrame, pd.Series)
    if isinstance(ret, valid_types):
        return {"_ret": serialize_pandas(ret)}
    elif isinstance(ret, (tuple, dict)):
        names = [f"_ret_{i}" for i in range(len(ret))] if isinstance(ret, tuple) else ret.keys()
        values = ret.values() if isinstance(ret, dict) else ret
        if not all(isinstance(item, valid_types) for item in values):
            print(f"Warning: Invalid return type in {names}: {values}")
            return None
        return {name: serialize_pandas(item) for name, item in zip(names, values)}
    else:
        print(f"Warning: Invalid return type: {type(ret)}")
        return None
    

async def execute_code(code, function_status_start_callback, function_status_end_callback, progress_callback, MOCK=False):
    """Execute the code and capture output and errors"""
    # Redirect stdout and stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = StringIO()
    redirected_error = StringIO()
    sys.stdout = redirected_output
    sys.stderr = redirected_error
    
    result = ""
    error_result = ""
    success = True
    # data extracted by the decorators; mutable
    example_inputs = [None]  # mutable
    last_fstatus_id = [None]
    steps = {}
    try:
        # Execute the code
        # Create a globals dictionary with our variables
        def mock_inputs(f):
            result = f()
            example_inputs[0] = serialize_ret(result)
            return mock(f)
        def mock(f):
            @wraps(f)  # Preserve the original function's name and metadata
            def wrapper(*args, **kwargs):
                ex_in = serialize_ret(gather_param_dict(f, args, kwargs))  # inputs to the function
                fname = f.__name__
                step_info = {
                    "description": f.__doc__,
                    "example_input": ex_in,
                    "example_output": None
                }
                # Gather both positional and named arguments into a dictionary
                fstatus_id = str(uuid.uuid4())
                last_fstatus_id[0] = fstatus_id
                function_status_start_callback(fname, step_info, fstatus_id)
                #
                if MOCK:
                    print(f"Using the mock {fname} function")
                    ret = f(*args, **kwargs)
                else:
                    print(f"Should use the real {fname} function")
                    ret = f(*args, **kwargs)
                ex_out = serialize_ret(ret)  # output of the function
                step_info["example_output"] = ex_out
                function_status_end_callback(fname, step_info, fstatus_id)  # this is async but no need to await since just logging
                if fname not in steps:
                    steps[fname] = step_info
                return ret
            return wrapper
        class CallbackTqdm(old_tqdm):
            def __init__(self, *args, **kwargs):
                self.progress_callback = progress_callback
                self.last_fstatus_id = last_fstatus_id[0]  # get the fstatus_id for the function call last ran when this tqdm was created
                kwargs.update({"miniters": 1, "mininterval": 0})  # tell tqdm to update every iteration
                super().__init__(*args, **kwargs)

            def update(self, n=1):
                self.progress_callback(self.n, self.total, self.last_fstatus_id)
                super().update(n)
        tqdm.tqdm = CallbackTqdm  # change the global tqdm
        code = code.replace("from tqdm import tqdm\n", "")  # TODO: more robust way to patch tqdm
        print("CODE", code)
        globals_dict = {"mock": mock, "mock_inputs": mock_inputs, "tqdm": CallbackTqdm}
        globals_dict["__name__"] = "__main__"
        # Execute the code with our custom globals
        exec(code, globals_dict, None)
        output = redirected_output.getvalue()
        error = redirected_error.getvalue()
        result = output
        if error:
            error_result = error
    except Exception as e:
        success = False
        # Get the full traceback
        error_result = f"Execution error: {str(e)}\n\nFull traceback:\n{traceback.format_exc()}"
    finally:
        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    return {
        "code_run_success": success,
        "code_output": result,
        "code_output_error": error_result,
        "example_inputs": example_inputs[0],
        "steps": steps
    }

async def on_new_message(payload):
    try:
        record = payload['data']['record']
        chat_id = record['chat_id']
        message_id = record['id']
        print("MESSAGE ID", message_id)
        username = record['username']
        
        # Only process user messages
        if record['role'] != 'user':
            return
            
        print(f"Processing new message: {record['content']}")
        
        # Check if requires_text_reply is true for code editing
        requires_text_reply = record.get('requires_text_reply', False)
        code_run = record.get('code_run', False)
        
        # Get code for the chat
        code = await get_code(supabase, chat_id)
        
        dry_run_code = False
        if requires_text_reply:
            # Get conversation history
            conversation_messages = await get_conversation_messages(supabase, chat_id)

            # Format messages for OpenAI
            formatted_messages = [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in conversation_messages
            ]

            # system prompt message
            system_prompt_message = {
                "role": "system",
                "content": prompts.code_system_prompt
            }

            # code prompt message
            code_prompt_message = {
                "role": "user",
                "content": prompts.code_code_prompt_template.format(code=code)
            }
            
            # Query OpenAI with streaming
            start_time = time.time()
            # stream = await client.chat.completions.create(
            #     model=MODEL,
            #     messages=[system_prompt_message, *formatted_messages, code_prompt_message],
            #     stream=True,
            # )
            
            # # Initialize variables to collect the response
            # full_response = ""
            # buffer = ""
            
            # # Process the stream
            # async for chunk in stream:
            #     if chunk.choices and chunk.choices[0].delta.content:
            #         content = chunk.choices[0].delta.content
            #         full_response += content
            #         buffer += content
                    
            #         # Log the chunk
            #         print(content, end="", flush=True)
                    
            #         # Only update the database when we encounter a newline or at the end
            #         if '\n' in buffer:
            #             # Update the script field in the messages table
            #             await supabase.table("messages").update({
            #                 "script": full_response
            #             }).eq("id", record['id']).execute()
            #             buffer = ""
            edited_code = apply_aider_edit_with_diff(code, record['content'])
            print("EDITED CODE", edited_code)
            end_time = time.time()
            print(f"Streaming completed in {end_time - start_time} seconds")
            # Make sure to update one final time at the end
            # if buffer:
            await supabase.table("messages").update({
                "script": edited_code
            }).eq("id", record['id']).execute()
            
            print(f"\nStreaming completed in {time.time() - start_time} seconds")
            dry_run_code = True

        if code_run or dry_run_code:
            # Execute the code and capture output
            print(f"Executing code for chat_id: {chat_id}")
            def function_status_start_callback(function_name, step_info, fstatus_id):
                # Insert into coderun_events table
                asyncio.create_task(supabase.table("coderun_events").insert({
                    "id": fstatus_id,
                    "chat_id": chat_id, 
                    "message_id": message_id,
                    "function_name": function_name, 
                    "example_input": step_info.get('example_input'),
                    "example_output": step_info.get('example_output')
                }).execute())
                if dry_run_code:
                    return
            def function_status_end_callback(function_name, step_info, fstatus_id):
                # Update the coderun_events table
                asyncio.create_task(supabase.table("coderun_events").update({
                    "example_output": step_info.get('example_output')
                }).eq("id", fstatus_id).execute())
            def progress_callback(current, total, fstatus_id):
                print(f"PROGRESS CALLBACK: {current} out of {total} for {fstatus_id}")
                asyncio.create_task(supabase.table("coderun_events").update({
                    "n_progress": current,
                    "n_total": total
                }).eq("id", fstatus_id).execute())
            result = await execute_code(code, function_status_start_callback, function_status_end_callback, progress_callback)

            # Update the message with execution results
            await supabase.table("messages").update(result).eq("id", record['id']).execute()
            
            print(f"Code execution completed. Output saved to message {record['id']}")
        
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        print(f"Full traceback:\n{traceback.format_exc()}")

def handle_message(payload):
    asyncio.create_task(on_new_message(payload))

async def main():
    # Subscribe to changes in the messages table
    messages_channel = supabase.realtime.channel("messages-changes")
    messages_channel.on_postgres_changes(
        "INSERT",
        schema="public",
        table="messages",
        callback=handle_message
    )
    
    # Subscribe to the channel
    await messages_channel.subscribe()
    
    print("Listening for new messages...")
    
    # Keep the program running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())