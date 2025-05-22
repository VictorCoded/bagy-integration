import requests

headers = {
    "Authorization": "Bearer SEU_TOKEN_AQUI",
    "Content-Type": "application/json"
}

try:
    response = requests.get("https://api.bagy.com.br/v2/products", headers=headers, timeout=10)
    print("Status:", response.status_code)
    print("Resposta:", response.text)
except Exception as e:
    print("❌ Erro ao conectar:", e)
