"""Skill taxonomy shared by resume analysis, JD matching, skill-gap analysis and roadmaps.

Each canonical skill has a category and a list of aliases that may appear in resumes / job descriptions.
Matching is dictionary based (no ML model): `find_skills(text)` returns canonical names."""
import re
from typing import Dict, List, Set

# canonical name -> (category, aliases)
_RAW: Dict[str, tuple] = {
    # languages
    "Python": ("language", ["python3", "python 3"]),
    "Java": ("language", ["core java", "java 8", "java 11", "java 17"]),
    "C++": ("language", ["cpp", "c plus plus"]),
    "C": ("language", []),
    "C#": ("language", ["c sharp"]),
    "JavaScript": ("language", ["js", "ecmascript", "es6"]),
    "TypeScript": ("language", ["ts"]),
    "Go": ("language", ["golang"]),
    "Rust": ("language", []),
    "Kotlin": ("language", []),
    "Swift": ("language", []),
    "R": ("language", []),
    "Scala": ("language", []),
    "PHP": ("language", []),
    "Bash": ("language", ["shell scripting", "shell script"]),
    # web / frameworks
    "React": ("framework", ["react.js", "reactjs"]),
    "Angular": ("framework", ["angularjs"]),
    "Vue": ("framework", ["vue.js", "vuejs"]),
    "Node.js": ("framework", ["nodejs", "node js"]),
    "Express": ("framework", ["express.js", "expressjs"]),
    "Django": ("framework", []),
    "Flask": ("framework", []),
    "FastAPI": ("framework", ["fast api"]),
    "Spring Boot": ("framework", ["springboot"]),
    "Spring": ("framework", ["spring framework", "spring mvc"]),
    "Hibernate": ("framework", ["jpa"]),
    ".NET": ("framework", ["dotnet", ".net core", "asp.net"]),
    "HTML": ("web", ["html5"]),
    "CSS": ("web", ["css3"]),
    "Tailwind CSS": ("web", ["tailwind", "tailwindcss"]),
    "Bootstrap": ("web", []),
    "Redux": ("web", []),
    "REST APIs": ("backend", ["rest api", "restful", "rest apis", "restful api", "restful apis", "rest"]),
    "GraphQL": ("backend", []),
    "Microservices": ("backend", ["microservice"]),
    # databases
    "SQL": ("database", ["structured query language"]),
    "MySQL": ("database", []),
    "PostgreSQL": ("database", ["postgres", "psql"]),
    "MongoDB": ("database", ["mongo"]),
    "SQLite": ("database", []),
    "Oracle": ("database", ["oracle db", "pl/sql"]),
    "Redis": ("database", []),
    "Elasticsearch": ("database", ["elastic search"]),
    "DBMS": ("cs_fundamentals", ["database management", "database management systems", "normalization"]),
    # cloud / devops
    "AWS": ("cloud", ["amazon web services", "ec2", "s3", "lambda"]),
    "Azure": ("cloud", ["microsoft azure"]),
    "GCP": ("cloud", ["google cloud", "google cloud platform"]),
    "Docker": ("devops", ["containerization", "containers"]),
    "Kubernetes": ("devops", ["k8s"]),
    "CI/CD": ("devops", ["cicd", "ci cd", "continuous integration", "continuous delivery"]),
    "Jenkins": ("devops", []),
    "Git": ("tools", ["version control"]),
    "GitHub": ("tools", []),
    "Linux": ("tools", ["unix"]),
    "Terraform": ("devops", []),
    # data / ml / ai
    "Machine Learning": ("ai_ml", ["ml"]),
    "Deep Learning": ("ai_ml", ["dl", "neural networks", "neural network", "cnn", "rnn"]),
    "NLP": ("ai_ml", ["natural language processing"]),
    "Generative AI": ("ai_ml", ["genai", "gen ai", "generative ai"]),
    "LLMs": ("ai_ml", ["llm", "large language models", "large language model", "gpt", "prompt engineering"]),
    "RAG": ("ai_ml", ["retrieval augmented generation", "retrieval-augmented generation"]),
    "Computer Vision": ("ai_ml", ["opencv", "image processing"]),
    "TensorFlow": ("ai_ml", []),
    "PyTorch": ("ai_ml", []),
    "Keras": ("ai_ml", []),
    "Scikit-learn": ("ai_ml", ["sklearn", "scikit learn"]),
    "Pandas": ("data", []),
    "NumPy": ("data", ["numpy"]),
    "Data Analysis": ("data", ["data analytics", "exploratory data analysis", "eda"]),
    "Data Science": ("data", []),
    "Power BI": ("data", ["powerbi"]),
    "Tableau": ("data", []),
    "Excel": ("data", ["microsoft excel", "ms excel"]),
    "Hugging Face": ("ai_ml", ["huggingface", "transformers"]),
    "LangChain": ("ai_ml", []),
    "Vector Databases": ("ai_ml", ["pgvector", "faiss", "pinecone", "chroma", "vector database", "vector db"]),
    # cs fundamentals
    "Data Structures": ("cs_fundamentals", ["dsa", "data structure"]),
    "Algorithms": ("cs_fundamentals", ["algorithm", "problem solving", "competitive programming"]),
    "Operating Systems": ("cs_fundamentals", ["os concepts", "operating system"]),
    "Computer Networks": ("cs_fundamentals", ["networking", "computer networking", "tcp/ip"]),
    "OOP": ("cs_fundamentals", ["object oriented programming", "object-oriented programming", "oops", "object oriented"]),
    "System Design": ("cs_fundamentals", ["low level design", "high level design", "lld", "hld", "distributed systems"]),
    # practices / testing
    "Agile": ("practice", ["scrum", "kanban"]),
    "Unit Testing": ("practice", ["junit", "pytest", "unittest", "jest", "test driven development", "tdd"]),
    "Selenium": ("practice", []),
    "Postman": ("tools", []),
    "Jira": ("tools", []),
}

