import asyncio, os, sys, json
from playwright.async_api import async_playwright
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"r")
async def run(shots):
    os.makedirs(OUT,exist_ok=True)
    async with async_playwright() as p:
        b=await p.chromium.launch(args=["--use-gl=angle","--enable-unsafe-swiftshader"])
        pg=await b.new_page(viewport={"width":1440,"height":1140}, device_scale_factor=2)
        errs=[]; pg.on("console", lambda m: errs.append(m.text) if m.type=="error" else None)
        await pg.goto("http://localhost:8123/_render.html")
        await pg.wait_for_function("window.__ready===true", timeout=180000)
        el=await pg.query_selector("#mv")
        for name,opts in shots:
            await pg.evaluate("(o)=>window.setup(o)", opts)
            await el.screenshot(path=f"{OUT}/{name}.png", omit_background=True)
            print("  ->",name, flush=True)
        if errs: print("console:", errs[:3])
        await b.close()
if __name__=="__main__":
    asyncio.run(run(json.load(open(sys.argv[1]))))
