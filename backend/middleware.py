from starlette.responses import JSONResponse

from .storage import MAX_UPLOAD


class BodyLimit:
    """Bound the complete request before multipart parsing can spill untrusted data to disk."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope.get('method') not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return await self.app(scope, receive, send)
        limit = MAX_UPLOAD + 65536 if scope['path'].endswith('/evidence') else 1024 * 1024
        headers = dict(scope.get('headers', []))
        try:
            declared = int(headers.get(b'content-length', b'0'))
        except ValueError:
            declared = -1
        if declared < 0:
            return await JSONResponse({'detail': 'Content-Length inválido.'}, status_code=400)(scope, receive, send)
        if declared > limit:
            return await JSONResponse({'detail': 'Requisição excede o limite permitido.'}, status_code=413)(scope, receive, send)
        messages = []
        total = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            total += len(message.get('body', b''))
            if total > limit:
                return await JSONResponse({'detail': 'Requisição excede o limite permitido.'}, status_code=413)(scope, receive, send)
            messages.append(message)
            if not message.get('more_body'):
                break
        index = 0

        async def bounded_receive():
            nonlocal index
            if index < len(messages):
                message = messages[index]
                index += 1
                return message
            return await receive()

        await self.app(scope, bounded_receive, send)
