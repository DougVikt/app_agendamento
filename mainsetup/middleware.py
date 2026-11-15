from django.http import HttpResponsePermanentRedirect

class RedirectIPToDomainMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host() # Pega "127.0.0.1:8000" ou "localhost:8000"
        
        # Se o usuário digitou o IP local, joga para o nome 'localhost'
        if host.startswith('127.0.0.1'):
            target = host.replace('127.0.0.1', 'localhost')
            # Mantém http no desenvolvimento (em vez de https)
            return HttpResponsePermanentRedirect(f"http://{target}{request.get_full_path()}")

        return self.get_response(request)
