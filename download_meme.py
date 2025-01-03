import aiohttp
import asyncio
import asyncpg
import re
from datetime import datetime
from private_conf import AUTHORIZATION, COOKIES, POSTGREST_PASSWORD, POSTGREST_USERNAME

headers = {
    'Authorization': AUTHORIZATION,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Content-Type': 'application/json'
}

async def get_messages(channel_id, session):
    messages = []
    last_message_id = None
    
    while True:
        if last_message_id:
            url = f"https://discord.com/api/v9/channels/{channel_id}/messages?before={last_message_id}&limit=100"
        else:
            url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=100"
            
        try:
            async with session.get(url, headers=headers, cookies=COOKIES) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    print(f"Rate limited. Waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    continue
                    
                if response.status != 200:
                    print(f"Error: Status Code {response.status}")
                    break
                    
                batch = await response.json()
                if not batch:
                    break
                    
                messages.extend(batch)
                last_message_id = batch[-1]['id']
                print(f"Retrieved {len(batch)} messages. Total: {len(messages)}")
                await asyncio.sleep(1)
                
        except Exception as e:
            print(f"Error fetching messages: {str(e)}")
            break
            
    return messages

def extract_media_urls(message):
    urls = []
    
    # Check attachments
    for attachment in message.get('attachments', []):
        if 'url' in attachment:
            urls.append(attachment['url'])
    
    # Check embeds
    for embed in message.get('embeds', []):
        if 'image' in embed and embed['image'].get('url'):
            urls.append(embed['image']['url'])
        if 'thumbnail' in embed and embed['thumbnail'].get('url'):
            urls.append(embed['thumbnail']['url'])
    
    # Process URLs
    processed_urls = []
    for url in urls:
        if 'media.discordapp.net' in url:
            url = url.replace('media.discordapp.net', 'cdn.discordapp.com')
            if '?' not in url:
                url = f"{url}?ex=9999999999&is=9999999999&hm=9999999999999999999999999999999999999999999999999999999999999999"
        if "cdn.discordapp.com" not in url:
            continue
        processed_urls.append(url)
    
    return list(set(processed_urls))

def get_media_type(url):
    if '.gif' in url.lower():
        return 'gif'
    elif any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png']):
        return 'image'
    else:
        return 'video'

async def download_media(url, session):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            else:
                print(f"Failed to download media from {url}: Status {response.status}")
                return None
    except Exception as e:
        print(f"Error downloading media from {url}: {str(e)}")
        return None

async def process_url(url, message, conn, session):
    try:
        # First check if URL exists
        exists = await conn.fetchval('SELECT COUNT(*) FROM memes WHERE url = $1', url)
        if exists:
            print(f"URL already in database: {url}")
            return
            
        # Download the media file
        file_data = await download_media(url, session)
        if not file_data:
            print(f"Skipping {url} due to download failure")
            return
            
        # Convert timestamp string to datetime object
        timestamp = datetime.strptime(message['timestamp'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
        
        # Insert new record
        await conn.execute('''
            INSERT INTO memes (
                url, 
                author_id, 
                timestamp, 
                media_type,
                file_data
            )
            VALUES ($1, $2, $3, $4, $5)
        ''', 
        url, 
        message['author']['id'], 
        timestamp, 
        get_media_type(url),
        file_data
        )
        
        print(f"Stored media from URL: {url}")
        
    except Exception as e:
        print(f"Error processing URL {url}: {str(e)}")

async def main():
    channels = ["341284235581194241", "424988827686404096", "595960816185114654", 
                "720096632615731250", "969507244980981820"]
    
    # Database connection
    conn = await asyncpg.connect(
        user=POSTGREST_USERNAME,
        password=POSTGREST_PASSWORD,
        database='memedb',
        host='192.168.178.23',
        port=5433
    )
    
    try:
        async with aiohttp.ClientSession() as session:
            for channel_id in channels:
                print(f"\nProcessing channel {channel_id}")
                messages = await get_messages(channel_id, session)
                
                for message in messages:
                    urls = extract_media_urls(message)
                    for url in urls:
                        await process_url(url, message, conn, session)
                        await asyncio.sleep(0.1)  # Small delay between processing URLs
                
    except Exception as e:
        print(f"Error in main process: {str(e)}")
    finally:
        await conn.close()
        print("\nProcess completed")

if __name__ == "__main__":
    asyncio.run(main())