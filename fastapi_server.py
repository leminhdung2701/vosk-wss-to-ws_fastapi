from fastapi import FastAPI, Request, WebSocket,WebSocketDisconnect
from vosk import Model, SpkModel, KaldiRecognizer
import uvicorn, json, logging,asyncio, sys, os
import concurrent.futures

app = FastAPI()



class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

def process_chunk(rec, message):
    if message == '{"eof" : 1}':
            return rec.FinalResult(), True
    elif rec.AcceptWaveform(message):
        return rec.Result(), False
    else:
        return rec.PartialResult(), False


async def recognize(websocket):
    global model
    global spk_model
    global args
    global pool

    loop = asyncio.get_running_loop()
    rec = None
    phrase_list = None
    sample_rate = args.sample_rate
    show_words = args.show_words
    max_alternatives = args.max_alternatives
    logging.info('Connection from %s', dict(websocket)["client"]);

    while True:
        # Receive mess from client 
        message = await websocket.receive()
        if 'text' in message: 
            message = message["text"]
        elif 'bytes' in message:
            message = message["bytes"]
            
        # Check config
        if isinstance(message, str) and 'config' in message:
            jobj = json.loads(message)['config']
            logging.info("Config %s", jobj)
            if 'phrase_list' in jobj:
                phrase_list = jobj['phrase_list']
            if 'sample_rate' in jobj:
                sample_rate = float(jobj['sample_rate'])
            if 'words' in jobj:
                show_words = bool(jobj['words'])
            if 'max_alternatives' in jobj:
                max_alternatives = int(jobj['max_alternatives'])
            continue
        
        # Turn recognize
        if not rec:
            if phrase_list:
                rec = KaldiRecognizer(model, sample_rate, json.dumps(phrase_list, ensure_ascii=False))
            else:
                rec = KaldiRecognizer(model, sample_rate)
            rec.SetWords(show_words)
            rec.SetMaxAlternatives(max_alternatives)
            if spk_model:
                rec.SetSpkModel(spk_model)
                
        # Load data from mic
        response, stop = await loop.run_in_executor(pool, process_chunk, rec, message)
        await websocket.send_text(response)
        if stop: break


@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await recognize(websocket)
        
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client left ")
        
def set_arg(args):
    # set up arg
    args.interface = os.environ.get('VOSK_SERVER_INTERFACE', '0.0.0.0')
    args.port = int(os.environ.get('VOSK_SERVER_PORT', 2700))
    args.model_path = os.environ.get('VOSK_MODEL_PATH', 'model')
    args.spk_model_path = os.environ.get('VOSK_SPK_MODEL_PATH')
    args.sample_rate = float(os.environ.get('VOSK_SAMPLE_RATE', 8000))
    args.max_alternatives = int(os.environ.get('VOSK_ALTERNATIVES', 0))
    args.show_words = bool(os.environ.get('VOSK_SHOW_WORDS', True))
    
if __name__ == "__main__":
    
    global model
    global spk_model
    global args
    global pool

    logging.basicConfig(level=logging.INFO)

    args = type('', (), {})()
    set_arg(args)
         
           
    if len(sys.argv) == 1: 
        path = 'vosk-model-en-us-0.22'
    else:
        args.model_path = sys.argv[1]
        path = args.model_path
    model = Model(path)
   
    
    spk_model = SpkModel(args.spk_model_path) if args.spk_model_path else None
    pool = concurrent.futures.ThreadPoolExecutor((os.cpu_count() or 1))
    
    # RUN FastAPI
    uvicorn.run(app,host=args.interface,port = args.port)