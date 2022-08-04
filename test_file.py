import asyncio
import websockets
import sys
import wave
from translate import transform

async def run_test(uri):
    async with websockets.connect(uri) as websocket:
        wf = wave.open('static/F_0560_10y0m_1.wav', "rb")
        await websocket.send('{ "config" : { "sample_rate" : %d } }' % (wf.getframerate()))
        buffer_size = int(wf.getframerate() * 0.2) 
        while True:
            data = wf.readframes(buffer_size)

            if len(data) == 0:
                break

            await websocket.send(data)
            
            data = transform(await websocket.recv())
            if data: print(data)

        await websocket.send('{"eof" : 1}')
        
        data = transform(await websocket.recv())
        if data: print(data)
        
        # print (await websocket.recv())

asyncio.run(run_test('ws://localhost:2700/ws'))