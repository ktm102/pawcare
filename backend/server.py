from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import logging
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
import bcrypt
import jwt
import requests
import secrets
from datetime import datetime, timezone, timedelta

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone
from pywebpush import webpush, WebPushException
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json as _json

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGORITHM = "HS256"
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']
VAPID_PUBLIC_KEY = os.environ['VAPID_PUBLIC_KEY']
VAPID_PRIVATE_KEY = os.environ['VAPID_PRIVATE_KEY']
VAPID_CLAIM_EMAIL = os.environ['VAPID_CLAIM_EMAIL']

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------- Helpers ----------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email,
               "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def set_auth_cookie(response: Response, token: str):
    response.set_cookie(key="access_token", value=token, httponly=True,
                        secure=True, samesite="none", max_age=604800, path="/")


def clean(doc: dict) -> dict:
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return doc


async def get_current_user(request: Request) -> dict:
    # 1. Google session token
    session_token = request.cookies.get("session_token")
    if session_token:
        session = await db.user_sessions.find_one({"session_token": session_token})
        if session:
            expires_at = session["expires_at"]
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at >= datetime.now(timezone.utc):
                user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
                if user:
                    return clean(user)
    # 2. JWT access token (cookie then Bearer)
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
            if user:
                return clean(user)
        except jwt.PyJWTError:
            pass
    raise HTTPException(status_code=401, detail="Non autenticato")


# ---------------- Models ----------------
class RegisterInput(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class PetInput(BaseModel):
    name: str
    species: str  # dog / cat
    breed: str
    birth_date: str  # ISO date
    sex: str  # M / F
    weight: Optional[float] = None
    photo: Optional[str] = None  # base64 data url


class VisitInput(BaseModel):
    date: str
    reason: str
    veterinarian: Optional[str] = ""
    notes: Optional[str] = ""


class VaccineInput(BaseModel):
    name: str
    date_given: str
    next_due: Optional[str] = None


class TreatmentInput(BaseModel):
    name: str
    date_given: str
    frequency_days: int
    next_due: Optional[str] = None


class ChatInput(BaseModel):
    message: str
    pet_id: Optional[str] = None


class WeightInput(BaseModel):
    date: str
    weight: float = Field(gt=0)


class AdviceInput(BaseModel):
    pet_id: str


class PushSubscriptionInput(BaseModel):
    subscription: dict


def _send_web_push(subscription_info: dict, payload: dict) -> bool:
    try:
        webpush(
            subscription_info=subscription_info,
            data=_json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_CLAIM_EMAIL},
        )
        return True
    except WebPushException as e:
        logger.warning(f"WebPush failed: {e}")
        return False
    except Exception as e:
        logger.warning(f"WebPush error: {e}")
        return False


async def send_push_to_user(user_id: str, title: str, body: str, url: str = "/dashboard"):
    subs = await db.push_subscriptions.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    payload = {"title": title, "body": body, "url": url}
    sent = 0
    for s in subs:
        ok = _send_web_push(s["subscription"], payload)
        if ok:
            sent += 1
        else:
            # remove dead subscription
            await db.push_subscriptions.delete_one({"user_id": user_id, "endpoint": s.get("endpoint")})
    return sent


def calc_age(birth_date: str) -> int:
    try:
        bd = datetime.fromisoformat(birth_date).date()
        today = datetime.now(timezone.utc).date()
        return (today - bd).days // 365
    except Exception:
        return 0


# ---------------- Auth Routes ----------------
@api_router.post("/auth/register")
async def register(input: RegisterInput, response: Response):
    email = input.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email già registrata")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    doc = {"user_id": user_id, "email": email, "name": input.name,
           "password_hash": hash_password(input.password), "picture": "",
           "auth_provider": "email", "created_at": datetime.now(timezone.utc).isoformat()}
    await db.users.insert_one(doc)
    token = create_access_token(user_id, email)
    set_auth_cookie(response, token)
    return {"user": {"user_id": user_id, "email": email, "name": input.name, "picture": ""}, "token": token}


