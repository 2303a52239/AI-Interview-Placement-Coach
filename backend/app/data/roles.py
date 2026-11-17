"""Role skill profiles used by the skill-gap analyzer. importance: 3 = core, 2 = important, 1 = nice to have.
These are general, publicly understood expectations for each role family, not employer-specific claims."""

ROLES = {
    "Software Developer": {"Data Structures": 3, "Algorithms": 3, "OOP": 3, "SQL": 2, "Git": 2, "System Design": 1,
                           "Operating Systems": 1, "Computer Networks": 1, "Python": 2, "Java": 2},
    "Backend Developer": {"Python": 3, "Java": 2, "SQL": 3, "REST APIs": 3, "Data Structures": 3, "Algorithms": 2,
                          "System Design": 2, "Docker": 2, "Git": 2, "PostgreSQL": 2, "Microservices": 1, "DBMS": 2},
    "Full Stack Developer": {"JavaScript": 3, "React": 3, "Node.js": 2, "SQL": 2, "REST APIs": 3, "HTML": 2, "CSS": 2,
                             "Git": 2, "Data Structures": 2, "TypeScript": 1, "Docker": 1},
    "Data Analyst": {"SQL": 3, "Python": 3, "Pandas": 3, "Data Analysis": 3, "Excel": 2, "Power BI": 2, "Tableau": 1,
                     "NumPy": 2, "Machine Learning": 1},
    "Data Scientist": {"Python": 3, "Machine Learning": 3, "Pandas": 3, "NumPy": 2, "SQL": 2, "Scikit-learn": 3,
                       "Data Analysis": 3, "Deep Learning": 2, "NLP": 1},
    "Machine Learning Engineer": {"Python": 3, "Machine Learning": 3, "Deep Learning": 3, "PyTorch": 2, "TensorFlow": 2,
                                  "Scikit-learn": 2, "SQL": 2, "Docker": 2, "Data Structures": 2, "NLP": 1, "System Design": 1},
    "GenAI Engineer": {"Python": 3, "LLMs": 3, "Generative AI": 3, "RAG": 3, "NLP": 2, "Vector Databases": 2,
                       "Deep Learning": 2, "REST APIs": 2, "LangChain": 1, "Docker": 1, "Hugging Face": 1},
    "DevOps Engineer": {"Linux": 3, "Docker": 3, "Kubernetes": 2, "CI/CD": 3, "AWS": 2, "Git": 2, "Bash": 2,
                        "Terraform": 1, "Computer Networks": 2, "Python": 1},
    "QA / Test Engineer": {"Unit Testing": 3, "Selenium": 2, "Java": 2, "Python": 2, "SQL": 2, "Postman": 2, "Agile": 2, "Git": 1},
}

# skill (canonical) -> interview/coding topic keys that provide measured evidence
SKILL_TOPICS = {
    "Python": ["python"], "Java": ["java"], "SQL": ["sql"], "PostgreSQL": ["sql", "dbms"], "MySQL": ["sql"],
    "DBMS": ["dbms"], "Data Structures": ["dsa", "arrays", "strings", "linked_lists", "trees", "graphs"],
    "Algorithms": ["dsa", "arrays", "dynamic_programming", "sorting", "searching"],
    "Operating Systems": ["os"], "Computer Networks": ["cn"], "Machine Learning": ["ml"], "Deep Learning": ["dl"],
    "NLP": ["nlp"], "Generative AI": ["genai"], "LLMs": ["llm"], "RAG": ["rag"], "System Design": ["system_design"],
    "OOP": ["java", "python"], "Vector Databases": ["rag"], "Scikit-learn": ["ml"], "TensorFlow": ["dl"], "PyTorch": ["dl"],
}

PROFICIENCY_SCORE = {"beginner": 30, "intermediate": 55, "advanced": 75, "expert": 90}

TOPIC_STUDY_NOTES = {
    "python": "Core syntax, data structures, decorators, generators, the GIL, and idiomatic Python.",
    "java": "OOP, collections framework (HashMap internals), exceptions, multithreading, JVM memory and GC.",
    "sql": "Joins, aggregation, window functions, indexes, query plans, transactions and isolation.",
    "dsa": "Arrays/strings, hashing, linked lists, trees, graphs, recursion, DP, complexity analysis.",
    "dbms": "ACID, normalisation, indexing, transactions, concurrency control.",
    "os": "Processes/threads, scheduling, memory management, synchronisation, deadlocks.",
    "cn": "OSI/TCP-IP, TCP vs UDP, HTTP/HTTPS/TLS, DNS, routing basics.",
    "ml": "Supervised/unsupervised learning, bias-variance, evaluation metrics, tree ensembles.",
    "dl": "Backpropagation, CNNs/RNNs, regularisation, transformers and attention.",
    "nlp": "Tokenisation, embeddings, TF-IDF, sequence models, BERT vs GPT.",
    "genai": "Generative model families, prompting, hallucinations, safety and evaluation.",
    "llm": "How LLMs work, sampling parameters, context windows, fine-tuning vs RAG, LoRA.",
    "rag": "Chunking, embeddings, vector search, hybrid retrieval, reranking, evaluation.",
    "system_design": "Scaling, load balancing, caching, databases and CAP, designing common services.",
    "hr": "STAR stories for strengths, conflict, failure, teamwork and motivation.",
}
