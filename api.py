from aiohttp import web


async def root_handler(request):
    return web.json_response({"status": "Made with ❤️ By @cant_think_1"})

async def web_server():
    app = web.Application()
    app.add_routes([web.get("/", root_handler)])
    runner = web.AppRunner(app)
    await runner.setup()
    PORT = 8000
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
