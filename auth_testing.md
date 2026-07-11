# Auth Testing Playbook (PawCare)

Two auth methods coexist: Email+Password (JWT access_token cookie) and Emergent Google Auth (session_token cookie).

## Email/Password
```
curl -c cookies.txt -X POST $BACKEND/api/auth/login -H "Content-Type: application/json" -d '{"email":"admin@pawcare.it","password":"admin123"}'
curl -b cookies.txt $BACKEND/api/auth/me
```
Login returns { user, token } and sets access_token cookie. Bearer header also supported: `Authorization: Bearer <token>`.

## Google Auth (simulated for testing)
Create a user + session in MongoDB, then set session_token cookie:
```
mongosh --eval "
use('test_database');
var uid='user_'+Date.now();
var st='test_session_'+Date.now();
db.users.insertOne({user_id:uid,email:'g'+Date.now()+'@test.it',name:'Google User',picture:'',auth_provider:'google',created_at:new Date().toISOString()});
db.user_sessions.insertOne({user_id:uid,session_token:st,expires_at:new Date(Date.now()+7*24*3600*1000).toISOString(),created_at:new Date().toISOString()});
print(st);
"
```
Set cookie name `session_token`, secure=true, sameSite=None, httpOnly=true.

## Protected endpoints (need auth cookie or Bearer)
- GET /api/pets
- POST /api/pets
- GET /api/pets/{id}
- GET /api/dashboard/upcoming
- POST /api/ai/advice { pet_id }
- POST /api/ai/chat { message, pet_id }
