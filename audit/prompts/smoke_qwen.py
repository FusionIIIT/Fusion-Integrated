import json
from urllib.request import Request, urlopen
request = Request("http://127.0.0.1:11434/api/generate", data=json.dumps({"model":"qwen14b-hybrid","prompt":"Reply exactly: QWEN_READY","stream":False,"options":{"num_gpu":8,"num_ctx":4096,"num_predict":20,"temperature":0.1}}).encode(), headers={"Content-Type":"application/json"}, method="POST")
with urlopen(request, timeout=300) as response:
    data = json.load(response)
print(data.get("response"), data.get("done"), data.get("eval_count"))
