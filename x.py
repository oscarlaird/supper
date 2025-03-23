#%%
from langchain_openai import ChatOpenAI
from browser_use import Agent
from browser_use import Browser
from browser_use import BrowserConfig
import asyncio
import nest_asyncio 
from dotenv import load_dotenv

load_dotenv()
nest_asyncio.apply()
config = BrowserConfig(
    cdp_url="ws://0.0.0.0:9223/playwright"
    #cdp_url ="ws://127.0.0.1:9222/devtools/browser/9d1e3be6-32cf-41cd-b8d2-988173595822"
    # cdp_url = "ws://127.0.0.1:9222/devtools/browser/f4ce136b-eeff-4ffd-a0aa-4e4b427a519c"
)
browser = Browser(config=config)
async def main():
    agent = Agent(
        task="Go find the tempearture in the city of San Francisco",
        
        llm=ChatOpenAI(model="gpt-4o"),
        browser=browser,
    )
    result = await agent.run()
    print(result)
asyncio.run(main())
#%%
import importlib.metadata  # Python 3.8+
import browser_use
# or from importlib_metadata import version  # For Python <3.8 with backport
version = importlib.metadata.version("browser_use")
print(version)
# %%
