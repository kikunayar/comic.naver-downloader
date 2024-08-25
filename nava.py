import requests
import asyncio
import aiohttp
import httpx
from bs4 import BeautifulSoup
import re
from pathlib import Path

# Global lists to store image URLs and save paths
dl, sp = [], []

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

async def fetch_url(client, url):
    try:
        response = await client.get(url)
        if response.status == 200:
            return response.text
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
    return None

async def fetch_download_image(client, url, fp):
    attempt = 0
    retries = 999
    while attempt < retries:
        try:
            async with client.get(url, headers=headers) as response:
                if response.status == 200:
                    image = await response.read()
                    fp.write_bytes(image)
                    print(f"DONE {fp}")
                    return
                else:
                    print(f"Failed to fetch image from {url}: Status code {response.status}")
        except Exception as e:
            print(f"Error fetching image from {url}: {e}")
        attempt += 1
        print(f"Retrying... ({attempt}/{retries})")
    print(f"Failed to fetch image from {url} after {retries} attempts")

async def download():
    async with aiohttp.ClientSession() as client:
        tasks = []
        for url, fp in zip(dl, sp):
            task = asyncio.create_task(fetch_download_image(client, url, fp))
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)

async def set_path(start, end, comic_id, full_path):
    global dl
    urls = [f"https://comic.naver.com/webtoon/detail?titleId={comic_id}&no={cur}" for cur in range(start, end)]
    async with httpx.AsyncClient() as client:
        responses = await asyncio.gather(*[fetch_url(client, url) for url in urls])
        for cur, content in zip(range(start, end), responses):
            if content:
                soup = BeautifulSoup(content, 'html.parser')
                div = soup.select_one('body > div:nth-of-type(1) > div:nth-of-type(3) > div:nth-of-type(1)')
                if div:
                    img_tags = div.find_all('img')
                    img_links = [img['src'] for img in img_tags if 'src' in img.attrs]
                    dl.extend(img_links)
                    img_folder = full_path / str(cur)
                    img_folder.mkdir(parents=True, exist_ok=True)
                    save_paths = [img_folder / f'{e}.jpg' for e in range(len(img_links))]
                    sp.extend(save_paths)

def downloader(start, end, comic_id, outpath):
    outpath = Path(outpath)
    name_url = f"https://comic.naver.com/webtoon/list?titleId={comic_id}"
    response = requests.get(name_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        meta_tag = soup.find('meta', attrs={'property': 'og:title'})
        title_content = meta_tag.get('content')
        folder_name = re.sub(r'[<>:"/\\|?*]', '-', title_content)
        full_path = outpath / folder_name
        full_path.mkdir(parents=True, exist_ok=True)
        asyncio.run(set_path(start, end + 1, comic_id, full_path))
        asyncio.run(download())
    else:
        print(f"Failed to retrieve the comic list from {name_url}")
