"""Company preparation guides.

IMPORTANT: these are deliberately GENERAL. They summarise only widely published, stable information (for example
that Amazon publishes its Leadership Principles, or that campus recruiters for service companies commonly assess
aptitude, basic coding and communication). They do NOT claim specific questions, cut-offs or round counts, which
change by year, role and campus. Every guide carries a `verify` note pointing students to the employer's official
careers page and their college placement cell for the current process."""

VERIFY = ("Hiring processes change by role, year and campus. Confirm the current stages on the company's official "
          "careers page and with your placement cell; nothing here is a guaranteed or insider pattern.")

COMPANIES = {
    "microsoft": {
        "name": "Microsoft", "category": "Product",
        "focus_topics": ["dsa", "system_design", "os", "dbms", "hr"], "coding_tags": ["arrays", "strings", "trees", "graphs"],
        "themes": ["Strong data-structure and algorithm fundamentals", "Clear problem-solving communication while coding",
                   "Design reasoning for larger roles", "Collaboration and learning mindset in behavioural rounds"],
        "tips": ["Practise explaining your approach before coding.", "Revise OS and DBMS basics alongside DSA.",
                 "Prepare STAR stories about teamwork and learning from feedback."],
    },
    "google": {
        "name": "Google", "category": "Product",
        "focus_topics": ["dsa", "system_design", "cn", "os", "hr"], "coding_tags": ["arrays", "graphs", "dynamic_programming", "trees"],
        "themes": ["Algorithmic problem solving and complexity analysis", "Writing clean code on a plain editor or document",
                   "Reasoning about scale for experienced roles", "General cognitive ability and collaboration"],
        "tips": ["State time and space complexity for every solution.", "Practise problems without autocomplete.",
                 "Think aloud and test your code with examples."],
    },
    "amazon": {
        "name": "Amazon", "category": "Product",
        "focus_topics": ["dsa", "system_design", "dbms", "hr"], "coding_tags": ["arrays", "strings", "trees", "graphs"],
        "themes": ["Amazon publishes its Leadership Principles and uses them in behavioural questions",
                   "Data structures, algorithms and clean coding", "Ownership and customer-focused examples",
                   "Design discussion for experienced roles"],
        "tips": ["Prepare STAR stories mapped to each published Leadership Principle.", "Quantify results in every story.",
                 "Practise coding with edge cases and complexity discussion."],
    },
    "accenture": {
        "name": "Accenture", "category": "Services",
        "focus_topics": ["dbms", "cn", "os", "python", "java", "hr"], "coding_tags": ["arrays", "strings", "basics"],
        "themes": ["Campus drives commonly combine aptitude, technical fundamentals and communication assessment",
                   "Basic programming and problem solving", "Adaptability and client-facing communication"],
        "tips": ["Be fluent in one programming language and core CS fundamentals.", "Practise clear spoken English answers.",
                 "Revise SQL and basic networking questions."],
    },
    "infosys": {
        "name": "Infosys", "category": "Services",
        "focus_topics": ["python", "java", "sql", "dbms", "dsa", "hr"], "coding_tags": ["arrays", "strings", "basics"],
        "themes": ["Campus drives commonly assess aptitude and logical reasoning", "Programming fundamentals and problem solving",
                   "Communication and willingness to learn"],
        "tips": ["Practise aptitude and basic coding under time limits.", "Know your projects end to end.",
                 "Prepare a confident self-introduction."],
    },
    "tcs": {
        "name": "TCS", "category": "Services",
        "focus_topics": ["python", "java", "sql", "dbms", "dsa", "hr"], "coding_tags": ["arrays", "strings", "basics"],
        "themes": ["National-level and campus assessments typically cover aptitude and programming", "Technical and HR interview rounds",
                   "Fundamentals of programming, databases and networking"],
        "tips": ["Revise programming basics and SQL queries.", "Prepare HR answers on relocation, teamwork and strengths.",
                 "Practise coding problems in your strongest language."],
    },
    "deloitte": {
        "name": "Deloitte", "category": "Consulting / Services",
        "focus_topics": ["sql", "dbms", "python", "cn", "hr"], "coding_tags": ["basics", "strings"],
        "themes": ["Consulting-style behavioural and case-flavoured discussion", "Technical fundamentals relevant to the role",
                   "Communication and client-readiness"],
        "tips": ["Structure answers clearly (situation, action, result).", "Be ready to explain any project on your resume.",
                 "Brush up SQL and fundamentals for technology roles."],
    },
}
for _c in COMPANIES.values():
    _c["verify"] = VERIFY
