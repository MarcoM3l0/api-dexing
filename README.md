# Dexing NDS3508B Zabbix Middleware

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Microservice-green?style=for-the-badge&logo=flask&logoColor=white)
![Zabbix](https://img.shields.io/badge/Zabbix-Monitoring-red?style=for-the-badge&logo=zabbix&logoColor=white)

Middleware de integração (API Gateway) desenvolvido em Python para permitir o monitoramento escalável, seguro e performático de equipamentos receptores de TV Digital (Dexing NDS3508B) através do Zabbix.

## 🎯 O Cenário e o Problema

Em operações de ISP e TV Digital, os receptores **Dexing NDS3508B** são equipamentos críticos para a recepção de sinais via satélite ou terrestre. No entanto, o monitoramento desses dispositivos apresenta desafios técnicos significativos:

1.  **Limitação de Hardware:** O servidor web embarcado no equipamento é legado e possui baixa capacidade de CPU. Múltiplas requisições simultâneas (comuns em sistemas de monitoramento como o Zabbix) causam travamento da interface de gerenciamento ou reboot involuntário do equipamento.
2.  **Ausência de SNMP Completo:** O equipamento não fornece via SNMP as métricas vitais de sinal RF (como BER, C/N e Power de cada Tuner individualmente).
3.  **Interface Web Complexa:** Os dados são exibidos apenas em uma interface web baseada em CGI/Frames antigos, dificultando a extração direta.

## 🛠️ A Solução

Desenvolvi um **Middleware** que atua como um proxy inteligente entre o Zabbix e o parque de equipamentos.

A solução utiliza **Engenharia Reversa** para comunicar-se diretamente com os endpoints CGI ocultos do equipamento (`tuner.cgi`), extraindo os dados brutos, tratando erros e entregando um JSON estruturado para o Zabbix.

### Principais Benefícios:
* **Proteção do Legado:** Reduz a carga no equipamento. O Zabbix faz apenas **uma requisição** centralizada (ex: a cada 5 minutos), e o Middleware gerencia a conexão e o parsing.
* **Auto-Discovery (LLD):** O JSON gerado é compatível com o *Low-Level Discovery* do Zabbix, permitindo a criação dinâmica de gráficos para os 16 tuners de cada chassi automaticamente.
* **Dados em Tempo Real:** Monitoramento de **Quality, Strength, C/N (dB), Power (dBm) e BER**.

## 🏗️ Arquitetura

O sistema foi desenhado para rodar isolado (em Container ou VM), atuando como um **Proxy de Tradução**. Isso garante que o servidor Zabbix nunca acesse diretamente o equipamento legado, protegendo-o de sobrecarga.

### Fluxo de Dados

1.  **Solicitação (Zabbix → Middleware):**
    O Zabbix realiza um `HTTP POST` centralizado (ex: a cada 5 minutos) para a API, enviando as credenciais e o IP do alvo via JSON.

2.  **Coleta (Middleware → Dexin):**
    O script Python autentica-se no equipamento usando *HTTP Basic Auth* e consome o endpoint oculto `/cgi-bin/tuner.cgi`, emulando uma requisição interna legítima.

3.  **Processamento (Interno):**
    O Middleware recebe os dados brutos (texto não estruturado/separado por vírgulas), realiza a limpeza, trata exceções de conexão e converte os valores para tipos numéricos (Float/Int).

4.  **Entrega (Middleware → Zabbix):**
    Um JSON padronizado e compatível com *Zabbix LLD* é retornado, contendo métricas de qualidade, força, C/N, potência e BER de todos os tuners disponíveis.


## 🚀 Tecnologias Utilizadas

O projeto foi desenvolvido utilizando uma stack leve e eficiente, focada em estabilidade para ambientes de produção crítica.

* **Linguagem:** [Python 3.8+](https://www.python.org/)
    * Utilizado pela robustez em manipulação de strings e facilidade em realizar engenharia reversa de chamadas HTTP.
* **Framework Web:** [Flask](https://flask.palletsprojects.com/)
    * Microframework escolhido para criar uma API RESTful rápida e com baixo *overhead* de memória.
* **Networking:** [Requests](https://requests.readthedocs.io/)
    * Biblioteca para gerenciamento de requisições HTTP complexas, incluindo autenticação *Basic Auth* e tratamento de *timeouts*.
* **Servidor de Aplicação:** [Gunicorn](https://gunicorn.org/)
    * Servidor WSGI utilizado para gerenciar a aplicação em produção, permitindo múltiplos *workers* simultâneos para atender a alta demanda de coleta.
* **Monitoramento:** [Zabbix](https://www.zabbix.com/)
    * Integração via *HTTP Agent* nativo, utilizando recursos avançados como *Low-Level Discovery (LLD)* e pré-processamento via *JSONPath*.

## ✅ Requisitos Mínimos

Para executar o middleware em ambiente de produção com estabilidade, recomenda-se:

* **Sistema Operacional:** Linux (Ubuntu 20.04+, Debian 11+ ou CentOS 8+).
    * *Nota: Compatível com Windows para fins de desenvolvimento.*
* **Runtime:** [Python 3.8](https://www.python.org/downloads/) ou superior.
* **Gerenciador de Pacotes:** Pip (instalado via `apt install python3-pip` ou equivalente).
* **Monitoramento:** Zabbix Server 6.0 LTS ou superior.
    * *Recomendado devido ao suporte nativo e otimizado para o tipo de item "HTTP Agent".*
* **Hardware (VM/Container):**
    * **vCPU:** 1 Core
    * **RAM:** 512MB (A aplicação consome ~150MB em carga)
    * **Disco:** 10GB
* **Rede:** Conectividade HTTP (Porta 80) com os equipamentos Dexing e acessibilidade pelo Zabbix Server na porta da API (padrão 5000).

## 🚀 Como Usar

### Instalação

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/Ronec1r/api-dexing.git](https://github.com/Ronec1r/api-dexing.git)
    cd api-dexing
    ```

2.  **Crie um ambiente virtual e instale as dependências:**
    Recomenda-se o uso de *virtualenv* para isolar as bibliotecas do projeto.
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    pip install flask requests gunicorn
    ```

### 🖥️ Execução (Modo Desenvolvimento)

Ideal para testes locais, validação de funcionamento e visualização de logs de erro em tempo real no terminal.

```bash
python app.py
```

A aplicação iniciará na porta 5000 por padrão. Para interromper, pressione Ctrl+C.

### 🏭 Execução (Modo Produção)

Para ambientes de produção, **não utilize** o servidor de desenvolvimento do Flask. Recomenda-se o uso do **Gunicorn** para gerenciar múltiplos processos e garantir estabilidade sob carga.

**Comando:**
```bash
gunicorn --workers 4 --bind 0.0.0.0:5000 app:app
```
* workers 4: Define 4 processos simultâneos (ideal para não bloquear a API enquanto um equipamento lento responde).
* bind 0.0.0.0:5000: Torna a API acessível externamente na porta 5000.

## 🔌 Referência da API

O Middleware expõe um único endpoint para comunicação com o Zabbix.

### Obter Métricas

**Rota:** `/metrics`
**Método:** `POST`

#### Corpo da Requisição (Input)

| Parâmetro  | Tipo   | Obrigatório | Descrição                                  |
| :---       | :---   | :---        | :---                                       |
| `ip`       | string | **Sim** | Endereço IP do equipamento Dexin.          |
| `port`     | int    | Não         | Porta da interface web (Padrão: `80`).     |
| `user`     | string | Não         | Usuário de login (Padrão: `admin`).        |
| `password` | string | Não         | Senha de login (Padrão: `admin`).          |

**Exemplo de Payload:**

```json
{
  "ip": "192.168.0.136",
  "port": 80,
  "user": "admin",
  "password": "admin"
}
```

### 📤 Resposta (Output)

A API retorna uma lista (array) de objetos JSON, onde cada objeto representa os dados de um Tuner específico.

```json
[
  {
    "{#TUNER_ID}": "1",       // Macro utilizada pelo Zabbix LLD
    "tuner_id": "1",          // ID limpo para uso em filtros JSONPath
    "quality": 98,            // Qualidade do Sinal (%)
    "strength": 45,           // Intensidade do Sinal (%)
    "cn": 31.5,               // Relação Sinal-Ruído (dB)
    "power": -50.2,           // Potência de Entrada (dBm)
    "ber": "0.00e+00"         // Bit Error Rate (Taxa de Erro)
  },
  {
    "{#TUNER_ID}": "2",
    "tuner_id": "2",
    "quality": 0,             // Exemplo de tuner sem sinal
    "strength": 0,
    "cn": 0.0,
    "power": 0.0,
    "ber": "0.000"
  }
]
```

## 📊 Configuração no Zabbix

A integração é feita nativamente usando o tipo de item **HTTP agent**. Não é necessário instalar scripts externos ou *sender* no servidor Zabbix.

### 1. Criar o Item Mestre (Master Item)

Este item será responsável por fazer a requisição única à API e guardar o JSON completo.

* **Name:** Dexing API
* **Type:** HTTP agent
* **Key:** `dexing.api.get`
* **URL:** `http://<IP_DO_MIDDLEWARE>:5000/metrics`
* **Request method:** POST
* **Request body type:** JSON data
* **Request body:**
    ```json
    {
      "ip": "{HOST.CONN}",
      "port": "{$DEXING_PORT}",
      "user": "{$DEXING_USER}",
      "password": "{$DEXING_PASS}"
    }
    ```
* **Type of information:** Text
* **History storage:** Do not keep history (Opcional, para economizar espaço).

### 2. Criar a Regra de Descoberta (LLD)

Esta regra lerá o JSON do item mestre e criará um "Objeto" para cada Tuner encontrado.

* **Name:** Descoberta de Tuners
* **Type:** Dependent item
* **Master item:** Dexing API
* **Key:** `dexing.discovery`
* **LLD macros:**
    * `{#TUNER_ID}` → `$.['{#TUNER_ID}']`

### 3. Criar os Protótipos de Itens (Item Prototypes)

Crie os itens para as métricas desejadas (Quality, C/N, Power, etc). Todos devem ser do tipo **Dependent item**.

**Exemplo: Configuração do C/N (Sinal/Ruído)**

* **Name:** Tuner {#TUNER_ID} - CN
* **Type:** Dependent item
* **Master item:** Dexing API
* **Key:** `dexing.cn[{#TUNER_ID}]`
* **Type of information:** Numeric (float)
* **Units:** dB
* **Preprocessing Steps (Essencial):**
    1.  **JSONPath:**
        ```
        $[?(@.tuner_id == '{#TUNER_ID}')].cn.first()
        ```

**Outros JSONPaths úteis:**

* **Power (dBm):** `$[?(@.tuner_id == '{#TUNER_ID}')].power.first()`
* **Quality (%):** `$[?(@.tuner_id == '{#TUNER_ID}')].quality.first()`
* **Strength (%):** `$[?(@.tuner_id == '{#TUNER_ID}')].strength.first()`
* **BER:** `$[?(@.tuner_id == '{#TUNER_ID}')].ber.first()`