import asyncio
import json
import configparser
from pyquotex.stable_api import Quotex

async def main():
    config = configparser.ConfigParser()
    config.read('settings/config.ini')
    email = config['settings']['email']
    password = config['settings']['password']
    
    client = Quotex(email, password)
    connected, error = await client.connect()
    if not connected:
        print(f"Failed to connect: {error}")
        return
    
    instruments = await client.get_instruments()
    print(f"Total instruments: {len(instruments)}")
    
    # Check for USDBRL
    usd_brl = [i for i in instruments if "USDBRL" in i[1]]
    print(f"USDBRL matches: {usd_brl}")
    
    # Save all to file for inspection
    with open("all_instruments.json", "w") as f:
        json.dump(instruments, f, indent=2)
        
    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
