"""
Seeds the database with demo data so the app can be evaluated immediately
after installation:
  - A demo user (see README for credentials)
  - A demo profile with skills/target role
  - A sample resume record (no file, just extracted fields) for the dashboard
  - A bank of Java coding questions with real test cases
  - One completed HR interview and one completed Technical interview with
    realistic scored answers, so charts/history are populated on first login
  - A generated preparation plan

Run with:  python -m scripts.seed   (from the backend/ directory, venv active)
"""
import json
import datetime as dt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine, SessionLocal
from app import models  # noqa: F401
from app.models.user import User, Profile
from app.models.resume import Resume, Skill, Project
from app.models.interview import Interview, InterviewQuestion, InterviewAnswer, Evaluation
from app.models.coding import CodingQuestion, CodingSubmission
from app.models.performance import PerformanceSnapshot
from app.utils.security import hash_password
from app.services.prep_plan_service import generate_preparation_plan

DEMO_EMAIL = "demo@student.com"
DEMO_PASSWORD = "Demo@1234"


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if existing:
            print(f"Demo user '{DEMO_EMAIL}' already exists. Skipping user/interview seed, "
                  f"will still ensure coding question bank exists.")
            user = existing
        else:
            user = User(
                name="Demo Student",
                email=DEMO_EMAIL,
                hashed_password=hash_password(DEMO_PASSWORD),
                is_admin=0, role="student",
            )
            db.add(user)
            db.flush()

            profile = Profile(
                user_id=user.id,
                college="Indian Institute of Technology (Demo)",
                degree="B.Tech Computer Science",
                target_role="Java Developer",
                experience_years="0-1",
                skills_text="Java, Spring Boot, SQL, React, Data Structures, Algorithms",
                projects_text="Library Management System (Java, MySQL); Student Portal (React, FastAPI, PostgreSQL)",
            )
            db.add(profile)

            for name, category in [
                ("Java", "language"), ("Spring Boot", "framework"), ("SQL", "database"),
                ("React", "framework"), ("Data Structures", "concept"), ("Algorithms", "concept"),
            ]:
                db.add(Skill(user_id=user.id, name=name, category=category, proficiency="intermediate"))

            db.add(Project(
                user_id=user.id, title="Library Management System",
                description="A desktop Java application to manage book issue/return with a MySQL backend.",
                technologies="Java, JDBC, MySQL, Swing",
            ))
            db.add(Project(
                user_id=user.id, title="Student Placement Portal",
                description="A full-stack web app for students to track placement preparation, built with "
                             "React and FastAPI.",
                technologies="React, FastAPI, PostgreSQL",
            ))

            resume = Resume(
                user_id=user.id,
                original_filename="demo_resume.pdf",
                file_path="",
                raw_text="Demo Student. Skills: Java, Spring Boot, SQL, React, Data Structures, Algorithms. "
                          "Projects: Library Management System, Student Placement Portal. "
                          "Education: B.Tech Computer Science. Experience: Internship at a startup.",
                extracted_skills=json.dumps(["java", "sql"]),
                extracted_technologies=json.dumps(["spring boot", "react"]),
                extracted_projects=json.dumps(["Library Management System", "Student Placement Portal"]),
                extracted_education=json.dumps(["B.Tech Computer Science"]),
                extracted_experience=json.dumps(["Internship at a startup"]),
                extracted_certifications=json.dumps([]),
                keywords=json.dumps(["java", "sql", "spring boot", "react", "data structures", "algorithms"]),
            )
            db.add(resume)
            db.flush()

            # ---- one completed HR interview ----
            hr_interview = Interview(
                user_id=user.id, interview_type="hr", target_role="Java Developer", status="completed",
                overall_score=78.0, technical_score=66.3, communication_score=78.0,
                strengths=json.dumps(["Answer stays relevant to what was asked.", "Good use of structured reasoning or examples."]),
                weaknesses=json.dumps(["Answer is quite short; add more specific detail or an example."]),
                ai_feedback="Good performance with room to grow - focus on depth and specific examples in weaker answers.",
                recommended_topics=json.dumps(["Communication", "Self Awareness"]),
                started_at=dt.datetime.utcnow() - dt.timedelta(days=5, minutes=20),
                completed_at=dt.datetime.utcnow() - dt.timedelta(days=5),
                duration_seconds=1180,
            )
            db.add(hr_interview)
            db.flush()

            hr_qas = [
                ("Tell me about yourself and what led you to pursue a career in Java Developer.",
                 "communication",
                 "I'm a final year Computer Science student who built a Library Management System in Java, "
                 "which sparked my interest in backend development because I enjoyed designing the data model "
                 "and connecting it to a MySQL database.", 82.0),
                ("What are your greatest strengths relevant to a Java Developer role?",
                 "self_awareness",
                 "I am strong in problem solving and enjoy debugging complex issues.", 58.0),
            ]
            for idx, (q_text, tag, ans, score) in enumerate(hr_qas):
                q = InterviewQuestion(interview_id=hr_interview.id, order_index=idx, question_text=q_text,
                                       difficulty="medium", skill_tag=tag)
                db.add(q)
                db.flush()
                a = InterviewAnswer(question_id=q.id, answer_text=ans, input_mode="text")
                db.add(a)
                db.flush()
                db.add(Evaluation(answer_id=a.id, score=score,
                                   strengths=json.dumps(["Relevant example provided."]),
                                   weaknesses=json.dumps(["Could add a measurable outcome."]),
                                   feedback="Solid answer overall.",
                                   suggested_improvement="Quantify the impact of your example."))

            db.add(PerformanceSnapshot(user_id=user.id, source_type="hr", source_id=hr_interview.id, score=78.0,
                                        difficulty="mixed", skill_tags=json.dumps(["communication", "self_awareness"]),
                                        recorded_at=dt.datetime.utcnow() - dt.timedelta(days=5)))

            # ---- one completed Technical interview ----
            tech_interview = Interview(
                user_id=user.id, interview_type="technical", target_role="Java Developer", status="completed",
                overall_score=64.0, technical_score=64.0, communication_score=57.6,
                strengths=json.dumps(["Answer covers relevant terminology."]),
                weaknesses=json.dumps(["Answer is quite short; add more specific detail or an example.",
                                        "Consider structuring the answer with a clear example."]),
                ai_feedback="This interview highlighted several areas to strengthen, particularly Java Collections.",
                recommended_topics=json.dumps(["Java", "Data Structures"]),
                started_at=dt.datetime.utcnow() - dt.timedelta(days=2, minutes=25),
                completed_at=dt.datetime.utcnow() - dt.timedelta(days=2),
                duration_seconds=1400,
            )
            db.add(tech_interview)
            db.flush()

            tech_qas = [
                ("Explain how HashMap works internally in Java.", "java",
                 "HashMap stores key-value pairs using hashing.", 42.0),
                ("What is the difference between ArrayList and LinkedList?", "java",
                 "ArrayList uses a dynamic array internally so random access is O(1), while LinkedList uses "
                 "doubly linked nodes so insertion/removal at the ends is O(1) but random access is O(n). "
                 "For example, I use ArrayList when I need frequent lookups.", 86.0),
            ]
            for idx, (q_text, tag, ans, score) in enumerate(tech_qas):
                q = InterviewQuestion(interview_id=tech_interview.id, order_index=idx, question_text=q_text,
                                       difficulty="medium", skill_tag=tag)
                db.add(q)
                db.flush()
                a = InterviewAnswer(question_id=q.id, answer_text=ans, input_mode="text")
                db.add(a)
                db.flush()
                db.add(Evaluation(answer_id=a.id, score=score,
                                   strengths=json.dumps(["Attempted the question."]),
                                   weaknesses=json.dumps(["Add more depth on internal mechanics."]),
                                   feedback="Reasonable attempt.",
                                   suggested_improvement="Mention time complexity explicitly."))

            db.add(PerformanceSnapshot(user_id=user.id, source_type="technical", source_id=tech_interview.id,
                                        score=64.0, difficulty="mixed", skill_tags=json.dumps(["java"]),
                                        recorded_at=dt.datetime.utcnow() - dt.timedelta(days=2)))

            db.commit()
            print(f"Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")

        # ---- Coding question bank (idempotent) ----
        if db.query(CodingQuestion).count() == 0:
            questions = [
                CodingQuestion(
                    title="Sum of Two Numbers",
                    problem_statement="Read two integers from standard input (space separated) and print their sum.",
                    input_format="Two space-separated integers a and b on a single line.",
                    output_format="A single integer: the sum of a and b.",
                    constraints="-10^9 <= a, b <= 10^9",
                    sample_input="3 5", sample_output="8", difficulty="easy", topic_tag="basics",
                    starter_code=(
                        "import java.util.Scanner;\n\n"
                        "public class Solution {\n"
                        "    public static void main(String[] args) {\n"
                        "        Scanner sc = new Scanner(System.in);\n"
                        "        int a = sc.nextInt();\n"
                        "        int b = sc.nextInt();\n"
                        "        // TODO: print the sum\n"
                        "    }\n"
                        "}\n"
                    ),
                    test_cases=json.dumps([
                        {"input": "3 5", "expected_output": "8"},
                        {"input": "-2 7", "expected_output": "5"},
                        {"input": "0 0", "expected_output": "0"},
                    ]),
                ),
                CodingQuestion(
                    title="Reverse a String",
                    problem_statement="Read a single line string and print it reversed.",
                    input_format="A single line containing a string with no spaces.",
                    output_format="The reversed string.",
                    constraints="1 <= length <= 1000",
                    sample_input="hello", sample_output="olleh", difficulty="easy", topic_tag="strings",
                    starter_code=(
                        "import java.util.Scanner;\n\n"
                        "public class Solution {\n"
                        "    public static void main(String[] args) {\n"
                        "        Scanner sc = new Scanner(System.in);\n"
                        "        String s = sc.nextLine();\n"
                        "        // TODO: print the reversed string\n"
                        "    }\n"
                        "}\n"
                    ),
                    test_cases=json.dumps([
                        {"input": "hello", "expected_output": "olleh"},
                        {"input": "java", "expected_output": "avaj"},
                        {"input": "a", "expected_output": "a"},
                    ]),
                ),
                CodingQuestion(
                    title="Find the Maximum in an Array",
                    problem_statement="Read n, then n space-separated integers. Print the maximum value.",
                    input_format="First line: integer n. Second line: n space-separated integers.",
                    output_format="A single integer: the maximum value in the array.",
                    constraints="1 <= n <= 1000",
                    sample_input="5\n3 7 2 9 4", sample_output="9", difficulty="easy", topic_tag="arrays",
                    starter_code=(
                        "import java.util.Scanner;\n\n"
                        "public class Solution {\n"
                        "    public static void main(String[] args) {\n"
                        "        Scanner sc = new Scanner(System.in);\n"
                        "        int n = sc.nextInt();\n"
                        "        int[] arr = new int[n];\n"
                        "        for (int i = 0; i < n; i++) arr[i] = sc.nextInt();\n"
                        "        // TODO: find and print the max value\n"
                        "    }\n"
                        "}\n"
                    ),
                    test_cases=json.dumps([
                        {"input": "5\n3 7 2 9 4", "expected_output": "9"},
                        {"input": "3\n-1 -5 -2", "expected_output": "-1"},
                        {"input": "1\n42", "expected_output": "42"},
                    ]),
                ),
                CodingQuestion(
                    title="Check Palindrome",
                    problem_statement="Read a string and print 'YES' if it is a palindrome, otherwise print 'NO'.",
                    input_format="A single line string.",
                    output_format="YES or NO",
                    constraints="1 <= length <= 1000",
                    sample_input="madam", sample_output="YES", difficulty="medium", topic_tag="strings",
                    starter_code=(
                        "import java.util.Scanner;\n\n"
                        "public class Solution {\n"
                        "    public static void main(String[] args) {\n"
                        "        Scanner sc = new Scanner(System.in);\n"
                        "        String s = sc.nextLine();\n"
                        "        // TODO: check palindrome and print YES/NO\n"
                        "    }\n"
                        "}\n"
                    ),
                    test_cases=json.dumps([
                        {"input": "madam", "expected_output": "YES"},
                        {"input": "hello", "expected_output": "NO"},
                        {"input": "level", "expected_output": "YES"},
                    ]),
                ),
                CodingQuestion(
                    title="Two Sum (Hash Map)",
                    problem_statement="Read n, an array of n integers, and a target integer. Print 'YES' if any "
                                       "two distinct elements sum to the target, otherwise print 'NO'. Aim for an "
                                       "O(n) solution using a HashSet/HashMap.",
                    input_format="Line 1: n. Line 2: n space-separated integers. Line 3: target integer.",
                    output_format="YES or NO",
                    constraints="1 <= n <= 10^4",
                    sample_input="4\n2 7 11 15\n9", sample_output="YES", difficulty="medium", topic_tag="data structures",
                    starter_code=(
                        "import java.util.*;\n\n"
                        "public class Solution {\n"
                        "    public static void main(String[] args) {\n"
                        "        Scanner sc = new Scanner(System.in);\n"
                        "        int n = sc.nextInt();\n"
                        "        int[] arr = new int[n];\n"
                        "        for (int i = 0; i < n; i++) arr[i] = sc.nextInt();\n"
                        "        int target = sc.nextInt();\n"
                        "        // TODO: use a HashSet to find if two numbers sum to target\n"
                        "    }\n"
                        "}\n"
                    ),
                    test_cases=json.dumps([
                        {"input": "4\n2 7 11 15\n9", "expected_output": "YES"},
                        {"input": "3\n1 2 3\n50", "expected_output": "NO"},
                        {"input": "2\n5 5\n10", "expected_output": "YES"},
                    ]),
                ),
            ]
            db.add_all(questions)
            db.commit()
            print(f"Seeded {len(questions)} coding questions.")
        else:
            print("Coding question bank already present. Skipping.")

        # ---- one weak coding attempt so weak areas / coding charts have data ----
        if db.query(CodingSubmission).filter(CodingSubmission.user_id == user.id).count() == 0:
            max_q = db.query(CodingQuestion).filter(CodingQuestion.title == "Find the Maximum in an Array").first()
            if max_q:
                sub = CodingSubmission(
                    user_id=user.id, question_id=max_q.id,
                    source_code="public class Solution { public static void main(String[] a) { System.out.println(0); } }",
                    status="failed", compile_output="", passed_test_cases=1, total_test_cases=3,
                    execution_time_ms=140.0, time_complexity_estimate="O(1)", space_complexity_estimate="O(1)",
                    score=33.3, ai_feedback="1/3 test cases passed. Review edge cases (negative numbers, single element).",
                    submitted_at=dt.datetime.utcnow() - dt.timedelta(days=1),
                )
                db.add(sub)
                db.flush()
                db.add(PerformanceSnapshot(
                    user_id=user.id, source_type="coding", source_id=sub.id, score=33.3, difficulty="easy",
                    skill_tags=json.dumps(["arrays"]), recorded_at=dt.datetime.utcnow() - dt.timedelta(days=1)))
                db.commit()
                print("Seeded a sample coding attempt for the demo user.")

        # ---- Advanced Edition seed data: interview bank, extra coding problems, JDs ----
        from app.services.bank_service import seed_question_bank
        from scripts.seed_extra import seed_extra
        print(f"Interview bank: {seed_question_bank(db)} questions added.")
        seed_extra(db)
        from app.services.coding_import import load_problem_pack
        print("Problem pack:", load_problem_pack(db))
        print("Seeded extra coding problems (with hidden tests), job descriptions.")

        # ---- generate initial preparation plan for the demo user ----
        generate_preparation_plan(db, user.id)
        print("Generated preparation plan for demo user.")

        print("\nSeed complete.")
        print(f"  Demo login:  {DEMO_EMAIL} / {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
