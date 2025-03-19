tools = [
{
    "type": "function",
    "name": "edit_workflow_step",
    "description": "Edit the title and description of a workflow step. Use empty strings to leave the title or description unchanged.",
    "parameters": {
        "type": "object",
        "properties": {
            "step_id": {"type": "string"},
            "new_title": {"type": "string"},
            "new_description": {"type": "string"}
        },
        "required": ["step_id", "new_title", "new_description"],
        "additionalProperties": False
    },
    "strict": True
},
{
    "type": "function",
    "name": "remove_workflow_step",
    "description": "Remove a workflow step.",
    "parameters": {
        "type": "object",
        "properties": {
            "step_id": {"type": "string"}
        },
        "required": ["step_id"],
        "additionalProperties": False
    },
    "strict": True
},
{
    "type": "function",
    "name": "add_workflow_step",
    "description": "Add a new workflow step. The step number is the position of the step in the workflow. \
So to insert a step after, use step_number+1. \
To insert a step before, use step_number. \
If appending a step, you should use step_number=len(workflow_steps)+1.",
    "parameters": {
        "type": "object",
        "properties": {
            "step_number": {"type": "integer"},
            "title": {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["title", "description", "step_number"],
        "additionalProperties": False
    },
    "strict": True
},
{
    "type": "function",
    "name": "set_multi_input",
    "description": "Set whether the workflow takes multiple inputs (tabular).",
    "parameters": {
        "type": "object",
        "properties": {
            "multi_input": {"type": "boolean"}
        },
        "required": ["multi_input"],
        "additionalProperties": False
    },
    "strict": True
},
{
    "type": "function",
    "name": "change_input_fields",
    "description": "Modify the input fields for the workflow by changing, adding, or removing them. \
    The input schema should be set as a JSON array of objects. Each object must represent a field and include 'type' and 'field_name' properties. \
    Use the most specific type applicable from the following special types: person, email, date, year, state, country, phone, address, url, currency, percentage, string, number, integer, bool.",
    "parameters": {
        "type": "object",
        "properties": {
            "input_schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["string", "number", "integer", "bool", "person", "email", "date", "year", "state", "country", "phone", "address", "url", "currency", "percentage"]},
                        "field_name": {"type": "string"}
                    },
                    "required": ["type", "field_name"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["input_schema"],
        "additionalProperties": False
    },
    "strict": True
}
]
