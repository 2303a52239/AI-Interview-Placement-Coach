CORRECT_SUM_CODE = """
import java.util.Scanner;
public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        int a = sc.nextInt();
        int b = sc.nextInt();
        System.out.println(a + b);
    }
}
"""

BROKEN_CODE = "public class Solution { public static void main(String[] a) { int x = ; } }"

WRONG_LOGIC_CODE = """
public class Solution {
    public static void main(String[] args) {
        System.out.println(0);
    }
}
"""


def _get_sum_question_id(client, headers):
    resp = client.get("/coding/questions", headers=headers)
    for q in resp.json():
        if q["title"] == "Sum of Two Numbers":
            return q["id"]
    raise AssertionError("Seed question 'Sum of Two Numbers' not found")


def test_list_coding_questions(client, auth_headers):
    resp = client.get("/coding/questions", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_submit_correct_code_passes_all_tests(client, auth_headers):
    qid = _get_sum_question_id(client, auth_headers)
    resp = client.post("/coding/submit", headers=auth_headers, json={"question_id": qid, "source_code": CORRECT_SUM_CODE})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "passed"
    assert data["passed_test_cases"] == data["total_test_cases"]
    assert data["score"] == 100.0


def test_submit_broken_code_reports_compile_error(client, auth_headers):
    qid = _get_sum_question_id(client, auth_headers)
    resp = client.post("/coding/submit", headers=auth_headers, json={"question_id": qid, "source_code": BROKEN_CODE})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "compiled_error"
    assert data["score"] == 0.0
    assert "error" in data["compile_output"].lower()


def test_submit_wrong_logic_partially_or_fully_fails(client, auth_headers):
    qid = _get_sum_question_id(client, auth_headers)
    resp = client.post("/coding/submit", headers=auth_headers, json={"question_id": qid, "source_code": WRONG_LOGIC_CODE})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"
    assert data["passed_test_cases"] == 0


def test_submit_empty_code_rejected(client, auth_headers):
    qid = _get_sum_question_id(client, auth_headers)
    resp = client.post("/coding/submit", headers=auth_headers, json={"question_id": qid, "source_code": "   "})
    assert resp.status_code == 400


def test_submit_nonexistent_question_returns_404(client, auth_headers):
    resp = client.post("/coding/submit", headers=auth_headers, json={"question_id": 999999, "source_code": CORRECT_SUM_CODE})
    assert resp.status_code == 404


def test_long_complexity_text_is_stored(client, auth_headers):
    """Regression: complexity estimates are sentences and once overflowed VARCHAR(50) on PostgreSQL."""
    qid = _get_sum_question_id(client, auth_headers)
    nested = ("import java.util.Scanner;\npublic class Solution { public static void main(String[] x) {"
              " Scanner s = new Scanner(System.in); int a = s.nextInt(), b = s.nextInt(); int r = 0;"
              " for (int i = 0; i < 1; i++) { for (int j = 0; j < 1; j++) { r = a + b; } } System.out.println(r); } }")
    resp = client.post("/coding/submit", headers=auth_headers, json={"question_id": qid, "source_code": nested})
    assert resp.status_code == 200
    assert len(resp.json()["time_complexity_estimate"]) > 50
