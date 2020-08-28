from abstract import abs_api
import logging
from aiohttp import web
import json
import requests
import asyncio
import argparse
from time import time
import copy

# python test.py --period 1 --debug 1 --rub 3000 --eur 1500 --usd 700

parser = argparse.ArgumentParser()
parser.add_argument('--period', type=float, required=True, help='Survey period')
parser.add_argument('--rub', type=float, default=0, help='Amount rub')
parser.add_argument('--usd', type=float, default=0, help='Amount usd')
parser.add_argument('--eur', type=float, default=0, help='Amount eur')
parser.add_argument('--debug', default='0',
                    choices=['0', '1', 'true', 'false', 'True', 'False', 'y', 'n', 'Y', 'N'],
                    help='Additional info')

cmd_args = parser.parse_args()

logger = logging.getLogger()
logging.getLogger('urllib3').setLevel('CRITICAL')
logging.getLogger('asyncio').setLevel('CRITICAL')
logging.getLogger('aiohttp').setLevel('CRITICAL')

# for key in logging.Logger.manager.loggerDict:
#     print(key)


def set_log_props():
    if is_debug():
        logging.basicConfig(level='DEBUG')
    else:
        logging.basicConfig(level='DEBUG', filename='api_log.log')


def is_debug():
    logger.debug('Проверка режима работы api')
    if cmd_args.debug in ['1', 'true', 'True', 'y', 'Y']:
        return True
    else:
        return False


def debug(request, response):
    if is_debug():
        print('debug message')
        if request is not None:
            print(f'Request\n{json.dumps(request, indent=2)}')
        if response is not None:
            print(f'Response\n{json.dumps(response, indent=2)}')

        logger.info('Сообщение от апи в режиме debug')


class API(abs_api):
    is_info = True

    amount = {
        'rub': cmd_args.rub,
        'usd': cmd_args.usd,
        'eur': cmd_args.eur
    }

    rates = {
        'rub_usd': 0,
        'rub_eur': 0,
        'usd_eur': 0
    }

    new_amount = copy.copy(amount)
    new_rates = copy.copy(rates)

    def calc_amount(self):
        logger.debug('Расчет суммы средств')
        try:
            rub = round(self.amount['rub'] + self.amount['usd'] * self.rates['rub_usd'] + self.amount['eur'] * self.rates['rub_eur'], 2)
            usd = round(self.amount['rub'] / self.rates['rub_usd'] + self.amount['usd'] + self.amount['eur'] * self.rates['usd_eur'], 2)
            eur = round(self.amount['rub'] / self.rates['rub_eur'] + self.amount['usd'] / self.rates['usd_eur'] + self.amount['eur'], 2)
        except Exception as ex:
            logger.error(f'{str(ex)}')
        else:
            return rub, usd, eur

    def all_info(self):
        logger.debug('Вывод основной информации')
        rub, usd, eur = self.calc_amount()

        response = {
            'rub': self.amount['rub'],
            'usd': self.amount['usd'],
            'eur': self.amount['eur'],

            'rub_usd': self.rates['rub_usd'],
            'rub_eur': self.rates['rub_eur'],
            'usd_eur': self.rates['usd_eur'],

            'sum': f'{rub} rub / {usd} usd / {eur} eur'
        }

        return response

    def get_response(self, response):
        logger.debug('Добавление text/plain')
        headers = {'Content-Type': 'text/plain'}
        return web.Response(text=json.dumps(response), status=200, headers=headers)

    def change_handler(self):
        logger.debug('Отслеживание изменений состояния счета')
        if self.new_amount != self.amount or self.new_rates != self.rates:
            self.is_info = True
            self.new_amount = copy.copy(self.amount)
            self.new_rates = copy.copy(self.rates)

    async def request_from_api(self):
        while True:
            logger.warning('Запрос курсов валют')
            url = 'https://www.cbr-xml-daily.ru/daily_json.js'
            response = requests.get(url)

            await self.parse(response)
            await asyncio.sleep(cmd_args.period * 60)

    async def parse(self, response):
        logger.debug('Парсинг курсов нужных валют')
        self.rates['rub_usd'] = response.json()['Valute']['USD']['Value']
        self.rates['rub_eur'] = response.json()['Valute']['EUR']['Value']
        self.rates['usd_eur'] = round(self.rates['rub_eur']/self.rates['rub_usd'], 4)
        self.change_handler()

    async def start_background_tasks(self, app):
        logger.debug('run background tasks')
        app['request_from_api'] = asyncio.create_task(self.request_from_api())
        app['printer'] = asyncio.create_task(self.printer())

    def server(self):
        logger.debug('Запуск сервера')
        app = web.Application()
        routes = [
            web.route('GET', '/usd/get', self.get_usd),
            web.route('GET', '/rub/get', self.get_rub),
            web.route('GET', '/eur/get', self.get_eur),
            web.route('GET', '/amount/get', self.get_amount),
            web.route('POST', '/amount/set', self.post_amount_set),
            web.route('POST', '/modify', self.post_modify)
        ]
        app.router.add_routes(routes)

        app.on_startup.append(self.start_background_tasks)
        web.run_app(app=app, host='localhost', port=8080)

        # runner = web.AppRunner(app)
        # await runner.setup()
        # site = web.TCPSite(runner, 'localhost', 8080)
        # await site.start()

    async def printer(self):
        while True:
            if self.is_info:
                try:
                    logger.debug('Консольный вывод')
                    self.is_info = False
                    info = self.all_info()
                    print(json.dumps(info, indent=2))
                except Exception as ex:
                    logger.error(f'{str(ex)}')
            else:
                logger.info('state no changed')

            await asyncio.sleep(60)

    async def get_usd(self, request):
        logger.info('Запрос валюты usd')
        response = {'usd': self.amount['usd']}
        debug(None, response)
        return self.get_response(response)

    async def get_rub(self, request):
        logger.info('Запрос валюты rub')
        response = {'rub': self.amount['rub']}
        debug(None, response)
        return self.get_response(response)

    async def get_eur(self, request):
        logger.info('Запрос валюты eur')
        response = {'eur': self.amount['eur']}
        debug(None, response)
        return self.get_response(response)

    async def get_amount(self, request):
        logger.info('Запрос общей информации')
        response = self.all_info()
        debug(None, response)
        return self.get_response(response)

    async def post_amount_set(self, request):
        logger.info('Запрос на установку нового значания валют(-ы)')
        try:
            body = await request.json()

            for key in body.keys():
                self.amount[key] = body[key]
        except Exception as ex:
            logger.error(f'{str(ex)}')
            response = {'message': 'The request body was filled incorrectly'}
            return self.get_response(response)
        else:
            self.change_handler()
            response = self.amount
            debug(body, response)
            return self.get_response(response)

    async def post_modify(self, request):
        logger.info('Запрос на изменение значения валют(-ы) на некоторое(-ые) значение(-ия)')
        try:
            body = await request.json()

            for key in body.keys():
                self.amount[key] += body[key]
        except Exception as ex:
            logger.error(f'{str(ex)}')
            response = {'message': 'The request body was filled incorrectly'}
            return self.get_response(response)
        else:
            self.change_handler()
            response = self.amount

            debug(body, response)
            return self.get_response(response)


def timer():
    return time() / 60


if __name__ == '__main__':
    api = API()
    logger.info('START_APP')
    set_log_props()

    if is_debug():
        debug(None, None)
    else:
        print('Server is started')

    api.server()
