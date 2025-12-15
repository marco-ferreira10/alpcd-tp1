import typer
import requests
import json
import csv
import sys
import re
from typing_extensions import Annotated
from datetime import datetime


API_KEY = "e6ef9d45d5928e071f7ff064506937dc"

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
   
    _check_api_key()
    user_agent = {"User-Agent": "Mozilla/5.0"}
    base = f"{BASE_URL}{endpoint}"
    parametros = "&".join(f"{k}={v}" for k, v in params.items())
    url_final = f"{base}?api_key={API_KEY}"
    
    if parametros:
        url_final += f"&{parametros}"

    try:
        response = requests.get(url_final, headers=user_agent, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao contactar a API: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    try:
        data = response.json()
    except json.JSONDecodeError:
        print("Erro: resposta da API não é JSON válido.", file=sys.stderr)
        raise typer.Exit(code=1)

    if isinstance(data, dict) and "error" in data:
        msg = data["error"].get("message", "Erro desconhecido da API.")
        print(f"Erro da API: {msg}", file=sys.stderr)
        raise typer.Exit(code=1)

    return data


TEAMLYZER_UA = {"User-Agent": "Mozilla/5.0"}
TEAMLYZER_BASE = "https://pt.teamlyzer.com"


def _slugify_teamlyzer(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s


def _teamlyzer_fetch_company_page(company_slug: str) -> str | None:
    url = f"{TEAMLYZER_BASE}/companies/{company_slug}"
    try:
        r = requests.get(url, headers=TEAMLYZER_UA, timeout=10)
        if r.status_code != 200:
            return None
        return r.text
    except requests.exceptions.RequestException:
        return None


def _teamlyzer_fetch_benefits_page(company_slug: str) -> str | None:
    url = f"{TEAMLYZER_BASE}/companies/{company_slug}/benefits-and-values"
    try:
        r = requests.get(url, headers=TEAMLYZER_UA, timeout=10)
        if r.status_code != 200:
            return None
        return r.text
    except requests.exceptions.RequestException:
        return None


def _teamlyzer_parse_company_info(company_html: str, benefits_html: str | None) -> dict:
    soup = BeautifulSoup(company_html, "html.parser")
    text = soup.get_text("\n", strip=True)

    rating = None
    m = re.search(r"\b(\d+(?:\.\d+)?)\s*/\s*5\b", text)
    if m:
        try:
            rating = float(m.group(1))
        except ValueError:
            rating = None
            
    salary = None
    m = re.search(r"(\d[\d\.\s]*€)\s*-\s*(\d[\d\.\s]*€)", text)
    if m:
        salary = f"{m.group(1).strip()} - {m.group(2).strip()}"

    description = None
    candidates = [line for line in text.split("\n") if len(line) >= 80]
    if candidates:
        description = candidates[0]

    benefits = []
    if benefits_html:
        bsoup = BeautifulSoup(benefits_html, "html.parser")
        btext_lines = [ln.strip() for ln in bsoup.get_text("\n", strip=True).split("\n")]
        for ln in btext_lines:
            if 3 <= len(ln) <= 60 and ln[:1].isupper():
                if ln in {"Toggle navigation", "Seguir", "Escrever review"}:
                    continue
                benefits.append(ln)
                
        seen = set()
        new_benefits = []
        for b in benefits:
            if b not in seen:
                seen.add(b)
                new_benefits.append(b)
        benefits = new_benefits[:10]

    return {
        "teamlyzer_rating": rating,
        "teamlyzer_description": description,
        "teamlyzer_benefits": benefits,
        "teamlyzer_salary": salary,
    }


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
    Alínea (b): listar trabalhos PART-TIME, de uma EMPRESA, numa LOCALIDADE.

    Implementação:
    - usa /job/list.json com type=2 (Part-time)  :contentReference[oaicite:1]{index=1}
    - filtra em Python por nome de empresa e localidade
    """
    localidade_norm = localidade.strip().lower()
    empresa_norm = empresa.strip().lower()

    encontrados: list[dict] = []
    page = 1
    limit_por_pagina = 50

    while len(encontrados) < n:
        data = _get("/job/list.json", {"type": TYPE_PART_TIME, "limit": limit_por_pagina, "page": page})
        jobs = data.get("results", [])
        if not jobs:
            break

        for job in jobs:
            if len(encontrados) >= n:
                break

            company = job.get("company") or {}
            nome_empresa = (company.get("name") or "").lower()
            if empresa_norm not in nome_empresa:
                continue

            locations = job.get("locations") or []
            tem_localidade = any(
                localidade_norm in (loc.get("name") or "").lower()
                for loc in locations
            )
            if not tem_localidade:
                continue

            encontrados.append(job)

        page += 1

    if not encontrados:
        print("Nenhum trabalho encontrado para os critérios.")
        return

    if export_csv:
        _write_to_csv(export_csv, encontrados)
    else:
        print(json.dumps(encontrados, indent=2, ensure_ascii=False))


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
