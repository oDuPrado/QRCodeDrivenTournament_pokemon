# websocket_server.py
import asyncio
import websockets

class WebSocketServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.clients = set()

    async def register(self, websocket):
        """Registra novos clientes."""
        self.clients.add(websocket)
        print(f"Novo cliente conectado: {websocket.remote_address}")
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            print(f"Cliente desconectado: {websocket.remote_address}")

    async def broadcast(self, message):
        """Envia mensagens para todos os clientes conectados."""
        if self.clients:
            await asyncio.gather(*[client.send(message) for client in self.clients])

    async def handler(self, websocket):
        """Gerencia novos clientes."""
        await self.register(websocket)

    async def start(self):
        """Inicia o servidor WebSocket."""
        print(f"Servidor WebSocket iniciado em ws://{self.host}:{self.port}")
        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()  # Mantém o servidor rodando
