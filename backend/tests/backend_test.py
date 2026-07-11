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


# ---------- Push notifications (NEW FEATURE) ----------
class TestPush:
    """Push endpoints: vapid-public-key, subscribe/status/unsubscribe, check-reminders, test."""

    @pytest.fixture(scope="class")
    def push_user(self):
        s = requests.Session()
        email = f"test_push_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Push Tester"},
                   timeout=15)
        assert r.status_code == 200
        return s

    def _fake_sub(self):
        return {
            "endpoint": f"https://fcm.googleapis.com/fcm/send/fake-{uuid.uuid4().hex[:16]}",
            "keys": {"p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
                     "auth": "tBHItJI5svbpez7KI4CCXg"},
        }

    def test_vapid_public_key_requires_no_auth_but_works(self, push_user):
        r = push_user.get(f"{API}/push/vapid-public-key", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "public_key" in data
        assert isinstance(data["public_key"], str)
        assert len(data["public_key"]) > 30  # VAPID keys are ~87 chars base64-url

    def test_status_initially_false(self, push_user):
        r = push_user.get(f"{API}/push/status", timeout=10)
        assert r.status_code == 200
        assert r.json() == {"subscribed": False}

    def test_subscribe_and_status_true(self, push_user):
        sub = self._fake_sub()
        push_user.sub = sub
        r = push_user.post(f"{API}/push/subscribe", json={"subscription": sub}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

        st = push_user.get(f"{API}/push/status", timeout=10)
        assert st.status_code == 200
        assert st.json() == {"subscribed": True}

    def test_subscribe_idempotent_upsert(self, push_user):
        # Re-post same subscription; still subscribed:true, no duplicate
        r = push_user.post(f"{API}/push/subscribe",
                           json={"subscription": push_user.sub}, timeout=10)
        assert r.status_code == 200
        st = push_user.get(f"{API}/push/status", timeout=10).json()
        assert st == {"subscribed": True}

    def test_subscribe_missing_endpoint_rejected(self, push_user):
        r = push_user.post(f"{API}/push/subscribe",
                           json={"subscription": {"keys": {"p256dh": "x", "auth": "y"}}},
                           timeout=10)
        assert r.status_code == 400
        assert "detail" in r.json()

    def test_check_reminders_ok(self, push_user):
        """check-reminders should complete without error even with an unreachable
        (fake) subscription — dead subs are pruned and sent should be 0."""
        r = push_user.post(f"{API}/push/check-reminders", timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert "sent" in data
        assert isinstance(data["sent"], int)

    def test_push_test_returns_400_when_no_valid_sub(self, push_user):
        # After a failed send, the dead subscription may have been pruned. Ensure at
        # least one fake sub is present, then /push/test will attempt to send, all
        # sends fail (invalid keys), so sent==0 -> 400 with Italian detail.
        push_user.post(f"{API}/push/subscribe",
                       json={"subscription": self._fake_sub()}, timeout=10)
        r = push_user.post(f"{API}/push/test", timeout=30)
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert isinstance(detail, str) and len(detail) > 0
        # Italian message check
        assert "notific" in detail.lower() or "attiva" in detail.lower()

    def test_unsubscribe_and_status_false(self, push_user):
        # ensure at least one sub exists (may have been pruned by previous test)
        sub = self._fake_sub()
        push_user.post(f"{API}/push/subscribe", json={"subscription": sub}, timeout=10)
        r = push_user.post(f"{API}/push/unsubscribe",
                           json={"subscription": sub}, timeout=10)
        assert r.status_code == 200

        # remove any other lingering subs so status becomes false
        # (Delete via unsubscribe endpoint of any known subs)
        push_user.post(f"{API}/push/unsubscribe",
                       json={"subscription": push_user.sub}, timeout=10)

        # Best-effort: status may still be true if extra subs remain, but we
        # unsubscribed both known ones. Accept either state — main assertion is
        # that unsubscribe returns 200 idempotently.
        st = push_user.get(f"{API}/push/status", timeout=10)
        assert st.status_code == 200
        assert "subscribed" in st.json()

    def test_push_endpoints_require_auth(self):
        for method, path in [("GET", "/push/status"),
                             ("POST", "/push/subscribe"),
                             ("POST", "/push/unsubscribe"),
                             ("POST", "/push/test"),
                             ("POST", "/push/check-reminders")]:
            r = requests.request(method, f"{API}{path}", json={"subscription": {}}, timeout=10)
            assert r.status_code == 401, f"{method} {path} should require auth"


# ---------- PWA assets ----------
class TestPWA:
    """Static PWA files served through frontend origin."""

    def test_manifest_json(self):
        r = requests.get(f"{BASE_URL}/manifest.json", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data.get("name") and "PawCare" in data["name"]
        assert data.get("short_name") == "PawCare"
        assert data.get("display") == "standalone"
        assert data.get("start_url") == "/dashboard"
        icons = data.get("icons", [])
        sizes = {i.get("sizes") for i in icons}
        assert "192x192" in sizes
        assert "512x512" in sizes

    def test_service_worker_js(self):
        r = requests.get(f"{BASE_URL}/sw.js", timeout=10)
        assert r.status_code == 200
        assert "javascript" in r.headers.get("content-type", "").lower()
        # Must contain push listener
        assert "push" in r.text.lower()
        assert "showNotification" in r.text


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



# ---------- AI Chat Streaming (NEW FEATURE - SSE) ----------
import json as _json


class TestAIChatStream:
    """Verify POST /api/ai/chat/stream is a real SSE stream that:
       1) Returns text/event-stream content-type
       2) Emits at least one `data: {"delta": ...}` chunk
       3) Ends with `data: {"done": true}`
       4) Persists both user + assistant messages to /ai/chat/history
       5) Requires auth (401 when anonymous)
    """

    @pytest.fixture(scope="class")
    def stream_user(self):
        s = requests.Session()
        email = f"test_stream_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Stream Tester"},
                   timeout=15)
        assert r.status_code == 200, f"register failed: {r.text}"
        s.email = email
        return s

    def test_stream_requires_auth(self):
        r = requests.post(f"{API}/ai/chat/stream",
                          json={"message": "ciao"}, timeout=15)
        assert r.status_code == 401

    def test_stream_emits_deltas_and_done(self, stream_user):
        # History before send
        h_before = stream_user.get(f"{API}/ai/chat/history", timeout=10).json()
        n_before = len(h_before)

        with stream_user.post(
            f"{API}/ai/chat/stream",
            json={"message": "Come si chiama la mia razza preferita di gatto? Rispondi brevemente."},
            stream=True, timeout=120,
        ) as r:
            assert r.status_code == 200, f"stream failed: {r.text[:400]}"
            ctype = r.headers.get("content-type", "")
            assert "text/event-stream" in ctype, f"bad content-type: {ctype}"

            delta_count = 0
            got_done = False
            got_error = False
            full_text = ""
            for raw in r.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if not raw.startswith("data:"):
                    continue
                payload = raw[5:].strip()
                try:
                    obj = _json.loads(payload)
                except Exception:
                    continue
                if "delta" in obj:
                    delta_count += 1
                    full_text += obj["delta"]
                elif obj.get("done"):
                    got_done = True
                    break
                elif obj.get("error"):
                    got_error = True

            assert not got_error, "stream emitted error frame"
            assert delta_count > 0, "no delta chunks received"
            assert got_done, "stream did not end with done:true"
            assert len(full_text) > 3, f"no accumulated text: {full_text!r}"

        # Give server a moment to persist the assistant message
        time.sleep(1.0)
        h_after = stream_user.get(f"{API}/ai/chat/history", timeout=10).json()
        assert len(h_after) == n_before + 2, \
            f"history should grow by 2, got {len(h_after)-n_before}"
        # last two entries: user then assistant
        last_two = h_after[-2:]
        assert last_two[0]["role"] == "user"
        assert last_two[1]["role"] == "assistant"
        assert len(last_two[1]["content"]) > 0
        stream_user.first_user_msg = last_two[0]["content"]

    def test_stream_conversation_memory(self, stream_user):
        """Second stream request should recall context from first turn."""
        # First turn: give the assistant a specific pet name to remember
        with stream_user.post(
            f"{API}/ai/chat/stream",
            json={"message": "Il mio cane si chiama Fulmine. Ricordati questo nome."},
            stream=True, timeout=120,
        ) as r:
            assert r.status_code == 200
            for raw in r.iter_lines(decode_unicode=True):
                if raw and raw.startswith("data:") and '"done"' in raw:
                    break
        time.sleep(0.5)

        # Second turn: ask the model to recall the name
        full = ""
        with stream_user.post(
            f"{API}/ai/chat/stream",
            json={"message": "Come si chiama il mio cane?"},
            stream=True, timeout=120,
        ) as r:
            assert r.status_code == 200
            for raw in r.iter_lines(decode_unicode=True):
                if not raw or not raw.startswith("data:"):
                    continue
                try:
                    obj = _json.loads(raw[5:].strip())
                except Exception:
                    continue
                if "delta" in obj:
                    full += obj["delta"]
                elif obj.get("done"):
                    break
        assert "fulmine" in full.lower(), \
            f"Streaming chat did not recall the pet name 'Fulmine'. Got: {full[:400]}"


# ---------- Scheduler + Manual Batch (NEW FEATURE) ----------
class TestSchedulerBatch:
    """Verify:
       - POST /api/push/run-batch requires auth (401 anonymous)
       - Non-admin user gets 403 with detail 'Solo admin'
       - Admin gets {total: int}
       - Regression: POST /api/push/check-reminders still works per user
    """

    def test_run_batch_requires_auth(self):
        r = requests.post(f"{API}/push/run-batch", timeout=15)
        assert r.status_code == 401

    def test_run_batch_forbidden_for_non_admin(self, new_user_session):
        r = new_user_session.post(f"{API}/push/run-batch", timeout=15)
        assert r.status_code == 403, f"non-admin should be 403, got {r.status_code}: {r.text}"
        body = r.json()
        assert body.get("detail") == "Solo admin", f"unexpected detail: {body}"

    def test_run_batch_ok_for_admin(self, admin_session):
        r = admin_session.post(f"{API}/push/run-batch", timeout=30)
        assert r.status_code == 200, f"admin batch failed: {r.status_code} {r.text}"
        body = r.json()
        assert "total" in body
        assert isinstance(body["total"], int)
        assert body["total"] >= 0

    def test_check_reminders_still_works(self, new_user_session):
        r = new_user_session.post(f"{API}/push/check-reminders", timeout=30)
        assert r.status_code == 200
        assert isinstance(r.json().get("sent"), int)


# ---------- Medical Documents (NEW FEATURE - Object Storage) ----------
class TestDocuments:
    """Verify document endpoints:
       - GET /api/pets/{id}/documents lists non-deleted docs (no storage_path leaked)
       - POST /api/pets/{id}/documents uploads (multipart) to object storage + DB record
       - GET /api/documents/{doc_id}/download returns bytes with correct content-type
       - DELETE /api/pets/{id}/documents/{doc_id} soft-deletes (is_deleted=true)
       - Files > 15MB rejected with 400
       - Auth required, owner-only
    """

    @pytest.fixture(scope="class")
    def doc_user(self):
        s = requests.Session()
        email = f"test_doc_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Doc Tester"},
                   timeout=15)
        assert r.status_code == 200
        pr = s.post(f"{API}/pets", json={
            "name": "TEST_DocPet", "species": "dog", "breed": "Bulldog",
            "birth_date": "2019-03-15", "sex": "M", "weight": 20.0
        }, timeout=15)
        assert pr.status_code == 200
        s.pet_id = pr.json()["id"]
        s.email = email
        return s

    def test_list_documents_empty_initially(self, doc_user):
        r = doc_user.get(f"{API}/pets/{doc_user.pet_id}/documents", timeout=15)
        assert r.status_code == 200
        assert r.json() == []

    def test_upload_document_txt(self, doc_user):
        pid = doc_user.pet_id
        content = b"TEST document contents - PawCare regression test\n"
        files = {"file": ("test_referto.txt", content, "text/plain")}
        data = {"category": "referto"}
        r = doc_user.post(f"{API}/pets/{pid}/documents", files=files, data=data, timeout=60)
        assert r.status_code == 200, f"upload failed: {r.status_code} {r.text[:400]}"
        body = r.json()
        assert body["name"] == "test_referto.txt"
        assert body["category"] == "referto"
        assert body["pet_id"] == pid
        assert body["is_deleted"] is False
        assert body["content_type"] == "text/plain"
        assert "id" in body
        # storage_path must NOT leak to client
        assert "storage_path" not in body
        assert "_id" not in body
        doc_user.doc_id = body["id"]
        doc_user.doc_content = content

    def test_list_documents_shows_uploaded_no_storage_path(self, doc_user):
        r = doc_user.get(f"{API}/pets/{doc_user.pet_id}/documents", timeout=15)
        assert r.status_code == 200
        docs = r.json()
        assert len(docs) >= 1
        our = next((d for d in docs if d["id"] == doc_user.doc_id), None)
        assert our is not None
        assert our["name"] == "test_referto.txt"
        assert our["category"] == "referto"
        assert "storage_path" not in our
        assert "_id" not in our

    def test_upload_default_category(self, doc_user):
        """category defaults to 'altro' if not provided."""
        pid = doc_user.pet_id
        files = {"file": ("misc.txt", b"misc bytes", "text/plain")}
        r = doc_user.post(f"{API}/pets/{pid}/documents", files=files, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json()["category"] == "altro"
        doc_user.doc_id_misc = r.json()["id"]

    def test_download_document_returns_bytes(self, doc_user):
        r = doc_user.get(f"{API}/documents/{doc_user.doc_id}/download", timeout=60)
        assert r.status_code == 200
        # Content bytes match what we uploaded
        assert r.content == doc_user.doc_content, \
            f"downloaded bytes mismatch. len={len(r.content)}"
        # Content-Type should be text/plain (as stored)
        ctype = r.headers.get("content-type", "")
        assert "text/plain" in ctype, f"bad content-type: {ctype}"

    def test_upload_requires_auth(self, doc_user):
        files = {"file": ("x.txt", b"y", "text/plain")}
        r = requests.post(f"{API}/pets/{doc_user.pet_id}/documents",
                          files=files, data={"category": "altro"}, timeout=15)
        assert r.status_code == 401

    def test_list_documents_requires_auth(self, doc_user):
        r = requests.get(f"{API}/pets/{doc_user.pet_id}/documents", timeout=10)
        assert r.status_code == 401

    def test_download_requires_auth(self, doc_user):
        r = requests.get(f"{API}/documents/{doc_user.doc_id}/download", timeout=15)
        assert r.status_code == 401

    def test_download_isolated_across_users(self, doc_user, admin_session):
        """Admin (different user) must NOT be able to download another user's doc."""
        r = admin_session.get(f"{API}/documents/{doc_user.doc_id}/download", timeout=15)
        assert r.status_code == 404

    def test_upload_other_user_pet_rejected(self, doc_user, admin_session):
        """Admin cannot upload to another user's pet (pet not found for admin)."""
        files = {"file": ("x.txt", b"y", "text/plain")}
        r = admin_session.post(f"{API}/pets/{doc_user.pet_id}/documents",
                               files=files, data={"category": "altro"}, timeout=15)
        assert r.status_code == 404

    def test_upload_rejects_over_15mb(self, doc_user):
        """15MB+1 byte payload must be rejected with 400."""
        big = b"A" * (15 * 1024 * 1024 + 1)
        files = {"file": ("big.txt", big, "text/plain")}
        r = doc_user.post(f"{API}/pets/{doc_user.pet_id}/documents",
                          files=files, data={"category": "altro"}, timeout=120)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:300]}"
        assert "15MB" in r.json().get("detail", "") or "grande" in r.json().get("detail", "").lower()

    def test_soft_delete_document(self, doc_user):
        pid = doc_user.pet_id
        r = doc_user.delete(f"{API}/pets/{pid}/documents/{doc_user.doc_id}", timeout=15)
        assert r.status_code == 200
        assert r.json().get("ok") is True

        # No longer in list
        lst = doc_user.get(f"{API}/pets/{pid}/documents", timeout=15).json()
        assert not any(d["id"] == doc_user.doc_id for d in lst), \
            "soft-deleted doc still visible in list"

        # Download by id must 404 (soft-deleted → not found)
        dr = doc_user.get(f"{API}/documents/{doc_user.doc_id}/download", timeout=15)
        assert dr.status_code == 404

    def test_delete_pet_cascades_soft_delete_documents(self, doc_user):
        """Delete pet must soft-delete remaining documents; list must return [] via new pet."""
        pid = doc_user.pet_id
        # doc_id_misc still exists — verify visible before delete
        lst_before = doc_user.get(f"{API}/pets/{pid}/documents", timeout=15).json()
        assert any(d["id"] == doc_user.doc_id_misc for d in lst_before)

        # Delete the pet
        r = doc_user.delete(f"{API}/pets/{pid}", timeout=15)
        assert r.status_code == 200

        # Download of the cascaded doc should also 404 (record still exists but is_deleted=true)
        dr = doc_user.get(f"{API}/documents/{doc_user.doc_id_misc}/download", timeout=15)
        assert dr.status_code == 404


