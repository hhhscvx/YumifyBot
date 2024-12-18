import asyncio
from pprint import pprint
from random import randint, uniform
from time import time
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
        self.energy_boost_name = 'fullRecharge'
        self.turbo_boost_name = 'turbo'

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
            http_client.headers['X-Tg-User-Id'] = str(self.user_id)
            http_client.headers['X-Tg-Web-Data'] = tg_web_data
            response = await http_client.post(url='https://backend.yumify.one/api/game/login',
                                              json={})
            resp_json = await response.json()
            response.raise_for_status()

            return resp_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while Login: {error}")
            await asyncio.sleep(delay=3)

    async def claim(self, http_client: ClientSession) -> dict:
        try:
            response = await http_client.post(url='https://backend.yumify.one/api/daily-rewards/claimDailyReward',
                                              json={})
            response.raise_for_status()

            return await response.json()
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when claim: {error}")
            await asyncio.sleep(delay=3)

    async def get_latest_claim(self, http_client: ClientSession) -> dict:
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

    async def apply_boost(self, http_client: ClientSession, boost_type: str) -> dict:
        """
        :param str boost_type: 'fullRecharge' or 'turbo'
        """
        try:
            response = await http_client.post(url='https://backend.yumify.one/api/game/activateDailyBooster',
                                              json={'booster': boost_type})
            response.raise_for_status()

            return await response.json()
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Apply Energy Boost: {error}")
            await asyncio.sleep(delay=3)

    async def level_up(self, http_client: ClientSession, booster: str) -> dict:
        """
        :param str booster: 'energyLimit' or 'multitap' or 'rechargeSpeed'
        """
        try:
            response = await http_client.post(url='https://backend.yumify.one/api/game/purchaseBooster',
                                              json={'booster': booster})
            response.raise_for_status()

            return await response.json()
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Level Up Boost: {error}")
            await asyncio.sleep(delay=3)

    async def get_boosters(self, http_client: ClientSession, booster: str, level: int | str) -> int:
        """
        :param str booster: 'energyLimit' or 'multitap' or 'rechargeSpeed'
        :param str | int level: user booster level

        :return: Price to upgrade booster
        """
        try:
            response = await http_client.post(url='https://backend.yumify.one/api/game/getBoosters',
                                              json={})
            response.raise_for_status()
            level = str(level)
            resp_json = await response.json()

            return int(resp_json[booster][level].get('price'))
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Get Boosters: {error}")
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
        active_turbo: bool = False
        turbo_time = 0
        last_claimed_time = 0

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        async with aiohttp.ClientSession(headers=headers, connector=proxy_conn) as http_client:
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            attempts = 3
            while attempts:
                try:
                    tg_web_data = await self.get_tg_web_data(proxy=proxy)
                    login = await self.login(http_client=http_client, tg_web_data=tg_web_data)
                    if login.get('kind') == 'success':
                        player_data: dict = login.get('value').get('player')
                        logger.success(f"{self.session_name} | Login! Balance: {player_data.get('balance')} | Energy: "
                                       f"{player_data.get('energy')}/{player_data.get('energyLimit')} | Turbo Boosts: "
                                       f"{player_data.get('turboBoostersAvailable')} | Energy Boosts: "
                                       f"{player_data.get('fullRechargeBoostersAvailable')}")
                    else:
                        pprint(login)
                        raise ValueError("Login 'kind' != 'success'")
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
                    if time() - last_claimed_time > 3600 * 8:
                        latest = await self.get_latest_claim(http_client)
                        await asyncio.sleep(delay=1)
                        if latest.get('value').get('value').get('hasUnclaimed'):
                            logger.info(f"{self.session_name} | Try to claim daily...")
                            claimed = await self.claim(http_client)
                            if claimed.get('kind') == 'success':
                                last_claimed_time = time()
                                claimed_amount = int(claimed['value']['value'][0]['value']['value'])
                                claimed_streak = claimed['value']['value'][0]['dayNumber']
                                logger.success(f"{self.session_name} | Successful Claimed! | Day {claimed_streak} "
                                               f"<g>+{claimed_amount}</g>")

                        await asyncio.sleep(delay=1)

                    taps = randint(*settings.RANDOM_TAPS_COUNT)

                    if active_turbo:
                        tapped = await self.send_taps(http_client=http_client, taps=taps, turbo=True)

                        if time() - turbo_time > 10:
                            active_turbo = False
                            turbo_time = 0
                    else:
                        tapped = await self.send_taps(http_client, taps=taps, turbo=active_turbo)

                    player_data = await self.get_me(http_client)
                    if not player_data or not tapped.get('kind') == 'success':
                        continue

                    player_data: dict = player_data.get('value')
                    player_tapped: dict = tapped.get('value')
                    available_energy = int(player_tapped.get('energy'))
                    balance = int(player_data['balance'])
                    logger.success(f"{self.session_name} | Successful tapped! | "
                                   f"Balance: <c>{player_tapped.get('balance')}</c> (<g>+{taps}</g>)")

                    turbo_boost_count = player_data['turboBoostersAvailable']
                    energy_boost_count = player_data['fullRechargeBoostersAvailable']

                    next_tap_level = player_data['multitapLevel'] + 1
                    next_energy_level = player_data['energyLimitLevel'] + 1
                    next_charge_level = player_data['rechargeSpeedLevel'] + 1

                    next_tap_price = await self.get_boosters(http_client, booster='multitap', level=next_tap_level)
                    next_energy_price = await self.get_boosters(http_client, booster='energyLimit', level=next_tap_level)
                    next_charge_price = await self.get_boosters(http_client, booster='rechargeSpeed', level=next_tap_level)

                    if active_turbo is False:
                        if (energy_boost_count > 0
                            and available_energy < settings.MIN_AVAILABLE_ENERGY
                                and settings.APPLY_DAILY_ENERGY is True):

                            logger.info(f"{self.session_name} | Sleep 5s before activating the daily energy boost")
                            await asyncio.sleep(delay=5)

                            apply = await self.apply_boost(http_client=http_client, boost_type=self.energy_boost_name)
                            if apply.get('kind') == 'success':
                                logger.success(f"{self.session_name} | Energy boost applied")

                                await asyncio.sleep(delay=1)

                            continue

                        if turbo_boost_count > 0 and settings.APPLY_DAILY_TURBO is True:
                            logger.info(f"{self.session_name} | Sleep 5s before activating the daily turbo boost")
                            await asyncio.sleep(delay=5)

                            apply = await self.apply_boost(http_client=http_client, boost_type=self.turbo_boost_name)
                            if apply.get('kind') is True:
                                logger.success(f"{self.session_name} | Turbo boost applied")

                                await asyncio.sleep(delay=1)

                                active_turbo = True
                                turbo_time = time()

                            continue

                        if (settings.AUTO_UPGRADE_TAP is True
                                and balance > next_tap_price
                                and next_tap_level <= settings.MAX_TAP_LEVEL):
                            logger.info(f"{self.session_name} | Sleep 5s before upgrade tap to {next_tap_level} lvl")
                            await asyncio.sleep(delay=5)

                            level_up = await self.level_up(http_client=http_client, booster='multitap')
                            if level_up.get('kind') == 'success':
                                logger.success(f"{self.session_name} | Tap upgraded to {next_tap_level} lvl")

                                await asyncio.sleep(delay=1)
                            elif level_up.get('kind') == 'error':
                                logger.info(
                                    f"{self.session_name} | Can`t upgrade Tap | Message: {level_up.get('error').get('message')}")

                            continue

                        if (settings.AUTO_UPGRADE_ENERGY is True
                                and balance > next_energy_price
                                and next_energy_level <= settings.MAX_ENERGY_LEVEL):
                            logger.info(
                                f"{self.session_name} | Sleep 5s before upgrade energy to {next_energy_level} lvl")
                            await asyncio.sleep(delay=5)

                            level_up: dict = await self.level_up(http_client=http_client, booster='energyLimit')
                            if level_up.get('kind') == 'success':
                                logger.success(f"{self.session_name} | Energy upgraded to {next_energy_level} lvl")

                                await asyncio.sleep(delay=1)
                            elif level_up.get('kind') == 'error':
                                logger.info(
                                    f"{self.session_name} | Can`t upgrade Energy | Message: {level_up.get('error').get('message')}")

                            continue

                        if (settings.AUTO_UPGRADE_CHARGE is True
                                and balance > next_charge_price
                                and next_charge_level <= settings.MAX_CHARGE_LEVEL):
                            logger.info(
                                f"{self.session_name} | Sleep 5s before upgrade recharge speed to {next_charge_level} lvl")
                            await asyncio.sleep(delay=5)

                            level_up = await self.level_up(http_client=http_client, booster='rechargeSpeed')
                            if level_up.get('kind') == 'success':
                                logger.success(
                                    f"{self.session_name} | Recharge speed upgraded to {next_charge_level} lvl")

                                await asyncio.sleep(delay=1)
                            elif level_up.get('kind') == 'error':
                                logger.info(
                                    f"{self.session_name} | Can`t upgrade Recharge Speed | Message: {level_up.get('error').get('message')}")

                            continue

                        if available_energy < settings.MIN_AVAILABLE_ENERGY:
                            sleep_time = randint(*settings.SLEEP_BY_MIN_ENERGY)
                            logger.info(f"{self.session_name} | Minimum energy reached: {available_energy}")
                            logger.info(f"{self.session_name} | Sleep {sleep_time}s")

                            await asyncio.sleep(delay=sleep_time)

                            continue
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
