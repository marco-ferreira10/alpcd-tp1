# ALPCD — Trabalho Prático 1

CLI em Python para interação com a API de ofertas de emprego do [itjobs.pt](https://www.itjobs.pt/api/docs).

## Grupo

- João Pires — A110462
- Marco Ferreira — A111550
- Miguel Lopes — A110077

## Dependências

Instalar usando:

    pip install -r requirements.txt

## Configuração

Alterar a variável `API_KEY` no ficheiro `jobscli.py`:

    API_KEY = "A_TUA_API_KEY_AQUI"

Também existe um ficheiro `.env.example` que mostra a variável necessária:

    API_KEY=COLOCAR_AQUI

## Utilização

Executar comandos com:

    python jobscli.py <comando> [opções]

---

## a) Top N ofertas mais recentes

    python jobscli.py top 30
    python jobscli.py top 30 --export-csv top.csv

---

## b) Part-time por empresa e localidade

    python jobscli.py search Porto "EmpresaY" 3
    python jobscli.py search Lisboa "EmpresaX" 5 --export-csv resultados.csv

---

## c) Regime de trabalho de um job id

    python jobscli.py type 123456

---

## d) Contagem de skills entre duas datas

    python jobscli.py skills 2025-01-01 2025-01-31

---

## Ambiente Sandbox vs Produção

Por omissão, o ficheiro `jobscli.py` usa o endpoint:

    http://api.sandbox.itjobs.pt

Para ambiente de produção, substituir no código:

    https://api.itjobs.pt

---

## Exemplo de saída (estrutura JSON)

Exemplo mostrado pelo comando:

    python jobscli.py top 1

Formato da resposta:

    [
      {
        "id": 123456,
        "title": "Software Developer",
        "company": {
          "id": 999,
          "name": "Empresa Exemplo"
        },
        "locations": [
          {"id": 18, "name": "Porto"}
        ],
        "publishedAt": "2025-02-01 14:30:00"
      }
    ]

*(Valores são apenas estruturais — não correspondem a um anúncio real.)*