@api_router.post("/auth/login")
async def login(input: LoginInput, response: Response):
    email = input.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not user.get("password_hash") or not verify_password(input.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    token = create_access_token(user["user_id"], email)
    set_auth_cookie(response, token)
    return {"user": {"user_id": user["user_id"], "email": email, "name": user["name"], "picture": user.get("picture", "")}, "token": token}


@api_router.post("/auth/google/session")
async def google_session(request: Request, response: Response):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=400, detail="Manca session id")
    resp = requests.get("https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                        headers={"X-Session-ID": session_id})
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Sessione non valida")
    data = resp.json()
    email = data["email"].lower()
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user = {"user_id": user_id, "email": email, "name": data.get("name", ""),
                "picture": data.get("picture", ""), "auth_provider": "google",
                "created_at": datetime.now(timezone.utc).isoformat()}
        await db.users.insert_one(dict(user))
    session_token = data["session_token"]
    await db.user_sessions.insert_one({
        "user_id": user["user_id"], "session_token": session_token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()})
    response.set_cookie(key="session_token", value=session_token, httponly=True,
                        secure=True, samesite="none", max_age=604800, path="/")
    return {"user": {"user_id": user["user_id"], "email": email, "name": user["name"], "picture": user.get("picture", "")}}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user_id": user["user_id"], "email": user["email"], "name": user["name"], "picture": user.get("picture", "")}


@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


# ---------------- Pet Routes ----------------
@api_router.get("/pets")
async def list_pets(user: dict = Depends(get_current_user)):
    pets = await db.pets.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(1000)
    for p in pets:
        p["age"] = calc_age(p["birth_date"])
    return pets


@api_router.post("/pets")
async def create_pet(input: PetInput, user: dict = Depends(get_current_user)):
    pet_id = str(uuid.uuid4())
    doc = {"id": pet_id, "user_id": user["user_id"], **input.model_dump(),
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.pets.insert_one(dict(doc))
    doc.pop("_id", None)
    doc["age"] = calc_age(doc["birth_date"])
    return doc


@api_router.get("/pets/{pet_id}")
async def get_pet(pet_id: str, user: dict = Depends(get_current_user)):
    pet = await db.pets.find_one({"id": pet_id, "user_id": user["user_id"]}, {"_id": 0})
    if not pet:
        raise HTTPException(status_code=404, detail="Animale non trovato")
    pet["age"] = calc_age(pet["birth_date"])
    return pet


@api_router.put("/pets/{pet_id}")
async def update_pet(pet_id: str, input: PetInput, user: dict = Depends(get_current_user)):
    res = await db.pets.update_one({"id": pet_id, "user_id": user["user_id"]}, {"$set": input.model_dump()})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Animale non trovato")
    pet = await db.pets.find_one({"id": pet_id}, {"_id": 0})
    pet["age"] = calc_age(pet["birth_date"])
    return pet


@api_router.delete("/pets/{pet_id}")
async def delete_pet(pet_id: str, user: dict = Depends(get_current_user)):
    await db.pets.delete_one({"id": pet_id, "user_id": user["user_id"]})
    await db.visits.delete_many({"pet_id": pet_id})
    await db.vaccines.delete_many({"pet_id": pet_id})
    await db.treatments.delete_many({"pet_id": pet_id})
    await db.weights.delete_many({"pet_id": pet_id})
    return {"ok": True}


async def _verify_pet(pet_id: str, user_id: str):
    pet = await db.pets.find_one({"id": pet_id, "user_id": user_id}, {"_id": 0})
    if not pet:
        raise HTTPException(status_code=404, detail="Animale non trovato")
    return pet


# ---------------- Visits ----------------
@api_router.get("/pets/{pet_id}/visits")
async def list_visits(pet_id: str, user: dict = Depends(get_current_user)):
    await _verify_pet(pet_id, user["user_id"])
    return await db.visits.find({"pet_id": pet_id}, {"_id": 0}).sort("date", -1).to_list(1000)


@api_router.post("/pets/{pet_id}/visits")
async def create_visit(pet_id: str, input: VisitInput, user: dict = Depends(get_current_user)):
    await _verify_pet(pet_id, user["user_id"])
    doc = {"id": str(uuid.uuid4()), "pet_id": pet_id, **input.model_dump()}
    await db.visits.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@api_router.delete("/pets/{pet_id}/visits/{item_id}")
async def delete_visit(pet_id: str, item_id: str, user: dict = Depends(get_current_user)):
    await _verify_pet(pet_id, user["user_id"])
    await db.visits.delete_one({"id": item_id, "pet_id": pet_id})
    return {"ok": True}


# ---------------- Vaccines ----------------
@api_router.get("/pets/{pet_id}/vaccines")
async def list_vaccines(pet_id: str, user: dict = Depends(get_current_user)):
    await _verify_pet(pet_id, user["user_id"])
    return await db.vaccines.find({"pet_id": pet_id}, {"_id": 0}).sort("date_given", -1).to_list(1000)


@api_router.post("/pets/{pet_id}/vaccines")
async def create_vaccine(pet_id: str, input: VaccineInput, user: dict = Depends(get_current_user)):
    await _verify_pet(pet_id, user["user_id"])
    doc = {"id": str(uuid.uuid4()), "pet_id": pet_id, **input.model_dump()}
    await db.vaccines.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@api_router.delete("/pets/{pet_id}/vaccines/{item_id}")
async def delete_vaccine(pet_id: str, item_id: str, user: dict = Depends(get_current_user)):
    await _verify_pet(pet_id, user["user_id"])
    await db.vaccines.delete_one({"id": item_id, "pet_id": pet_id})
    return {"ok": True}


# ---------------- Treatments ----------------
@api_router.get("/pets/{pet_id}/treatments")
async def list_treatments(pet_id: str, user: dict = Depends(get_current_user)):
    await _verify_pet(pet_id, user["user_id"])
    return await db.treatments.find({"pet_id": pet_id}, {"_id": 0}).sort("date_given", -1).to_list(1000)


@api_router.post("/pets/{pet_id}/treatments")
async def create_treatment(pet_id: str, input: TreatmentInput, user: dict = Depends(get_current_user)):
    await _verify_pet(pet_id, user["user_id"])
    doc = {"id": str(uuid.uuid4()), "pet_id": pet_id, **input.model_dump()}
    await db.treatments.insert_one(dict(doc))
    doc.pop("_id", None)
    return doc


@api_router.delete("/pets/{pet_id}/treatments/{item_id}")
async def delete_treatment(pet_id: str, item_id: str, user: dict = Depends(get_current_user)):
    await _verify_pet(pet_id, user["user_id"])
    await db.treatments.delete_one({"id": item_id, "pet_id": pet_id})
    return {"ok": True}


# ---------------- Weight logs ----------------
@api_router.get("/pets/{pet_id}/weights")
async def list_weights(pet_id: str, user: dict = Depends(get_current_user)):
    await _verify_pet(pet_id, user["user_id"])
    return await db.weights.find({"pet_id": pet_id}, {"_id": 0}).sort("date", 1).to_list(1000)


@api_router.post("/pets/{pet_id}/weights")
async def create_weight(pet_id: str, input: WeightInput, user: dict = Depends(get_current_user)):
    await _verify_pet(pet_id, user["user_id"])
    doc = {"id": str(uuid.uuid4()), "pet_id": pet_id, **input.model_dump()}
    await db.weights.insert_one(dict(doc))
    doc.pop("_id", None)
    # keep the pet's current weight in sync with the latest measurement
    latest = await db.weights.find({"pet_id": pet_id}, {"_id": 0}).sort("date", -1).to_list(1)
    if latest:
        await db.pets.update_one({"id": pet_id}, {"$set": {"weight": latest[0]["weight"]}})
    return doc


@api_router.delete("/pets/{pet_id}/weights/{item_id}")
async def delete_weight(pet_id: str, item_id: str, user: dict = Depends(get_current_user)):
    await _verify_pet(pet_id, user["user_id"])
    await db.weights.delete_one({"id": item_id, "pet_id": pet_id})
    return {"ok": True}


# ---------------- Dashboard: upcoming due dates ----------------
@api_router.get("/dashboard/upcoming")
async def upcoming(user: dict = Depends(get_current_user)):
    pets = await db.pets.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(1000)
    pet_map = {p["id"]: p for p in pets}
    pet_ids = list(pet_map.keys())
    items = []
    if not pet_ids:
        return items
    today = datetime.now(timezone.utc).date()
    vaccines = await db.vaccines.find({"pet_id": {"$in": pet_ids}, "next_due": {"$ne": None}}, {"_id": 0}).to_list(1000)
    treatments = await db.treatments.find({"pet_id": {"$in": pet_ids}, "next_due": {"$ne": None}}, {"_id": 0}).to_list(1000)
    for v in vaccines:
        if not v.get("next_due"):
            continue
        due = datetime.fromisoformat(v["next_due"]).date()
        items.append({"type": "vaccine", "title": v["name"], "due_date": v["next_due"],
                      "days_left": (due - today).days, "pet_id": v["pet_id"],
                      "pet_name": pet_map[v["pet_id"]]["name"]})
    for t in treatments:
        if not t.get("next_due"):
            continue
        due = datetime.fromisoformat(t["next_due"]).date()
        items.append({"type": "treatment", "title": t["name"], "due_date": t["next_due"],
                      "days_left": (due - today).days, "pet_id": t["pet_id"],
                      "pet_name": pet_map[t["pet_id"]]["name"]})
    items.sort(key=lambda x: x["days_left"])
    return items


# ---------------- Guides ----------------
GUIDES = [
    {"id": "g1", "title": "Alimentazione del cucciolo", "species": "dog", "min_age": 0, "max_age": 1,
     "content": "Nei primi mesi il cucciolo ha bisogno di pasti frequenti (3-4 al giorno) con crocchette specifiche per puppy, ricche di proteine e calcio per una crescita sana. Introduci gradualmente cibo solido dallo svezzamento."},
    {"id": "g2", "title": "Vaccinazioni essenziali per cani", "species": "dog", "min_age": 0, "max_age": 100,
     "content": "Le vaccinazioni core includono cimurro, epatite, parvovirosi e rabbia. Il ciclo primario inizia a 6-8 settimane con richiami ogni 3-4 settimane fino alle 16 settimane, poi richiami annuali o triennali."},
    {"id": "g3", "title": "Prevenzione antiparassitaria", "species": "dog", "min_age": 0, "max_age": 100,
     "content": "Utilizza antiparassitari regolari contro pulci, zecche e filaria. In primavera-estate aumenta la frequenza. I trattamenti spot-on o le compresse masticabili vanno somministrati secondo il peso e il calendario consigliato dal veterinario."},
    {"id": "g4", "title": "Cura del cane anziano", "species": "dog", "min_age": 7, "max_age": 100,
     "content": "I cani anziani necessitano di controlli veterinari più frequenti, dieta a basso contenuto calorico, integratori per le articolazioni e attività fisica moderata. Monitora peso, denti e mobilità."},
    {"id": "g5", "title": "Alimentazione del gattino", "species": "cat", "min_age": 0, "max_age": 1,
     "content": "I gattini richiedono cibo umido e crocchette kitten ad alto contenuto proteico. Fino ai 6 mesi offri pasti piccoli e frequenti. Assicura sempre acqua fresca disponibile."},
    {"id": "g6", "title": "Vaccinazioni per gatti", "species": "cat", "min_age": 0, "max_age": 100,
     "content": "Le vaccinazioni core per il gatto includono trivalente (panleucopenia, rinotracheite, calicivirosi) e antirabbica. Il ciclo inizia a 8-9 settimane con richiami. I gatti che escono necessitano anche del vaccino FeLV."},
    {"id": "g7", "title": "Cura del pelo e igiene del gatto", "species": "cat", "min_age": 0, "max_age": 100,
     "content": "Spazzola regolarmente il gatto per ridurre i boli di pelo, soprattutto le razze a pelo lungo. Controlla orecchie, denti e unghie. La lettiera va pulita quotidianamente per prevenire problemi urinari."},
    {"id": "g8", "title": "Gatto senior: cosa sapere", "species": "cat", "min_age": 8, "max_age": 100,
     "content": "Dai 8 anni in poi il gatto è considerato senior. Sono consigliati controlli semestrali, attenzione a reni e tiroide, dieta specifica e ambiente confortevole con accessi facilitati."},
]


@api_router.get("/guides")
async def get_guides(species: Optional[str] = None, age: Optional[int] = None):
    result = GUIDES
    if species:
        result = [g for g in result if g["species"] == species]
    if age is not None:
        result = [g for g in result if g["min_age"] <= age <= g["max_age"]]
    return result


# ---------------- AI ----------------
async def _pet_context(pet_id: str, user_id: str) -> str:
    pet = await db.pets.find_one({"id": pet_id, "user_id": user_id}, {"_id": 0})
    if not pet:
        return ""
    age = calc_age(pet["birth_date"])
    species = "cane" if pet["species"] == "dog" else "gatto"
    return f"L'animale si chiama {pet['name']}, è un {species} di razza {pet['breed']}, ha {age} anni, sesso {'maschio' if pet['sex']=='M' else 'femmina'}, peso {pet.get('weight') or 'non indicato'} kg."


@api_router.post("/ai/advice")
async def ai_advice(input: AdviceInput, user: dict = Depends(get_current_user)):
    ctx = await _pet_context(input.pet_id, user["user_id"])
    if not ctx:
        raise HTTPException(status_code=404, detail="Animale non trovato")
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"advice_{input.pet_id}",
        system_message="Sei un assistente veterinario esperto. Fornisci consigli pratici, chiari e sicuri su cura e prevenzione per animali domestici, in italiano. Non sostituisci il veterinario: consiglia sempre una visita per problemi seri."
    ).with_model("anthropic", "claude-sonnet-4-6")
    prompt = f"{ctx}\n\nFornisci consigli personalizzati di cura e prevenzione per questo animale in base alla sua età e razza. Struttura la risposta in sezioni brevi: Alimentazione, Attività fisica, Prevenzione sanitaria, Cosa monitorare. Usa un tono amichevole e pratico."
    resp = await chat.send_message(UserMessage(text=prompt))
    return {"advice": resp}


@api_router.post("/ai/chat")
async def ai_chat(input: ChatInput, user: dict = Depends(get_current_user)):
    ctx = ""
    if input.pet_id:
        ctx = await _pet_context(input.pet_id, user["user_id"])
    system = "Sei PawCare AI, un assistente veterinario amichevole. Rispondi in italiano con consigli pratici su cura, alimentazione, vaccini e prevenzione per animali domestici. Ricorda il contesto della conversazione precedente e le informazioni già fornite dall'utente. Consiglia una visita veterinaria per problemi di salute seri."
    if ctx:
        system += f" Contesto animale: {ctx}"
    # Build conversation history from DB (last 20 messages) for context memory
    history = await db.chat_messages.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    history.reverse()
    initial_messages = [{"role": "system", "content": system}]
    for m in history:
        initial_messages.append({"role": m["role"], "content": m["content"]})
    # persist user message
    await db.chat_messages.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["user_id"], "role": "user",
        "content": input.message, "created_at": datetime.now(timezone.utc).isoformat()})
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"chat_{user['user_id']}",
                   system_message=system, initial_messages=initial_messages).with_model("anthropic", "claude-sonnet-4-6")
    resp = await chat.send_message(UserMessage(text=input.message))
    await db.chat_messages.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["user_id"], "role": "assistant",
        "content": resp, "created_at": datetime.now(timezone.utc).isoformat()})
    return {"reply": resp}