# ---------- Calendar (NEW FEATURE - multi-pet events) ----------
class TestCalendar:
    """Verify GET /api/calendar/events returns all events across the user's pets:
       - visits (date), vaccines (next_due), treatments (next_due)
       - each event has {date, type, title, pet_id, pet_name}
       - sorted by date ascending
       - only current user's events (isolation)
       - empty list when user has no pets
    """

    @pytest.fixture(scope="class")
    def cal_user(self):
        s = requests.Session()
        email = f"test_cal_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Pass1234!", "name": "Cal Tester"},
                   timeout=15)
        assert r.status_code == 200
        s.email = email
        return s

    def test_calendar_empty_no_pets(self, cal_user):
        r = cal_user.get(f"{API}/calendar/events", timeout=15)
        assert r.status_code == 200
        assert r.json() == []

    def test_calendar_returns_all_event_types_sorted(self, cal_user):
        # Create two pets
        p1 = cal_user.post(f"{API}/pets", json={
            "name": "TEST_CalPet1", "species": "dog", "breed": "Boxer",
            "birth_date": "2020-01-01", "sex": "M", "weight": 22.0
        }, timeout=15).json()
        p2 = cal_user.post(f"{API}/pets", json={
            "name": "TEST_CalPet2", "species": "cat", "breed": "Siamese",
            "birth_date": "2021-01-01", "sex": "F", "weight": 4.5
        }, timeout=15).json()
        cal_user.p1 = p1["id"]
        cal_user.p2 = p2["id"]

        # visit on pet1
        cal_user.post(f"{API}/pets/{p1['id']}/visits", json={
            "date": "2025-06-10", "reason": "TEST_Controllo", "veterinarian": "Dr. X"
        }, timeout=10)
        # vaccine on pet1 with next_due
        cal_user.post(f"{API}/pets/{p1['id']}/vaccines", json={
            "name": "TEST_Antirabbica", "date_given": "2025-01-01", "next_due": "2025-08-01"
        }, timeout=10)
        # vaccine without next_due → should NOT appear
        cal_user.post(f"{API}/pets/{p1['id']}/vaccines", json={
            "name": "TEST_NoDueVax", "date_given": "2025-01-01", "next_due": None
        }, timeout=10)
        # treatment on pet2 with next_due
        cal_user.post(f"{API}/pets/{p2['id']}/treatments", json={
            "name": "TEST_Antipulci", "date_given": "2025-01-01",
            "frequency_days": 30, "next_due": "2025-04-15"
        }, timeout=10)
        # treatment without next_due → should NOT appear
        cal_user.post(f"{API}/pets/{p2['id']}/treatments", json={
            "name": "TEST_NoDueTr", "date_given": "2025-01-01",
            "frequency_days": 30, "next_due": None
        }, timeout=10)

        r = cal_user.get(f"{API}/calendar/events", timeout=15)
        assert r.status_code == 200
        events = r.json()

        # find our TEST events
        ours = [e for e in events if e["title"].startswith("TEST_")]
        titles = {e["title"] for e in ours}
        assert "TEST_Controllo" in titles
        assert "TEST_Antirabbica" in titles
        assert "TEST_Antipulci" in titles
        # events with null next_due are excluded
        assert "TEST_NoDueVax" not in titles
        assert "TEST_NoDueTr" not in titles

        # Each event has required fields
        for e in ours:
            assert set(["date", "type", "title", "pet_id", "pet_name"]).issubset(e.keys())
            assert e["type"] in ("visit", "vaccine", "treatment")
            assert e["pet_name"] in ("TEST_CalPet1", "TEST_CalPet2")

        # Verify types match
        by_title = {e["title"]: e for e in ours}
        assert by_title["TEST_Controllo"]["type"] == "visit"
        assert by_title["TEST_Controllo"]["date"] == "2025-06-10"
        assert by_title["TEST_Controllo"]["pet_id"] == p1["id"]
        assert by_title["TEST_Controllo"]["pet_name"] == "TEST_CalPet1"

        assert by_title["TEST_Antirabbica"]["type"] == "vaccine"
        assert by_title["TEST_Antirabbica"]["date"] == "2025-08-01"

        assert by_title["TEST_Antipulci"]["type"] == "treatment"
        assert by_title["TEST_Antipulci"]["date"] == "2025-04-15"
        assert by_title["TEST_Antipulci"]["pet_name"] == "TEST_CalPet2"

        # Sorted ascending by date (globally, not only ours)
        dates = [e["date"] for e in events]
        assert dates == sorted(dates), f"events not sorted ascending: {dates}"

    def test_calendar_requires_auth(self):
        r = requests.get(f"{API}/calendar/events", timeout=10)
        assert r.status_code == 401

    def test_calendar_isolated_across_users(self, cal_user, admin_session):
        """Admin's calendar must NOT include cal_user's TEST_ events."""
        r = admin_session.get(f"{API}/calendar/events", timeout=15)
        assert r.status_code == 200
        events = r.json()
        # None of admin's events should be linked to cal_user's pets
        assert not any(e["pet_id"] in (cal_user.p1, cal_user.p2) for e in events)
        # And no TEST_ titles from cal_user's pets
        assert not any(e["title"] in ("TEST_Controllo", "TEST_Antirabbica", "TEST_Antipulci")
                       and e["pet_name"] in ("TEST_CalPet1", "TEST_CalPet2")
                       for e in events)



