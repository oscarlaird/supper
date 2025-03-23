#%%
# !pip install aider-chat
import os, tempfile
from pathlib import Path
from aider.coders import Coder
from aider.models import Model
from aider.io import InputOutput
from dotenv import load_dotenv
from pathlib import Path
# import anthropic

load_dotenv()

# MODEL_NAME = "claude-3-sonnet-20240229"
MODEL_NAME= "claude-3-7-sonnet-20250219"

from aider.coders import UnifiedDiffCoder
def apply_aider_edit_with_diff(code_to_edit, instruction, model_name=MODEL_NAME):
    """
    Apply an edit to code using aider's UnifiedDiffCoder.
    
    Args:
        code_to_edit (str): The source code to be edited
        instruction (str): The instruction for editing the code
        model_name (str): The name of the model to use
        
    Returns:
        str: The edited code
    """
    # Use Claude Sonnet 3.5 model
    model = Model(model_name)

    # Prepare non-interactive I/O and temp file for the code
    io = InputOutput(yes=True)
    tmp_file = tempfile.NamedTemporaryFile(suffix=".py", delete=False)
    try:
        tmp_file_path = Path(tmp_file.name)
        tmp_file_path.write_text(code_to_edit)

        # Create the UnifiedDiffCoder session with the temp file
        coder = UnifiedDiffCoder(
            main_model=model,
            io=io,
            fnames=[str(tmp_file_path)],
            use_git=False,
            auto_commits=False,
            auto_lint=False,
            auto_test=False,
            map_tokens=0,  # no repo, don't need repo map
            map_refresh="never",
            cache_prompts=False,
            stream=False  # anthropic especially can be slower with streaming
        )
        
        # Disable reflections for faster processing
        coder.max_reflections = 2
        
        # Execute the single instruction
        coder.run(instruction)

        # token count
        print(coder.message_tokens_sent, coder.message_tokens_received)
        
        # Read the modified code from the file
        edited_code = tmp_file_path.read_text()
    finally:
        tmp_file.close()           # close the file
        tmp_file_path.unlink()     # remove the temp file
    return edited_code

#%%