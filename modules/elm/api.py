from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

class ELMBackend(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(ELMBackend, self).dispatch(*args, **kwargs)

    def get(self, request):
        return JsonResponse({"message": "ELM backend is up and running."})

    def post(self, request):
        data = json.loads(request.body)
        # Handle the POST request data
        return JsonResponse({"received": data})
