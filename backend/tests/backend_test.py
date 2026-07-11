"""PawCare Backend API tests - Full coverage suite."""
import os
import time
import uuid
import pytest
import requests
from datetime import date, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL",
                          "https://petcare-ai-13.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@pawcare.it"
ADMIN_PASSWORD = "admin123"


# ---------- Fixtures ----------
@pytest.fixture(scope="module")
def admin_session():
    """Login admin via cookie session."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def new_user_session():
    """Register a fresh TEST_ user."""
    s = requests.Session()
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    r = s.post(f"{API}/auth/register",
               json={"email": email, "password": "Pass1234!", "name": "Test User"},
               timeout=15)
    assert r.status_code == 200, f"Registration failed: {r.status_code} {r.text}"
    s.email = email  # attach for reference
    return s


# ---------- Auth tests ----------
class TestAuth:
    def test_root(self):
        r = requests.get(f"{API}/", timeout=10)
        assert r.status_code == 200
        assert "message" in r.json()

    def test_register_and_me(self, new_user_session):
        r = new_user_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == new_user_session.email
        assert data["name"] == "Test User"

    def test_register_duplicate(self, new_user_session):
        r = new_user_session.post(f"{API}/auth/register",
                                  json={"email": new_user_session.email,
                                        "password": "Pass1234!", "name": "Dup"},
                                  timeout=10)
        assert r.status_code == 400

    def test_login_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=10)
        assert r.status_code == 401

    def test_me_unauthenticated(self):
        r = requests.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 401

    def test_logout(self):
        s = requests.Session()
        s.post(f"{API}/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=10)
        assert s.get(f"{API}/auth/me", timeout=10).status_code == 200
        r = s.post(f"{API}/auth/logout", timeout=10)
        assert r.status_code == 200
        # After logout, previously authenticated session should no longer work
        r2 = s.get(f"{API}/auth/me", timeout=10)
        assert r2.status_code == 401

    def test_protected_endpoints_require_auth(self):
        for path in ["/pets", "/dashboard/upcoming", "/ai/chat/history"]:
            r = requests.get(f"{API}{path}", timeout=10)
            assert r.status_code == 401, f"{path} should be 401 but got {r.status_code}"


# ---------- Pets CRUD ----------
class TestPets:
    def _pet_payload(self, name="TEST_Fido"):
        return {"name": name, "species": "dog", "breed": "Labrador",
                "birth_date": "2020-05-01", "sex": "M", "weight": 25.5}

    def test_create_pet(self, new_user_session):
        r = new_user_session.post(f"{API}/pets", json=self._pet_payload(), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "TEST_Fido"
        assert data["species"] == "dog"
        assert data["breed"] == "Labrador"
        assert "id" in data and "age" in data
        assert data["age"] >= 4
        new_user_session.pet_id = data["id"]

    def test_list_pets(self, new_user_session):
        r = new_user_session.get(f"{API}/pets", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert any(p["id"] == new_user_session.pet_id for p in r.json())

    def test_get_pet(self, new_user_session):
        r = new_user_session.get(f"{API}/pets/{new_user_session.pet_id}", timeout=10)
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_Fido"

    def test_get_pet_not_found(self, new_user_session):
        r = new_user_session.get(f"{API}/pets/nonexistent-id", timeout=10)
        assert r.status_code == 404

    def test_update_pet(self, new_user_session):
        payload = self._pet_payload(name="TEST_Rex")
        payload["weight"] = 30.0
        r = new_user_session.put(f"{API}/pets/{new_user_session.pet_id}",
                                 json=payload, timeout=10)
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_Rex"
        # verify persistence
        got = new_user_session.get(f"{API}/pets/{new_user_session.pet_id}").json()
        assert got["weight"] == 30.0

    def test_pet_isolation_between_users(self, new_user_session, admin_session):
        """Admin should not see the other user's pet."""
        r = admin_session.get(f"{API}/pets/{new_user_session.pet_id}", timeout=10)
        assert r.status_code == 404