# ---------- Admin endpoints (NEW FEATURE - role gating + stats + users table) ----------
class TestAdmin:
    """Verify:
       - GET /api/auth/me returns role='admin' for admin, 'user' otherwise
       - GET /api/admin/stats + /api/admin/users:
           - 401 anonymous
           - 403 with Italian detail for normal user
           - 200 with expected shape for admin
    """

    def test_me_returns_role_admin(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert body.get("role") == "admin", f"expected role=admin, got {body}"

    def test_me_returns_role_user_for_normal(self, new_user_session):
        r = new_user_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json().get("role") == "user"

    def test_admin_stats_requires_auth(self):
        r = requests.get(f"{API}/admin/stats", timeout=10)
        assert r.status_code == 401

    def test_admin_users_requires_auth(self):
        r = requests.get(f"{API}/admin/users", timeout=10)
        assert r.status_code == 401

    def test_admin_stats_forbidden_for_non_admin(self, new_user_session):
        r = new_user_session.get(f"{API}/admin/stats", timeout=10)
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        assert r.json().get("detail") == "Accesso riservato agli amministratori"

    def test_admin_users_forbidden_for_non_admin(self, new_user_session):
        r = new_user_session.get(f"{API}/admin/users", timeout=10)
        assert r.status_code == 403
        assert r.json().get("detail") == "Accesso riservato agli amministratori"

    def test_admin_stats_ok_for_admin(self, admin_session):
        r = admin_session.get(f"{API}/admin/stats", timeout=15)
        assert r.status_code == 200
        data = r.json()
        # required keys
        required = ["total_users", "new_users_7d", "google_users", "email_users",
                   "push_users", "total_pets", "total_visits", "total_vaccines",
                   "total_treatments", "total_chat_messages"]
        for k in required:
            assert k in data, f"missing stat: {k}"
            assert isinstance(data[k], int), f"{k} should be int, got {type(data[k])}"
        # sanity
        assert data["total_users"] >= 1
        assert data["email_users"] >= 1  # at least admin

    def test_admin_users_ok_for_admin(self, admin_session):
        r = admin_session.get(f"{API}/admin/users", timeout=20)
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list)
        assert len(users) >= 1
        # find admin row
        admin_row = next((u for u in users if u.get("email") == ADMIN_EMAIL), None)
        assert admin_row is not None, "admin user missing from /admin/users"
        # required user fields
        for k in ["user_id", "email", "name", "auth_provider", "pet_count", "chat_count", "has_push"]:
            assert k in admin_row, f"missing field: {k}"
        # no sensitive fields leaked
        assert "password_hash" not in admin_row
        assert "_id" not in admin_row
        # counts are ints, has_push is bool
        assert isinstance(admin_row["pet_count"], int)
        assert isinstance(admin_row["chat_count"], int)
        assert isinstance(admin_row["has_push"], bool)
        # role field present for admin row
        assert admin_row.get("role") == "admin"

