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


# ---------- Cleanup: delete pet cascades ----------
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

        r = new_user_session.delete(f"{API}/pets/{pid}", timeout=10)
        assert r.status_code == 200
        # verify pet gone
        r2 = new_user_session.get(f"{API}/pets/{pid}", timeout=10)
        assert r2.status_code == 404
        # upcoming should no longer include items from this pet
        u = new_user_session.get(f"{API}/dashboard/upcoming", timeout=10).json()
        assert not any(i["pet_id"] == pid for i in u)
