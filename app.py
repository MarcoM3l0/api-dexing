from flask import Flask, request, jsonify
import requests
from requests.auth import HTTPBasicAuth

app = Flask(__name__)

# Configurações padrão para conexão com equipamentos Dexin
CONFIG = {
    "PORTA_DEFAULT": 80,                # Porta HTTP padrão do CGI
    "USER_DEFAULT": "admin",            # Usuário padrão do equipamento
    "PASSWORD_DEFAULT": "admin",        # Senha padrão do equipamento
    "IP_DEFAULT": "192.168.0.136",      # IP padrão (fallback)
    "TIMEOUT": 8,                       # Timeout em segundos para evitar travar o Zabbix    
    "CHUNK_SIZE": 9                     # Quantidade de campos por tuner na resposta do CGI
}


@app.route("/metrics", methods=["POST"])
def get_metrics():
    """
    Endpoint principal que recebe requisições do Zabbix e retorna métricas dos tuners.
    
    Payload esperado (JSON):
        - ip: IP do equipamento Dexin
        - port: Porta HTTP (padrão: 80)
        - user: Usuário de autenticação
        - password: Senha de autenticação
    
    Retorna:
        Lista de objetos com métricas de cada tuner (quality, strength, cn, power, ber)
    """
    # 1. Recebe os dados enviados pelo Zabbix
    req_data = request.get_json()

    if not req_data:
        return jsonify({"error": "Invalid JSON body"}), 400

    # Extrai parâmetros da requisição ou usa valores padrão
    target_ip = req_data.get("ip", CONFIG["IP_DEFAULT"])
    target_port = req_data.get("port", CONFIG["PORTA_DEFAULT"])
    user = req_data.get("user", CONFIG["USER_DEFAULT"])
    password = req_data.get("password", CONFIG["PASSWORD_DEFAULT"])

    if not target_ip:
        return jsonify({"error": "IP missing"}), 400

    # Monta a URL para o CGI, do Dexin, que retorna dados dos tuners
    url = f"http://{target_ip}:{target_port}/cgi-bin/tuner.cgi"
    payload = {"h_setflag": "3", "edit_ch": "1", "h_tuner_type": "1"}

    try:
        # 2. Faz a requisição ao equipamento
        # Requisição HTTP ao equipamento Dexin usando autenticação básica e timeout para evitar travamentos
        response = requests.post(
            url,
            data=payload,
            auth=HTTPBasicAuth(user, password),
            timeout=CONFIG["TIMEOUT"],
        )

        if response.status_code != 200:
            return jsonify({"error": f"HTTP {response.status_code}"}), 502

        # 3. Processamento dos Dados (Parsing)
        raw_data = response.text

        # O retorno é algo como "tuner:1,99,40,..."
        if ":" in raw_data:
            content = raw_data.split(":", 1)[1]
        else:
            # Se não vier no formato esperado, retorna lista vazia
            return jsonify([]), 200

        content = raw_data.split(":", 1)[1] 
        values = content.split(",")

        return jsonify(parse_turner_data(values))
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out"}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Connection error: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def parse_turner_data(values):
    """
    Processa lista de valores brutos retornados pelo equipamento Dexin.

    Formato esperado: cada tuner possui 9 campos separados por vírgula
    [0]=ID, [1-2]=reservados, [3]=quality, [4]=strength, [5]=reservado,
    [6]=cn(dB), [7]=power(dBm), [8]=ber

    Args:
        values: Lista de strings com valores brutos separados por vírgula

    Returns:
        Lista de dicionários prontos para o Zabbix LLD
    """
    zabbix_data = []

    # Itera sobre chunks de 9 valores (cada chunk = 1 tuner)
    for i in range(0, len(values), CONFIG["CHUNK_SIZE"]):
        chunk = values[i : i + CONFIG["CHUNK_SIZE"]]

        if len(chunk) < CONFIG["CHUNK_SIZE"] or not chunk[0].strip():
            # Se o chunk tiver menos de 9 valores ou o ID estiver vazio, ignora
            continue

        try:
            # Ignora tuners com ID 0 (linhas vazias do equipamento)
            turne_id = int(chunk[0])

            if turne_id == 0: continue

            # Monta objeto no formato esperado pelo Zabbix
            item = {
                "{#TUNER_ID}": str(turne_id),  # Macro para LLD
                "tuner_id": str(turne_id),
                "quality": int(chunk[3]) if chunk[3].isdigit() else 0,
                "strength": int(chunk[4]) if chunk[4].isdigit() else 0,
                "cn": float(chunk[6].replace(" db", "").strip()),
                "power": float(chunk[7].replace(" dbm", "").strip()),
                "ber": float(chunk[8].strip()),
            }

            zabbix_data.append(item)

        except (ValueError, IndexError):
            # Pula tuners com dados inválidos ou incompletos
            continue

    return zabbix_data


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
