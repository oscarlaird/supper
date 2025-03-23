#%%
import tqdm
import time

def my_callback(current, total):
    print(f"Callback: {current} out of {total} completed.")

class CallbackTqdm(tqdm.tqdm):
    def __init__(self, *args, **kwargs):
        self.callback = my_callback
        super().__init__(*args, **kwargs)

    def update(self, n=1):
        # Call the base update method
        super().update(n)
        # Call the callback with current progress and total if provided
        if self.callback:
            self.callback(self.n, self.total)

tqdm.tqdm = CallbackTqdm

# Usage example
script = """
from tqdm import tqdm
for i in tqdm(range(100)):
    time.sleep(0.1)  # Simulate work
"""

exec(script)