@api_router.get("/ai/chat/history")
async def chat_history(user: dict = Depends(get_current_user)):
    msgs = await db.chat_messages.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", 1).to_list(200)
    return msgs


@api_router.post("/ai/chat/stream")
async def ai_chat_stream(input: ChatInput, user: dict = Depends(get_current_user)):
    ctx = ""
    if input.pet_id:
        ctx = await _pet_context(input.pet_id, user["user_id"])
    system = "Sei PawCare AI, un assistente veterinario amichevole. Rispondi in italiano con consigli pratici su cura, alimentazione, vaccini e prevenzione per animali domestici. Ricorda il contesto della conversazione precedente e le informazioni già fornite dall'utente. Consiglia una visita veterinaria per problemi di salute seri."
    if ctx:
        system += f" Contesto animale: {ctx}"
    history = await db.chat_messages.find(
        {"user_id": user["user_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    history.reverse()
    initial_messages = [{"role": "system", "content": system}]
    for m in history:
        initial_messages.append({"role": m["role"], "content": m["content"]})
    await db.chat_messages.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["user_id"], "role": "user",
        "content": input.message, "created_at": datetime.now(timezone.utc).isoformat()})
    user_id = user["user_id"]
    message_text = input.message

    async def event_generator():
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"chat_{user_id}",
                       system_message=system, initial_messages=initial_messages).with_model("anthropic", "claude-sonnet-4-6")
        full = ""
        try:
            async for event in chat.stream_message(UserMessage(text=message_text)):
                if isinstance(event, TextDelta):
                    full += event.content
                    yield f"data: {_json.dumps({'delta': event.content})}\n\n"
                elif isinstance(event, StreamDone):
                    break
        except Exception as e:
            logger.warning(f"AI stream error: {e}")
            yield f"data: {_json.dumps({'error': True})}\n\n"
        await db.chat_messages.insert_one({
            "id": str(uuid.uuid4()), "user_id": user_id, "role": "assistant",
            "content": full, "created_at": datetime.now(timezone.utc).isoformat()})
        yield f"data: {_json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------- Push notifications ----------------
