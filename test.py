from abstract import abs_api
import aiohttp
import logging
from aiohttp import web
import json
import requests
import asyncio
import argparse

logger = logging.getLogger()

parser = argparse.ArgumentParser()

# parser.add_argument('--period', type=int, required=True, help='Survey period')
# parser.add_argument('--rub', type=int, default=0, help='Amount rub')
# parser.add_argument('--usd', type=int, default=0, help='Amount usd')
# parser.add_argument('--eur', type=int, default=0, help='Amount eur')
parser.add_argument('--debug', default=0,
                    choices=['0', '1', 'true', 'false', 'True', 'False', 'y', 'n', 'Y', 'N'],
                    help='Additional info')
cmd_args = parser.parse_args()

def debug(request, response):
    print('Before IF')
    if cmd_args.debug in ['1', 'true', 'True', 'y', 'Y']:
        print('{} / {}'.format(request, response))

class API(abs_api):
    async def parse(self):
        url = 'https://www.cbr-xml-daily.ru/daily_json.js'
        response = requests.get(url)
        print(response.text)

    async def server(self):
        app = web.Application()
        routes = [
            web.route('GET', '/', get_valute),
            web.route('GET', '/amount/get', get_amount),
            web.route('POST', '/modify', modify)
        ]
        app.router.add_routes(routes)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8080)
        await site.start()
        # web.run_app(app, host='localhost', port=8080)

    async def printer(self):
        pass

async def get_valute(request):
        response = {'status': 'currency'}
        headers = {'Content-Type': 'text/plain'}
        debug(request, response)
        return web.Response(text=json.dumps(response), status=200, headers=headers)

async def get_amount(request):
        response = {'status': 'amount'}
        return web.Response(text=json.dumps(response), status=200)

async def modify(request):
        response = {'status': 'modify'}
        return web.Response(text=json.dumps(response), status=200)

async def event_loop():
    tasks = []
    tasks.append(asyncio.create_task(api.parse()))
    tasks.append(asyncio.create_task(api.server()))
    tasks.append(asyncio.create_task(api.printer()))

    while True:
        await asyncio.gather(*tasks)

api = API()

if __name__ == '__main__':
    asyncio.run(event_loop())