SKILLS: Dict[str, str] = {name: cat for name, (cat, _a) in _RAW.items()}
_ALIAS_TO_CANON: Dict[str, str] = {}
for _name, (_cat, _aliases) in _RAW.items():
    _ALIAS_TO_CANON[_name.lower()] = _name
    for _a in _aliases:
        _ALIAS_TO_CANON.setdefault(_a.lower(), _name)

# longest first so "spring boot" wins over "spring"
_TERMS = sorted(_ALIAS_TO_CANON, key=len, reverse=True)
_PATTERNS = {t: re.compile(r"(?<![A-Za-z0-9+#])" + re.escape(t) + r"(?![A-Za-z0-9+#])", re.IGNORECASE) for t in _TERMS}
# single-letter / ambiguous skills need a programming context to avoid matching prose ("C", "R", "Go", "Rest")
_AMBIGUOUS = {"c", "r", "go", "rest", "ts", "js", "ml", "dl", "os", "spring", "oracle"}


def canonical(name: str) -> str:
    return _ALIAS_TO_CANON.get((name or "").strip().lower(), (name or "").strip())


def category_of(name: str) -> str:
    return SKILLS.get(canonical(name), "general")


def find_skills(text: str) -> List[str]:
    """Canonical skills mentioned in `text`, in order of first appearance."""
    if not text:
        return []
    found: Dict[str, int] = {}
    consumed = []  # (start, end) spans already claimed by a longer term

    for term in _TERMS:
        for m in _PATTERNS[term].finditer(text):
            s, e = m.span()
            if any(s < ce and e > cs for cs, ce in consumed):
                continue
            raw = text[s:e]
            if term in _AMBIGUOUS:
                # only count when written as a standalone token in typical skill style:
                # exact original casing (e.g. "C", "R", "Go") AND listed with separators nearby
                if raw != raw.upper() and raw != term.capitalize() and raw != term:
                    continue
                prev_ch = text[:s].rstrip(" \t")[-1:]
                next_ch = text[e:].lstrip(" \t")[:1]
                seps = ",;|/•·:\n"
                if term not in {"spring", "oracle", "rest"} and not (prev_ch in seps or prev_ch == "" or next_ch in seps or next_ch == ""):
                    continue
                if term in {"rest"} and not re.search(r"api|restful|services?", text[max(0, s - 12): e + 14], re.IGNORECASE):
                    continue
            consumed.append((s, e))
            canon = _ALIAS_TO_CANON[term]
            found.setdefault(canon, s)
    return [k for k, _ in sorted(found.items(), key=lambda kv: kv[1])]


def skills_by_category(names: List[str]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for n in names:
        out.setdefault(category_of(n), []).append(canonical(n))
    return out


ALL_SKILLS: Set[str] = set(SKILLS)
