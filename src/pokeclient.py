import os
import json
import asyncio
from pathlib import Path
from typing import Union, Optional, Dict, Any
import aiohttp
from PIL import Image
from io import BytesIO

class AsyncPokeAPI:
    def __init__(self, max_concurrent_requests: int = 10):
        self.base_url = "https://pokeapi.co/api/v2"
        self.cache_dir = Path("assets/poke_cache")
        self.image_dir = self.cache_dir / "images"
        self.data_dir = self.cache_dir / "data"
        self.max_concurrent = max_concurrent_requests
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._locks = {}
        self._session = None
        self._session_lock = asyncio.Lock()

        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": "AsyncPokeAPI/1.0"},
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, *exc):
        await self._session.close()
        self._session = None

    def _get_cache_path(self, resource: str, resource_id: Union[int, str]) -> Path:
        return self.data_dir / f"{resource}_{resource_id}.json"

    def _get_image_path(self, pokemon_id: int) -> Path:
        return self.image_dir / f"{pokemon_id}.png"

    async def _get_lock(self, key: str):
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    async def _fetch_json(self, url: str) -> Dict[str, Any]:
        await self.ensure_session()
        async with self._semaphore:
            async with self._session.get(url) as response:
                response.raise_for_status()
                return await response.json()

    async def _get_resource_data(self, resource: str, identifier: Union[int, str]) -> Dict:
        cache_path = self._get_cache_path(resource, identifier)
        lock = await self._get_lock(f"data_{resource}_{identifier}")

        async with lock:
            # Leer de caché con operaciones nativas asincrónicas
            if await asyncio.to_thread(cache_path.exists):
                content = await asyncio.to_thread(cache_path.read_text, encoding='utf-8')
                return json.loads(content)

            # Obtener datos de la API
            url = f"{self.base_url}/{resource}/{identifier}"
            data = await self._fetch_json(url)

            # Guardar en caché
            if 'id' in data:
                final_cache_path = self._get_cache_path(resource, data['id'])
                await asyncio.to_thread(
                    final_cache_path.write_text,
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )

            return data

    async def ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"User-Agent": "PokeAPI/2.0"},
                timeout=aiohttp.ClientTimeout(total=30)
            )

    async def close(self):
        async with self._session_lock:
            if self._session:
                await self._session.close()
                self._session = None

    async def get_pokemon(self, identifier: Union[int, str]) -> Dict:
        return await self._get_resource_data('pokemon', identifier)

    async def get_image(self, identifier: Union[int, str]) -> Image.Image:
        try:
            data = await self.get_pokemon(identifier)
            pokemon_id = data['id']
            image_path = self._get_image_path(pokemon_id)
            lock = await self._get_lock(f"image_{pokemon_id}")

            async with lock:
                # Verificar imagen en caché
                if await asyncio.to_thread(image_path.exists):
                    try:
                        return Image.open(image_path)
                    except (IOError, Image.UnidentifiedImageError):
                        await asyncio.to_thread(image_path.unlink, missing_ok=True)

                # Descargar imagen
                image_url = data['sprites']['other']['official-artwork']['front_default']
                async with self._session.get(image_url) as response:
                    response.raise_for_status()
                    image_data = await response.read()

                # Guardar temporal y validar
                temp_path = image_path.with_suffix('.tmp')
                await asyncio.to_thread(temp_path.write_bytes, image_data)
                
                try:
                    image = Image.open(BytesIO(image_data))
                    image.verify()
                except (IOError, Image.UnidentifiedImageError) as e:
                    await asyncio.to_thread(temp_path.unlink, missing_ok=True)
                    raise ValueError(f"Invalid image data: {e}") from e

                # Mover a ubicación final
                await asyncio.to_thread(os.replace, temp_path, image_path)
                return Image.open(BytesIO(image_data))
                
        except aiohttp.ClientError as e:
            await asyncio.sleep(1)
            return await self.get_image(identifier)

    async def get_all_types(self) -> Dict:
        return await self._get_resource_data('type', '')

    async def get_ability(self, identifier: Union[int, str]) -> Dict:
        return await self._get_resource_data('ability', identifier)

    async def get_move(self, identifier: Union[int, str]) -> Dict:
        return await self._get_resource_data('move', identifier)

async def main():
    async with AsyncPokeAPI() as api:
        tasks = [
            api.get_pokemon(25),
            api.get_image(25),
            api.get_move('thunderbolt')
        ]
        results = await asyncio.gather(*tasks)
        
        pikachu, image, move = results
        print(f"Nombre: {pikachu['name'].capitalize()}")
        print(f"Movimiento: {move['name']} - {move['power']} power")
        image.show()

if __name__ == "__main__":
    asyncio.run(main())