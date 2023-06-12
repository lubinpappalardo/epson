from flask import Flask, render_template, request, redirect
import epson_projector as epson
from epson_projector.const import (PWR_OFF)
from epson_projector.const import (POWER)
import asyncio
import aiohttp
import ipaddress

app = Flask(__name__)

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.errorhandler(405)
def method_not_allowed(error):
  return redirect("/")

@app.route('/')
def index():
    onlines = asyncio.run(main('power'))
    return render_template('index.html', log = '', onlines_num = len(onlines), onlines = '<br>'.join(onlines))

@app.post('/shut_down')
def shut_down():
    info_messages = asyncio.run(main('shut_down'))
    onlines = asyncio.run(main('power'))
    if len(info_messages) == 0:
        return render_template('index.html', log = 'No projectors have been turned off', onlines_num = 0, onlines = '')
    return render_template('index.html', log = '<br>'.join(info_messages), onlines_num = len(onlines), onlines = '<br>'.join(onlines))

async def main(action):
    async with aiohttp.ClientSession() as session:
        return await run(session, action)

async def run(websession, action):
    network = ipaddress.ip_network('172.16.16.0/24')
    starting_ip = ipaddress.IPv4Address('172.16.16.100')
    concurrency_limit = 25

    semaphore = asyncio.Semaphore(concurrency_limit)

    if action == 'shut_down':
        tasks = [
            turn_off_projector(websession, str(ip), semaphore)
            for ip in network
            if ip >= starting_ip
        ]
    elif action == 'power':
        tasks = [
            power_status(websession, str(ip), semaphore)
            for ip in network
            if ip >= starting_ip
        ]
    results = await asyncio.gather(*tasks)
    return [result for result in results if result is not None]

async def turn_off_projector(websession, ip, semaphore):
    async with semaphore:
        try:
            projector = epson.Projector(
                host=ip,
                websession=websession
            )
            data = await projector.send_command(PWR_OFF)
            info = f"Projector at {ip} turned off: {data}"
            print(info)
            return info
        except Exception as e:
            info = f"Error turning off projector at {ip}: {e}"
            print(info)
            return None
        
async def power_status(websession, ip, semaphore):
    async with semaphore:
        try:
            projector = epson.Projector(
                host=ip,
                websession=websession
            )
            data = await projector.get_property(POWER)
            info = f"Projector at {ip}: {data}"
            print(info)
            return info
        except Exception as e:
            info = f"Error getting status of projector at {ip}: {e}"
            print(info)
            return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
