import typer
import requests
import json
import csv
import sys
import re
from typing_extensions import Annotated
from datetime import datetime


API_KEY = "COLOCA_AQUI_A_TUA_API_KEY"  

BASE_URL = "http://api.sandbox.itjobs.pt"

TYPE_PART_TIME = 2

LOCATION_IDS = {
    "aveiro": 1,
    "açores": 2,
    "beja": 3,
    "braga": 4,
    "bragança": 5,
    "castelo branco": 6,
    "coimbra": 8,
    "faro": 9,
    "évora": 10,
    "guarda": 11,
    "portalegre": 12,
    "leiria": 13,
    "lisboa": 14,
    "madeira": 15,
    "viseu": 16,
    "setúbal": 17,
    "porto": 18,
    "santarém": 20,
    "vila real": 21,
    "viana do castelo": 22,
    "internacional": 29,
}

LISTA_SKILLS = [
    "python", "java", "sql", "react", "javascript",
    "c#", "aws", "azure", "docker", "php", "c++", "angular"
]

app = typer.Typer(help="CLI para interagir com a API de empregos do ITJobs.")


def _check_api_key():
    if not API_KEY or API_KEY == "COLOCA_AQUI_A_TUA_API_KEY":
        print("Erro: define a API_KEY no ficheiro jobscli.py.", file=sys.stderr)
        raise typer.Exit(code=1)


def _write_to_csv(filename: str, job_list: list):
    """
    Escreve uma lista de trabalhos num ficheiro CSV.
    Campos: titulo, empresa, descrição, data de publicação, salário, localização.
    """
    headers = ["titulo", "empresa", "descrição", "data de publicação", "salário", "localização"]

    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()

            for job in job_list:
                company = job.get("company") or {}
                locations = job.get("locations") or []
                loc_names = " / ".join(loc.get("name", "") for loc in locations)

                row = {
                    "titulo": job.get("title", ""),
                    "empresa": company.get("name", ""),
                    "descrição": (job.get("body", "") or "").strip().replace("\n", " "),
                    "data de publicação": job.get("publishedAt", ""),
                    "salário": job.get("wage", ""),
                    "localização": loc_names,
                }
                writer.writerow(row)

        print(f"Dados exportados com sucesso para {filename}")

    except IOError as e:
        print(f"Erro ao escrever no ficheiro CSV: {e}", file=sys.stderr)


