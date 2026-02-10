from flask import Flask, request, jsonify
import requests
from requests.auth import HTTPBasicAuth

app = Flask(__name__)
PORTA_DEFAULT = 80
USER_DEFAULT = 'admin'
PASSWORD_DEFAULT = 'admin'
IP_DEFAULT = '192.168.0.136'

@app.route('/metrics', methods=['POST'])
def get_metrics():
    # 1. Recebe os dados enviados pelo Zabbix
    req_data = request.get_json()

    # Validação básica
    if not req_data:
        return jsonify({"error": "Invalid JSON body"}), 400

    # Pega os dados ou usa valores padrão (fallback)
    target_ip = req_data.get('ip', IP_DEFAULT)
    target_port = req_data.get('port', PORTA_DEFAULT)
    user = req_data.get('user', USER_DEFAULT)
    password = req_data.get('password', PASSWORD_DEFAULT)

    if not target_ip:
        return jsonify({"error": "IP missing"}), 400

    # Monta a URL para o CGI do Dexin
    url = f"http://{target_ip}:{target_port}/cgi-bin/tuner.cgi"

    # Payload mágico que o equipamento exige
    payload = {
        "h_setflag": "3",
        "edit_ch": "1",
        "h_tuner_type": "1"
    }

    try:
        # 2. Faz a requisição ao equipamento
        # Timeout de 8s para não travar o Zabbix se o equipamento estiver offline
        response = requests.post(
            url,
            data=payload,
            auth=HTTPBasicAuth(user, password),
            timeout=8
        )

        if response.status_code != 200:
            return jsonify({"error": f"HTTP {response.status_code}"}), 502

        # 3. Processamento dos Dados (Parsing)
        raw_data = response.text

        # O retorno é algo como "tuner:1,99,40,..."
        if ":" in raw_data:
            content = raw_data.split(':', 1)[1]
        else:
            # Se não vier no formato esperado, retorna lista vazia
            return jsonify([]), 200

        values = content.split(',')
        zabbix_data = []
        CHUNK_SIZE = 9 # O padrão se repete a cada 9 campos

        for i in range(0, len(values), CHUNK_SIZE):
            chunk = values[i:i+CHUNK_SIZE]

            # Validação: precisa ter 9 campos e o ID não pode ser vazio
            if len(chunk) < 9 or not chunk[0].strip():
                continue

            try:
                # Ignora se o ID for 0 (alguns equipamentos retornam linhas vazias com ID 0)
                if int(chunk[0]) == 0: continue

                # Monta o objeto para o Zabbix
                item = {
                    "{#TUNER_ID}": chunk[0],   # Chave para o LLD (Descoberta)
                    "tuner_id": chunk[0],      # ID do Tuner
                    "quality": int(chunk[3]) if chunk[3].isdigit() else 0, # Qualidade do sinal (%)
                    "strength": int(chunk[4]) if chunk[4].isdigit() else 0, # Intensidade do sinal (%)
                    "cn": float(chunk[6].replace(' dB', '').strip()), # Relação sinal-ruído (dB)
                    "power": float(chunk[7].replace(' dBm', '').strip()), # Potência do sinal (dBm)
                    "ber": chunk[8] # Taxa de erro de bits (BER), pode ser string como "1e-5"
                }
                zabbix_data.append(item)

            except Exception:
                continue # Pula linha se houver erro de conversão

        return jsonify(zabbix_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)