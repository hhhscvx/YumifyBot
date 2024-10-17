import asyncio
from random import randint, uniform
from urllib.parse import unquote

from aiohttp import ClientSession
import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered
from pyrogram.raw.functions.messages import RequestWebView
from pyrogram.errors import FloodWait

from bot.utils import logger
from bot.config import InvalidSession
from .headers import headers
from bot.config import settings


class Tapper:
    def __init__(self, tg_client: Client) -> None:
        self.session_name = tg_client.name
        self.tg_client = tg_client
        self.user_id = 0

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy: Proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            with_tg = True

            if not self.tg_client.is_connected:
                with_tg = False
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            while True:
                try:
                    peer = await self.tg_client.resolve_peer('Yumify_Bot')
                    break
                except FloodWait as fl:
                    fls = fl.value

                    logger.warning(f"{self.session_name} | FloodWait {fl}")
                    logger.info(f"{self.session_name} | Sleep {fls}s")

                    await asyncio.sleep(fls + 3)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=peer,
                bot=peer,
                platform='android',
                from_bot_menu=False,
                url='https://frontend.yumify.one/'
            ))

            auth_url = web_view.url
            query = unquote(string=auth_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])

            self.user_id = (await self.tg_client.get_me()).id

            if with_tg is False:
                await self.tg_client.disconnect()

            return query

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def login(self, http_client: ClientSession, tg_web_data: str) -> dict:
        try:
            http_client.headers['X-Tg-User-Id'] = self.user_id
            http_client.headers['X-Tg-Web-Data'] = tg_web_data
            response = await http_client.post(url='https://backend.yumify.one/api/game/login',
                                              json={})
            response.raise_for_status()

            return await response.json()
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Login: {error}")
            await asyncio.sleep(delay=3)

    async def claim(self, http_client: ClientSession) -> dict:
        """TODO claim['v..']['v..']['v..']['value'] | claim['v']['v']['dayNumber']"""
        try:
            response = await http_client.post(url='https://backend.yumify.one/api/daily-rewards/claimDailyReward',
                                              json={})
            response.raise_for_status()

            return await response.json()
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when claim: {error}")
            await asyncio.sleep(delay=3)

    async def get_latest_claim(self, http_client: ClientSession) -> dict:
        """TODO если get_latest_claim['value']['value']['hasUnclaimed'] true то клеймить"""
        try:
            response = await http_client.post(url='https://backend.yumify.one/api/daily-rewards/getLatestStreak',
                                              json={})
            response.raise_for_status()

            return await response.json()
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when get latest claim: {error}")
            await asyncio.sleep(delay=3)

    async def send_taps(self, http_client: ClientSession, taps: int, turbo: bool = False) -> dict:
        try:
            turbo = 'false' if not turbo else 'true'
            response = await http_client.post(url=f'https://backend.yumify.one/api/game/submitTaps?turbo={turbo}',
                                              json={'battleId': None, 'taps': taps})
            response.raise_for_status()

            return await response.json()
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when tapping: {error}")
            await asyncio.sleep(delay=3)

    async def apply_turbo_boost(self, http_client: ClientSession) -> dict:
        try:
            response = await http_client.post(url='https://backend.yumify.one/api/game/activateDailyBooster',
                                              json={'booster': 'turbo'})
            response.raise_for_status()

            return await response.json()
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Apply Turbo Boost: {error}")
            await asyncio.sleep(delay=3)

    async def apply_energy_boost(self, http_client: ClientSession) -> dict:
        try:
            response = await http_client.post(url='https://backend.yumify.one/api/game/activateDailyBooster',
                                              json={'booster': 'fullRecharge'})
            response.raise_for_status()

            return await response.json()
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Apply Energy Boost: {error}")
            await asyncio.sleep(delay=3)

    async def get_me(self, http_client: ClientSession) -> dict:
        try:
            response = await http_client.post(url='https://backend.yumify.one/api/game/me',
                                              json={})
            response.raise_for_status()

            return await response.json()
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when get user info: {error}")
            await asyncio.sleep(delay=3)

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def run(self, proxy: str | None) -> None:
        active_turbo = False

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        async with aiohttp.ClientSession(headers=headers, connector=proxy_conn) as http_client:
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            attempts = 3
            while attempts:
                try:
                    tg_web_data = await self.get_tg_web_data(proxy=proxy)
                    login = await self.login(http_client=http_client, tg_web_data=tg_web_data)
                    logger.success(f"{self.session_name} | Login! Balance: {login.get('balance')} | Energy: "
                                   f"{login.get('energy')}/{login.get('energyLimit')} | Turbo Boosts: {login.get('turboBoostersAvailable')}"
                                   f" | Energy Boosts: {login.get('fullRechargeBoostersAvailable')}")
                    break
                except Exception as e:
                    logger.error(f"{self.session_name} | Left login attempts: {attempts}, error: {e}")
                    await asyncio.sleep(uniform(*settings.RELOGIN_DELAY))
                    attempts -= 1
            else:
                logger.error(f"{self.session_name} | Couldn't login")
                return

            while True:
                try:
                    ...

                except InvalidSession as error:
                    raise error

                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error: {error}")
                    await asyncio.sleep(delay=3)

                else:
                    sleep_between_clicks = randint(a=settings.SLEEP_BETWEEN_TAP[0], b=settings.SLEEP_BETWEEN_TAP[1])

                    if active_turbo is True:
                        active_turbo = False

                    logger.info(f"Sleep {sleep_between_clicks}s")
                    await asyncio.sleep(delay=sleep_between_clicks)


async def run_tapper(tg_client: Client, proxy: str | None):
    try:
        await Tapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