# ---------- Records: visits/vaccines/treatments ----------
class TestRecords:
    def test_add_visit_and_list(self, new_user_session):
        pid = new_user_session.pet_id
        payload = {"date": "2025-01-15", "reason": "Controllo annuale",
                   "veterinarian": "Dr. Bianchi", "notes": "Tutto ok"}
        r = new_user_session.post(f"{API}/pets/{pid}/visits", json=payload, timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["reason"] == "Controllo annuale"
        new_user_session.visit_id = data["id"]

        lst = new_user_session.get(f"{API}/pets/{pid}/visits", timeout=10).json()
        assert any(v["id"] == new_user_session.visit_id for v in lst)

    def test_add_vaccine(self, new_user_session):
        pid = new_user_session.pet_id
        next_due = (date.today() + timedelta(days=15)).isoformat()
        r = new_user_session.post(f"{API}/pets/{pid}/vaccines",
                                  json={"name": "Antirabbica",
                                        "date_given": "2025-01-01",
                                        "next_due": next_due}, timeout=10)
        assert r.status_code == 200
        new_user_session.vaccine_id = r.json()["id"]

    def test_add_treatment(self, new_user_session):
        pid = new_user_session.pet_id
        next_due = (date.today() + timedelta(days=5)).isoformat()
        r = new_user_session.post(f"{API}/pets/{pid}/treatments",
                                  json={"name": "Antipulci",
                                        "date_given": "2025-01-01",
                                        "frequency_days": 30,
                                        "next_due": next_due}, timeout=10)
        assert r.status_code == 200
        new_user_session.treatment_id = r.json()["id"]

    def test_upcoming_dashboard(self, new_user_session):
        r = new_user_session.get(f"{API}/dashboard/upcoming", timeout=10)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        # Should include vaccine and treatment we added
        titles = [i["title"] for i in items]
        assert "Antirabbica" in titles
        assert "Antipulci" in titles
        # Sorted by days_left ascending
        days = [i["days_left"] for i in items]
        assert days == sorted(days)

    def test_delete_records(self, new_user_session):
        pid = new_user_session.pet_id
        r = new_user_session.delete(f"{API}/pets/{pid}/visits/{new_user_session.visit_id}", timeout=10)
        assert r.status_code == 200
        r = new_user_session.delete(f"{API}/pets/{pid}/vaccines/{new_user_session.vaccine_id}", timeout=10)
        assert r.status_code == 200
        # verify vaccine gone
        vs = new_user_session.get(f"{API}/pets/{pid}/vaccines").json()
        assert not any(v["id"] == new_user_session.vaccine_id for v in vs)


# ---------- Guides ----------
class TestGuides:
    def test_all_guides(self):
        r = requests.get(f"{API}/guides", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 8

    def test_filter_by_species_dog(self):
        r = requests.get(f"{API}/guides?species=dog", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert all(g["species"] == "dog" for g in data)
        assert len(data) >= 1

    def test_filter_by_species_cat(self):
        r = requests.get(f"{API}/guides?species=cat", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert all(g["species"] == "cat" for g in data)


# ---------- AI (may be slow) ----------
class TestAI:
    def test_advice(self, new_user_session):
        pid = new_user_session.pet_id
        r = new_user_session.post(f"{API}/ai/advice",
                                  json={"pet_id": pid}, timeout=90)
        assert r.status_code == 200, f"AI advice failed: {r.text[:400]}"
        data = r.json()
        assert "advice" in data
        assert len(data["advice"]) > 30

    def test_advice_not_found(self, new_user_session):
        r = new_user_session.post(f"{API}/ai/advice",
                                  json={"pet_id": "nope"}, timeout=90)
        assert r.status_code == 404

    def test_chat_and_history(self, new_user_session):
        r = new_user_session.post(f"{API}/ai/chat",
                                  json={"message": "Ciao, come devo curare il mio cane?"},
                                  timeout=90)
        assert r.status_code == 200
        data = r.json()
        assert "reply" in data
        assert len(data["reply"]) > 10

        time.sleep(0.5)
        h = new_user_session.get(f"{API}/ai/chat/history", timeout=10)
        assert h.status_code == 200
        msgs = h.json()
        assert isinstance(msgs, list)
        assert len(msgs) >= 2
        roles = [m["role"] for m in msgs]
        assert "user" in roles and "assistant" in roles


# ---------- AI Chat Memory (multi-turn context) - BUG FIX VERIFICATION ----------
class TestAIChatMemory:
    """Verify the AI assistant retains context across multiple turns via initial_messages."""

    @pytest.fixture(scope="class")
    def fresh_chat_session(self):
        """Register a brand-new user so DB chat history is empty for a clean test."""
        s = requests.Session()
        email = f"test_mem_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Memory Tester"},
                   timeout=15)
        assert r.status_code == 200, f"register failed: {r.text}"
        # Sanity: history should be empty
        h = s.get(f"{API}/ai/chat/history", timeout=10)
        assert h.status_code == 200
        assert h.json() == []
        return s

    def test_multi_turn_context_recall(self, fresh_chat_session):
        s = fresh_chat_session
        # Turn 1 - provide breed + problem
        r1 = s.post(f"{API}/ai/chat",
                    json={"message": "Ho un Golden Retriever che si gratta molto le orecchie."},
                    timeout=120)
        assert r1.status_code == 200, f"chat turn1 failed: {r1.text[:500]}"
        reply1 = r1.json()["reply"]
        assert isinstance(reply1, str) and len(reply1) > 20

        # Turn 2 - ask the model to recall what was said
        r2 = s.post(f"{API}/ai/chat",
                    json={"message": "Che razza di cane ho e qual era il problema che ti ho descritto?"},
                    timeout=120)
        assert r2.status_code == 200, f"chat turn2 failed: {r2.text[:500]}"
        reply2 = r2.json()["reply"].lower()
        print(f"\n[MEMORY TEST] Turn2 reply:\n{r2.json()['reply']}\n")

        # Assistant must recall the breed and the problem from turn 1
        assert "golden retriever" in reply2, f"Breed not recalled. Reply: {reply2[:400]}"
        assert ("orecchi" in reply2 or "grat" in reply2 or "prurito" in reply2), \
            f"Problem (ear scratching) not recalled. Reply: {reply2[:400]}"

    def test_third_turn_still_has_context(self, fresh_chat_session):
        s = fresh_chat_session
        # Turn 3 - narrow follow-up that only makes sense with memory
        r = s.post(f"{API}/ai/chat",
                   json={"message": "Ha 5 anni. Cosa mi consigli per il suo problema alle orecchie?"},
                   timeout=120)
        assert r.status_code == 200
        reply = r.json()["reply"].lower()
        print(f"\n[MEMORY TEST] Turn3 reply:\n{r.json()['reply']}\n")
        # It should give advice about ears / scratching (not generic off-topic)
        assert ("orecchi" in reply or "auricol" in reply or "prurito" in reply
                or "otit" in reply or "veterinar" in reply), \
            f"Turn3 lost topical context. Reply: {reply[:400]}"

    def test_history_persisted_and_ordered(self, fresh_chat_session):
        s = fresh_chat_session
        h = s.get(f"{API}/ai/chat/history", timeout=10)
        assert h.status_code == 200
        msgs = h.json()
        # 3 user + 3 assistant messages
        assert len(msgs) == 6, f"expected 6 messages, got {len(msgs)}: {[m['role'] for m in msgs]}"
        roles = [m["role"] for m in msgs]
        assert roles == ["user", "assistant", "user", "assistant", "user", "assistant"]
        # First user message must be the Golden Retriever one
        assert "golden retriever" in msgs[0]["content"].lower()
        # Timestamps monotonically non-decreasing
        ts = [m["created_at"] for m in msgs]
        assert ts == sorted(ts)


# ---------- Weight logs (NEW FEATURE) ----------
class TestWeights:
    """Weight tracking endpoints - list/create/delete + syncing pet.weight to latest."""

    @pytest.fixture(scope="class")
    def weight_user(self):
        """Fresh user + pet dedicated to weight tests."""
        s = requests.Session()
        email = f"test_wt_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Weight Tester"},
                   timeout=15)
        assert r.status_code == 200
        pr = s.post(f"{API}/pets", json={
            "name": "TEST_Weighty", "species": "dog", "breed": "Beagle",
            "birth_date": "2021-06-01", "sex": "M", "weight": 10.0
        }, timeout=15)
        assert pr.status_code == 200
        s.pet_id = pr.json()["id"]
        return s

    def test_list_weights_empty_initially(self, weight_user):
        r = weight_user.get(f"{API}/pets/{weight_user.pet_id}/weights", timeout=10)
        assert r.status_code == 200
        assert r.json() == []

    def test_create_weight_and_persistence(self, weight_user):
        pid = weight_user.pet_id
        payload = {"date": "2025-01-05", "weight": 12.3}
        r = weight_user.post(f"{API}/pets/{pid}/weights", json=payload, timeout=10)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["weight"] == 12.3
        assert data["date"] == "2025-01-05"
        assert data["pet_id"] == pid
        assert "id" in data
        assert "_id" not in data  # ObjectId must not leak
        weight_user.w1 = data["id"]

        # GET verifies persistence
        got = weight_user.get(f"{API}/pets/{pid}/weights", timeout=10).json()
        assert any(w["id"] == weight_user.w1 for w in got)

    def test_multiple_weights_sorted_asc(self, weight_user):
        pid = weight_user.pet_id
        # add two more entries out of order
        r2 = weight_user.post(f"{API}/pets/{pid}/weights",
                              json={"date": "2025-03-10", "weight": 13.1}, timeout=10)
        assert r2.status_code == 200
        weight_user.w3 = r2.json()["id"]
        r3 = weight_user.post(f"{API}/pets/{pid}/weights",
                              json={"date": "2025-02-01", "weight": 12.7}, timeout=10)
        assert r3.status_code == 200
        weight_user.w2 = r3.json()["id"]

        lst = weight_user.get(f"{API}/pets/{pid}/weights", timeout=10).json()
        assert len(lst) == 3
        dates = [w["date"] for w in lst]
        assert dates == sorted(dates), f"Weights not sorted asc: {dates}"

    def test_pet_weight_synced_to_latest(self, weight_user):
        """pet.weight should reflect the measurement with the latest date."""
        pid = weight_user.pet_id
        pet = weight_user.get(f"{API}/pets/{pid}", timeout=10).json()
        # latest measurement was 2025-03-10 with weight 13.1
        assert pet["weight"] == 13.1, f"Expected pet.weight=13.1, got {pet['weight']}"

    def test_delete_weight_and_verify(self, weight_user):
        pid = weight_user.pet_id
        r = weight_user.delete(f"{API}/pets/{pid}/weights/{weight_user.w2}", timeout=10)
        assert r.status_code == 200
        lst = weight_user.get(f"{API}/pets/{pid}/weights", timeout=10).json()
        assert not any(w["id"] == weight_user.w2 for w in lst)
        assert len(lst) == 2

    def test_weights_require_auth(self, weight_user):
        pid = weight_user.pet_id
        r = requests.get(f"{API}/pets/{pid}/weights", timeout=10)
        assert r.status_code == 401

    def test_weights_isolated_across_users(self, weight_user, admin_session):
        """Admin should not be able to list/create weights on another user's pet."""
        pid = weight_user.pet_id
        r = admin_session.get(f"{API}/pets/{pid}/weights", timeout=10)
        assert r.status_code == 404
        r2 = admin_session.post(f"{API}/pets/{pid}/weights",
                                json={"date": "2025-01-01", "weight": 5.0}, timeout=10)
        assert r2.status_code == 404


