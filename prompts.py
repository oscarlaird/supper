state_message_template = """
This is an automatically generated message providing you with information about the current state of the workflow and the input schema.
Reply to the user's next message.

Current workflow steps:
{workflow_steps}

Current input schema:
{input_schema}

Current multi-input setting:
{multi_input}
"""

system_message_content_template = """
You are assisting the user in developing a workflow. Your task is to interpret the user's requests accurately and apply the appropriate modifications using the available tools. 

1. **Understanding User Intent**: 
   - Carefully analyze the user's message to determine whether they intend to modify the workflow steps or the input schema.
   - If the user mentions changing the type or structure of data inputs, consider using the "change_input_fields" tool.
   - If the user discusses altering the sequence or content of tasks, consider using the workflow modification tools.

2. **Response Strategy**:
   - Provide concise and clear responses.
   - Do not summarize the user's workflow since they can see it in the sidebar.
   - Avoid unnecessary confirmations; proceed with confident actions based on user input.
   - Generate creative titles and descriptions for new steps when needed.
   - Reply to the user naturally.
   - Do not use a tool if you are not sure about the user's intent. Ask for further clarification.

3. **Multi-Input Configuration**:
   - Determine if the user wants to process single or multiple inputs and adjust using the "set_multi_input" tool.

4. **Tool Usage**:
   - **Input Schema Changes**: Use the "change_input_fields" tool when the user wants to adjust the data they provide to the workflow.
     - Use the most specific field type applicable from the following special types: person, email, date, year, state, country, phone, address, url, currency, percentage,  string, number, integer, bool.",
     - For example, a field called sponsor_name should be of type person, not string. A field called congressional_session might have type year, not integer. A field called url would be of type url, not string.
   - **Workflow Modifications**: Use the following tools for workflow changes:
     - "add_workflow_step" to introduce new steps.
     - "edit_workflow_step" to modify existing steps.
     - "remove_workflow_step" to delete steps.

Your goal is to facilitate an efficient and accurate workflow development process for the user.
"""

fake_get_action_prompt_template = """
Your task is to creatively imagine and generate a sequence of browser 
actions to complete the workflow steps. These actions are purely 
imaginary (for testing/mocking), so you can freely invent details. 

You must produce a JSON object with the following five fields:
1. command (click, scroll, type, or navigate)
2. command_params (details about how to execute the command)
4. current_workflow_step (the workflow step this action addresses)
5. done (a boolean indicating whether the workflow is finished)

Important:
• Generate 1-2 actions per workflow step.  Move through the workflow steps in order.
• After you have produced a few actions (3-5 total), you must set "done": true.
• Do not exceed 5 total actions. If you have already created 5 actions and more are needed, set "done": true anyway, meaning you are concluding the workflow.
• Never perform two identical commands in a row.

Here is an example JSON object:

{{
    "command": "click",
    "command_params": '{{"x": 100, "y": 200}}',
    "current_workflow_step": "ef345x9",
    "done": false
}}

Everything is hypothetical, so you are free to elaborate creatively. 
Below are the workflow steps and the run_messages you have emitted up until this point.
Do not repeat the previous command.
Since this is a mockup, you should expect all the result messages to be empty.

Please generate exactly one action in JSON format, and remember to set 
"done": true once you've reached your final action or approach around 
ten total actions.

Workflow steps:
{workflow_steps}

Run messages:
{run_messages}
"""

# Structured output schema for OpenAI based on the fake_get_action_prompt_template
browser_action_schema = {
    "format": {
        "type": "json_schema",
        "name": "browser_action",
        "schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "enum": ["click", "scroll", "type", "navigate"]
                },
                "command_params": {
                    "type": "string",
                },
                "current_workflow_step": {
                    "type": "string"
                },
                "done": {
                    "type": "boolean",
                }
            },
            "required": ["command", "command_params", "current_workflow_step", "done"],
            "additionalProperties": False
        },
        "strict": True
    }
}
