from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import sqlite3, os, time, hmac, hashlib, secrets, mimetypes

BASE = Path(__file__).parent
STATIC = BASE / 'static'
ORIG = BASE / 'storage' / 'originals'
PREV = BASE / 'storage' / 'previews'
DB = BASE / 'data.db'
ORIG.mkdir(parents=True, exist_ok=True); PREV.mkdir(parents=True, exist_ok=True)
SECRET = os.getenv('DPS_SESSION_SECRET','dev-secret-change-before-live').encode()
ADMIN_PASSWORD = os.getenv('DPS_ADMIN_PASSWORD','change-this-before-live')
app = FastAPI(title='Drone Pro Solution')
app.mount('/static', StaticFiles(directory=STATIC), name='static')


def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db(); c.executescript('''
    CREATE TABLE IF NOT EXISTS gallery(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,category TEXT NOT NULL,filename TEXT NOT NULL,preview TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS enquiries(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT,service TEXT,details TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    '''); c.commit(); c.close()
init_db()

def sign(v): return hmac.new(SECRET,v.encode(),hashlib.sha256).hexdigest()
def session_ok(request):
    token=request.cookies.get('dps_admin')
    return bool(token and hmac.compare_digest(token, sign('admin')))

def safe_name(name):
    ext=Path(name).suffix.lower()
    if ext not in {'.jpg','.jpeg','.png','.webp'}: raise HTTPException(400,'Only JPG, PNG or WEBP images are supported for protected previews.')
    return secrets.token_hex(10)+ext

def make_preview(src, dest):
    im=Image.open(src).convert('RGB'); im.thumbnail((1500,1000), Image.Resampling.LANCZOS)
    draw=ImageDraw.Draw(im)
    text='DRONE PRO SOLUTION • PREVIEW'
    try: font=ImageFont.truetype('arial.ttf', max(18, im.width//45))
    except: font=ImageFont.load_default()
    bbox=draw.textbbox((0,0),text,font=font); pad=14
    x=im.width-bbox[2]-pad; y=im.height-bbox[3]-pad
    draw.rounded_rectangle((x-10,y-8,x+bbox[2]+10,y+bbox[3]+8),radius=10,fill=(0,27,50,190))
    draw.text((x,y),text,font=font,fill=(255,255,255))
    im.save(dest,'JPEG',quality=78,optimize=True)

@app.get('/', response_class=HTMLResponse)
def home(): return FileResponse(STATIC/'index.html')

@app.get('/api/gallery')
def gallery():
    c=db(); rows=c.execute('SELECT id,title,category,preview,created_at FROM gallery ORDER BY id DESC').fetchall(); c.close()
    return [dict(r) for r in rows]

@app.get('/preview/{filename}')
def preview(filename:str):
    p=PREV/Path(filename).name
    if not p.exists(): raise HTTPException(404)
    return FileResponse(p, media_type='image/jpeg', headers={'Cache-Control':'public,max-age=3600','X-Content-Type-Options':'nosniff'})

@app.post('/api/enquiry')
def enquiry(name:str=Form(...), email:str=Form(...), service:str=Form(...), details:str=Form('')):
    c=db(); c.execute('INSERT INTO enquiries(name,email,service,details) VALUES(?,?,?,?)',(name,email,service,details)); c.commit(); c.close()
    msg=f"New enquiry from {name}%0AService: {service}%0AEmail: {email}%0ADetails: {details}"
    return {'ok':True,'whatsapp':f'https://wa.me/919343329079?text={msg}'}

@app.get('/admin/login',response_class=HTMLResponse)
def login_page():
    return '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>DPS Admin Login</title><style>body{font-family:Segoe UI;background:#061b32;color:white;display:grid;place-items:center;height:100vh;margin:0}.box{background:white;color:#10233d;padding:30px;border-radius:18px;width:min(360px,88%)}input,button{width:100%;padding:12px;margin-top:10px;border-radius:9px;border:1px solid #ccd8e5;box-sizing:border-box}button{background:#087cff;color:white;border:0;font-weight:700}</style></head><body><form class="box" method="post"><h2>Drone Pro Solution</h2><p>Private Gallery Admin</p><input name="password" type="password" placeholder="Admin password" required><button>Login</button></form></body></html>'''

@app.post('/admin/login')
def login(password:str=Form(...)):
    if not hmac.compare_digest(password, ADMIN_PASSWORD): raise HTTPException(401,'Invalid password')
    r=RedirectResponse('/admin',303); r.set_cookie('dps_admin',sign('admin'),httponly=True,samesite='lax',secure=False,max_age=86400); return r

@app.get('/admin',response_class=HTMLResponse)
def admin(request:Request):
    if not session_ok(request): return RedirectResponse('/admin/login',303)
    c=db(); rows=c.execute('SELECT * FROM enquiries ORDER BY id DESC LIMIT 100').fetchall(); c.close()
    items=''.join(f'<tr><td>{r["created_at"]}</td><td>{r["name"]}</td><td>{r["email"]}</td><td>{r["service"]}</td><td>{r["details"]}</td></tr>' for r in rows)
    return f'''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>DPS Admin</title><style>body{{font-family:Segoe UI;margin:0;background:#f5f8fc;color:#10233d}}header{{background:#061b32;color:white;padding:20px 5vw}}main{{max-width:1100px;margin:30px auto;padding:0 20px}}section{{background:white;padding:22px;border-radius:16px;margin-bottom:20px}}input,button{{padding:11px;border-radius:9px;border:1px solid #ccd8e5}}button{{background:#087cff;color:white;border:0;font-weight:700}}table{{width:100%;border-collapse:collapse;font-size:13px}}td,th{{padding:10px;border-bottom:1px solid #e3eaf2;text-align:left}}</style></head><body><header><b>Drone Pro Solution — Private Admin</b></header><main><section><h2>Upload Protected Sample Image</h2><p>Original stays in private storage. Public endpoint serves only the resized/watermarked preview.</p><form action="/api/admin/upload" method="post" enctype="multipart/form-data"><input name="title" placeholder="Project title" required><input name="category" placeholder="Category e.g. Railway" required><input type="file" name="file" accept="image/jpeg,image/png,image/webp" required><button>Upload Preview</button></form></section><section><h2>Recent Enquiries</h2><table><tr><th>Date</th><th>Name</th><th>Email</th><th>Service</th><th>Details</th></tr>{items or '<tr><td colspan="5">No enquiries yet.</td></tr>'}</table></section></main></body></html>'''

@app.post('/api/admin/upload')
def upload(request:Request, title:str=Form(...), category:str=Form(...), file:UploadFile=File(...)):
    if not session_ok(request): raise HTTPException(401,'Login required')
    filename=safe_name(file.filename or '')
    original=ORIG/filename; preview=PREV/(Path(filename).stem+'.jpg')
    data=file.file.read()
    if len(data)>25*1024*1024: raise HTTPException(413,'Image too large (25MB max)')
    original.write_bytes(data)
    try: make_preview(original,preview)
    except Exception:
        original.unlink(missing_ok=True); raise HTTPException(400,'Invalid image')
    c=db(); c.execute('INSERT INTO gallery(title,category,filename,preview) VALUES(?,?,?,?)',(title,category,filename,preview.name)); c.commit(); c.close()
    return RedirectResponse('/admin',303)