@api_router.get("/push/vapid-public-key")
async def vapid_public_key():
    return {"public_key": VAPID_PUBLIC_KEY}


@api_router.post("/push/subscribe")
async def push_subscribe(input: PushSubscriptionInput, user: dict = Depends(get_current_user)):
    sub = input.subscription
    endpoint = sub.get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=400, detail="Subscription non valida")
    await db.push_subscriptions.update_one(
        {"user_id": user["user_id"], "endpoint": endpoint},
        {"$set": {"user_id": user["user_id"], "endpoint": endpoint, "subscription": sub,
                  "created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"ok": True}


@api_router.post("/push/unsubscribe")
async def push_unsubscribe(input: PushSubscriptionInput, user: dict = Depends(get_current_user)):
    endpoint = input.subscription.get("endpoint")
    await db.push_subscriptions.delete_one({"user_id": user["user_id"], "endpoint": endpoint})
    return {"ok": True}


@api_router.get("/push/status")
async def push_status(user: dict = Depends(get_current_user)):
    count = await db.push_subscriptions.count_documents({"user_id": user["user_id"]})
    return {"subscribed": count > 0}


@api_router.post("/push/test")
async def push_test(user: dict = Depends(get_current_user)):
    sent = await send_push_to_user(user["user_id"], "PawCare 🐾", "Le notifiche sono attive! Ti avviseremo delle prossime scadenze.")
    if sent == 0:
        raise HTTPException(status_code=400, detail="Nessuna notifica inviata. Attiva le notifiche.")
    return {"sent": sent}


@api_router.post("/push/check-reminders")
async def push_check_reminders(user: dict = Depends(get_current_user)):
    """Send push reminders for vaccines/treatments due within 7 days, deduped."""
    sent = await _send_reminders_for_user(user["user_id"])
    return {"sent": sent}


async def _send_reminders_for_user(user_id: str) -> int:
    items = await upcoming({"user_id": user_id})
    today_iso = datetime.now(timezone.utc).date().isoformat()
    sent = 0
    for item in items:
        if item["days_left"] < 0 or item["days_left"] > 7:
            continue
        dedupe_key = f"{item['type']}:{item['pet_id']}:{item['due_date']}"
        already = await db.push_sent.find_one({"user_id": user_id, "key": dedupe_key, "sent_date": today_iso})
        if already:
            continue
        kind = "Vaccino" if item["type"] == "vaccine" else "Antiparassitario"
        when = "oggi" if item["days_left"] == 0 else f"tra {item['days_left']} giorni"
        s = await send_push_to_user(
            user_id, f"Promemoria: {kind} in scadenza",
            f"{item['title']} per {item['pet_name']} è previsto {when}.",
            f"/pet/{item['pet_id']}")
        if s:
            sent += 1
            await db.push_sent.insert_one({"user_id": user_id, "key": dedupe_key, "sent_date": today_iso})
    return sent


async def send_all_reminders() -> int:
    """Background job: send due-date reminders to every user with a push subscription."""
    user_ids = await db.push_subscriptions.distinct("user_id")
    total = 0
    for uid in user_ids:
        try:
            total += await _send_reminders_for_user(uid)
        except Exception as e:
            logger.warning(f"Reminder batch error for {uid}: {e}")
    logger.info(f"Reminder batch complete: {total} notifications sent across {len(user_ids)} users")
    return total


@api_router.post("/push/run-batch")
async def push_run_batch(user: dict = Depends(get_current_user)):
    """Manually trigger the reminder batch for all users (admin only)."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo admin")
    total = await send_all_reminders()
    return {"total": total}


@api_router.get("/")
async def root():
    return {"message": "PawCare API"}
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000")],
    allow_methods=["*"],
    allow_headers=["*"],
)


scheduler = AsyncIOScheduler(timezone="UTC")


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.user_sessions.create_index("session_token")
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@pawcare.it")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "user_id": f"user_{uuid.uuid4().hex[:12]}", "email": admin_email,
            "name": "Admin", "password_hash": hash_password(admin_password),
            "picture": "", "auth_provider": "email", "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat()})
    # Daily reminder job at 08:00 UTC — sends push even when the app is closed
    if not scheduler.running:
        scheduler.add_job(send_all_reminders, "cron", hour=8, minute=0,
                          id="daily_reminders", replace_existing=True)
        scheduler.start()
        logger.info("Reminder scheduler started (daily 08:00 UTC)")


@app.on_event("shutdown")
async def shutdown_db_client():
    if scheduler.running:
        scheduler.shutdown(wait=False)
    client.close()