# ---------- Cleanup: delete pet cascades (includes weights) ----------
class TestZCleanup:
    def test_delete_pet_cascade(self, new_user_session):
        # create our own pet & records (loadscope may separate classes)
        r = new_user_session.post(f"{API}/pets", json={
            "name": "TEST_ToDelete", "species": "cat", "breed": "Persian",
            "birth_date": "2022-01-01", "sex": "F", "weight": 4.2
        }, timeout=15)
        assert r.status_code == 200
        pid = r.json()["id"]

        # add a vaccine so cascade can be verified
        nd = (date.today() + timedelta(days=10)).isoformat()
        new_user_session.post(f"{API}/pets/{pid}/vaccines", json={
            "name": "TEST_Trivalente", "date_given": "2025-01-01", "next_due": nd
        }, timeout=10)
        # add a weight log so cascade can be verified for weights too
        new_user_session.post(f"{API}/pets/{pid}/weights", json={
            "date": "2025-01-01", "weight": 4.5
        }, timeout=10)
        wlist = new_user_session.get(f"{API}/pets/{pid}/weights", timeout=10).json()
        assert len(wlist) == 1

        r = new_user_session.delete(f"{API}/pets/{pid}", timeout=10)
        assert r.status_code == 200
        # verify pet gone
        r2 = new_user_session.get(f"{API}/pets/{pid}", timeout=10)
        assert r2.status_code == 404
        # weights endpoint should now 404 too (pet not found)
        r3 = new_user_session.get(f"{API}/pets/{pid}/weights", timeout=10)
        assert r3.status_code == 404
        # upcoming should no longer include items from this pet
        u = new_user_session.get(f"{API}/dashboard/upcoming", timeout=10).json()
        assert not any(i["pet_id"] == pid for i in u)
