import asyncio
from src.lingo import LingoClient

async def test_lingo():
    # Use the User's Key (hardcoded here for the test script only)
    # In production it comes from input
    api_key = "api_ffqsk8a2qnmbzfyi3gdj6jmk"
    
    print(f"Testing Lingo.dev API with key: {api_key[:10]}...")
    
    client = LingoClient(api_key=api_key, mock=False)
    
    try:
        # Request a simple translation
        suggestion = await client.suggest_translation(
            text="Submit Payment", 
            target_lang="es", 
            context="Button on a payment form"
        )
        print(f"SUCCESS! Suggestion: '{suggestion}'")
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    asyncio.run(test_lingo())