def _normalize_text(html_text: str) -> str:
    """
    Remove tags HTML simples e passa a minúsculas, para facilitar regex.
    """
    if html_text is None:
        html_text = ""
    text = re.sub(r"<[^>]+>", " ", html_text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _get(endpoint: str, params: dict) -> dict:
    """
    Faz pedido GET à API, já com api_key e tratamento de erros.
    endpoint: string do tipo "/job/list.json" ou similar (sem BASE_URL).
    """
    _check_api_key()

    url = f"{BASE_URL}{endpoint}"
    merged_params = dict(params)
    merged_params["api_key"] = API_KEY

    try:
        response = requests.get(url, params=merged_params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao contactar a API: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    try:
        data = response.json()
    except json.JSONDecodeError:
        print("Erro: a resposta da API não é JSON válido.", file=sys.stderr)
        raise typer.Exit(code=1)

    if isinstance(data, dict) and "error" in data:
        msg = data["error"].get("message", "Erro desconhecido da API.")
        print(f"Erro da API: {msg}", file=sys.stderr)
        raise typer.Exit(code=1)

    return data


@app.command(name="top", help="Lista os N trabalhos mais recentes. [Alínea a]")
def get_top_jobs(
    n: Annotated[int, typer.Argument(help="Número de trabalhos a listar.")],
    export_csv: Annotated[str | None, typer.Option(help="Exportar o resultado para um ficheiro CSV.")] = None,
):
    """
    Alínea (a): Listar os N trabalhos mais recentes (JSON; CSV opcional).
    Exemplo: python jobscli.py top 30 --export-csv top.csv
    """
    data = _get("/job/list.json", {"limit": n})
    jobs = data.get("results", [])

    if not jobs:
        print("Nenhum trabalho encontrado para os critérios.")
        return

    if export_csv:
        _write_to_csv(export_csv, jobs)
    else:
        print(json.dumps(jobs, indent=2, ensure_ascii=False))


@app.command(
    name="search",
    help="Lista trabalhos part-time de uma empresa numa localidade. [Alínea b]",
)
def search_jobs(
    localidade: Annotated[str, typer.Argument(help="Localidade (ex: Porto, Lisboa).")],
    empresa: Annotated[str, typer.Argument(help="Nome da empresa a pesquisar.")],
    n: Annotated[int, typer.Argument(help="Número máximo de trabalhos a mostrar.")],
    export_csv: Annotated[str | None, typer.Option(help="Exportar o resultado para um ficheiro CSV.")] = None,
):
    """
    Alínea (b): trabalhos part-time, de uma empresa, numa localidade.
    Exemplo do enunciado: python jobscli.py search Porto EmpresaY 3
    """
    loc_id = LOCATION_IDS.get(localidade.lower())
    if loc_id is None:
        print("Erro: localidade não reconhecida para a API.", file=sys.stderr)
        raise typer.Exit(code=1)

    params = {
        "q": empresa,
        "type": TYPE_PART_TIME,
        "location": loc_id,
        "limit": n,
    }

    data = _get("/job/search.json", params)
    jobs = data.get("results", [])

    if not jobs:
        print("Nenhum trabalho encontrado para os critérios.")
        return

    if export_csv:
        _write_to_csv(export_csv, jobs)
    else:
        print(json.dumps(jobs, indent=2, ensure_ascii=False))


@app.command(name="type", help="Extrai o regime de trabalho (remoto/híbrido/presencial/outro) de um job ID. [Alínea c]")
def get_job_type(
    job_id: Annotated[int, typer.Argument(help="ID interno do trabalho (ex: 125378).")],
):
    """
    Alínea (c): Extrair regime de trabalho de um job id.
    Usa campo allowRemote e expressões regulares sobre title/body/location.
    """
    job_data = _get("/job/get.json", {"id": job_id})

    text_to_search = " ".join([
        job_data.get("title", ""),
        job_data.get("body", ""),
        " ".join(loc.get("name", "") for loc in job_data.get("locations", []) or []),
    ])

    text_norm = _normalize_text(text_to_search)

    allow_remote = bool(job_data.get("allowRemote:") or job_data.get("allowRemote"))

    padrao_hibrido = r"\b(h[íi]brido|hybrid)\b"
    padrao_remoto = r"\b(remoto|remote|teletrabalho|work from home|wfh)\b"
    padrao_presencial = r"\b(presencial|on-site|no escrit[óo]rio)\b"

    tem_hibrido = re.search(padrao_hibrido, text_norm, re.IGNORECASE) is not None
    tem_remoto = allow_remote or (re.search(padrao_remoto, text_norm, re.IGNORECASE) is not None)
    tem_presencial = re.search(padrao_presencial, text_norm, re.IGNORECASE) is not None

    tem_loc = bool(job_data.get("locations"))

    if tem_hibrido:
        print("Híbrido")
    elif tem_remoto and tem_loc:
        print("Híbrido")
    elif tem_remoto:
        print("Remoto")
    elif tem_presencial or tem_loc:
        print("Presencial")
    else:
        print("Outro (ou não especificado)")


@app.command(name="skills", help="Conta skills em anúncios entre duas datas (YYYY-MM-DD). [Alínea d]")
def count_skills_by_date(
    data_inicial: Annotated[str, typer.Argument(help="Data inicial (YYYY-MM-DD).")],
    data_final: Annotated[str, typer.Argument(help="Data final (YYYY-MM-DD).")],
):
    """
    Alínea (d): Contar ocorrências de skills nas descrições entre duas datas.
    Output: lista JSON ordenada por número de ocorrências desc.
    Exemplo: python jobscli.py skills 2025-01-01 2025-01-31
    """
    try:
        dt_start = datetime.strptime(data_inicial, "%Y-%m-%d")
        dt_end = datetime.strptime(data_final, "%Y-%m-%d")
    except ValueError:
        print("Erro: formato de data inválido. Use YYYY-MM-DD.", file=sys.stderr)
        raise typer.Exit(code=1)

    if dt_end < dt_start:
        print("Erro: data_final < data_inicial.", file=sys.stderr)
        raise typer.Exit(code=1)

    contagem_skills: dict[str, int] = {skill: 0 for skill in LISTA_SKILLS}

    padroes = {}
    for skill in LISTA_SKILLS:
        if skill == "c#":
            padroes[skill] = re.compile(r"c#", re.IGNORECASE)
        else:
            padroes[skill] = re.compile(rf"\b{re.escape(skill)}\b", re.IGNORECASE)

    page = 1
    total_filtrados = 0
    stop = False

    while not stop:
        data = _get("/job/list.json", {"limit": 50, "page": page})
        jobs = data.get("results", [])
        if not jobs:
            break

        for job in jobs:
            pub_str = job.get("publishedAt")
            if not pub_str:
                continue

            try:
                pub_dt = datetime.strptime(pub_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

            if pub_dt < dt_start:
                stop = True
                continue
            if pub_dt > dt_end:
                continue

            total_filtrados += 1

            texto_job = (job.get("title", "") or "") + " " + (job.get("body", "") or "")
            texto_norm = _normalize_text(texto_job)

            for skill, padrao in padroes.items():
                matches = padrao.findall(texto_norm)
                if matches:
                    contagem_skills[skill] += len(matches)

        page += 1

    lista_ordenada = sorted(
        ({"skill": s, "count": c} for s, c in contagem_skills.items() if c > 0),
        key=lambda d: d["count"],
        reverse=True,
    )

    print(f"Analisados {total_filtrados} trabalhos entre {data_inicial} e {data_final}.")
    print(json.dumps(lista_ordenada, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    app()
