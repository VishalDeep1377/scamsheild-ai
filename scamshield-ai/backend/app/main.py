from datetime import datetime, timezone
from io import BytesIO
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from reportlab.pdfgen import canvas
from app.config import settings
from app.database import Base, engine, get_db
from app.models import User, Scan, ScanEvidence, Feedback, ScamReport, LessonProgress
from app.schemas import RegisterIn, LoginIn, ScanMessageIn, ScanUrlIn, ScanEmailIn, BatchIn, FeedbackIn, ReportIn, StatusIn
from app.security import hash_password, verify_password, create_token, current_user, admin_user
from app.detection import analyze_text, analyze_url

Base.metadata.create_all(bind=engine)
app = FastAPI(title="ScamShield AI API", version="1.0.0", description="Explainable suspicious-message and URL analysis.")
origins = [x.strip() for x in settings.frontend_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

LESSONS = [
 {"id":"spot-urgency","title":"Recognize urgency and pressure","level":"Beginner","minutes":4,"body":"Scammers create artificial deadlines to stop you thinking. Pause and verify independently."},
 {"id":"protect-otp","title":"Protect OTPs, PINs and passwords","level":"Beginner","minutes":5,"body":"Never share authentication codes, passwords, PINs, or recovery codes with callers or message senders."},
 {"id":"inspect-links","title":"Inspect links safely","level":"Intermediate","minutes":6,"body":"Read the actual hostname carefully. Do not click a link to test it. Navigate using the official app or a saved bookmark."},
 {"id":"job-fraud","title":"Spot recruitment fee scams","level":"Intermediate","minutes":5,"body":"Be cautious of requests for registration, interview, training, or document processing fees. Verify the employer using independently sourced details."},
]
@app.get("/api/health")
def health():
    return {"status":"ok","service":"ScamShield AI API"}

def serialize_scan(scan):
    return {"id":scan.id,"input_type":scan.input_type,"input_text":scan.input_text,"risk_score":scan.risk_score,
            "risk_level":scan.risk_level,"category":scan.category,"prediction":scan.prediction,"confidence":scan.confidence,
            "created_at":scan.created_at.isoformat(),"evidence":[{"signal":e.signal,"severity":e.severity,"points":e.points,"explanation":e.explanation} for e in scan.evidence]}

def save_scan(db, user, input_type, input_text, result):
    scan = Scan(user_id=user.id,input_type=input_type,input_text=input_text,risk_score=result["risk_score"],
                risk_level=result["risk_level"],category=result["category"],prediction=result["prediction"],confidence=result["confidence"])
    db.add(scan); db.flush()
    for e in result["evidence"]:
        db.add(ScanEvidence(scan_id=scan.id,signal=e["signal"],severity=e["severity"],points=e["points"],explanation=e["explanation"]))
    db.commit(); db.refresh(scan)
    return scan

@app.post("/api/auth/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409,"An account with this email already exists.")
    user = User(name=data.name,email=email,password_hash=hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token":create_token(user.id),"token_type":"bearer","user":{"id":user.id,"name":user.name,"email":user.email,"role":user.role}}

@app.post("/api/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password,user.password_hash):
        raise HTTPException(401,"Incorrect email or password.")
    return {"access_token":create_token(user.id),"token_type":"bearer","user":{"id":user.id,"name":user.name,"email":user.email,"role":user.role}}

@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return {"id":user.id,"name":user.name,"email":user.email,"role":user.role}

@app.post("/api/scans/message")
def scan_message(data: ScanMessageIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    result = analyze_text(data.text)
    scan = save_scan(db,user,"message",data.text,result)
    return {**serialize_scan(scan),"actions":result["actions"],"urls":result["urls"],"model_available":result["model_available"]}

@app.post("/api/scans/url")
def scan_url(data: ScanUrlIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    parsed = analyze_url(data.url)
    result = analyze_text(data.url)
    result["evidence"] = [{"signal":s,"severity":sev,"points":pts,"explanation":exp} for s,sev,pts,exp in parsed["signals"]]
    result["risk_score"] = parsed["score"]
    result["risk_level"] = "Low" if parsed["score"] < 25 else "Medium" if parsed["score"] < 50 else "High" if parsed["score"] < 75 else "Critical"
    result["category"] = "url"
    result["prediction"] = "suspicious" if parsed["score"] >= 25 else "no strong indicators"
    scan = save_scan(db,user,"url",data.url,result)
    return {**serialize_scan(scan),"actions":result["actions"],"url_analysis":parsed}

@app.post("/api/scans/email")
def scan_email(data: ScanEmailIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    combined = f"Subject: {data.subject}\nFrom: {data.sender}\nReply-To: {data.reply_to}\n{data.body}\nAttachments: {' '.join(data.attachment_names)}"
    result = analyze_text(combined)
    ev = result["evidence"]
    if data.sender and data.reply_to and data.sender.lower().split("@")[-1] != data.reply_to.lower().split("@")[-1]:
        ev.append({"signal":"sender_reply_to_mismatch","severity":"high","points":20,"explanation":"Sender and reply-to domains differ. This can be legitimate, but should be verified."})
    risky_ext = {".exe",".scr",".js",".vbs",".bat",".cmd",".msi",".iso",".hta"}
    for name in data.attachment_names:
        if any(name.lower().endswith(ext) for ext in risky_ext):
            ev.append({"signal":"risky_attachment_extension","severity":"high","points":20,"explanation":f"Attachment filename {name!r} has an executable or script-like extension. The file was not opened."})
    result["risk_score"] = min(100,sum(e["points"] for e in ev))
    result["risk_level"] = "Low" if result["risk_score"] < 25 else "Medium" if result["risk_score"] < 50 else "High" if result["risk_score"] < 75 else "Critical"
    result["prediction"] = "suspicious" if result["risk_score"] >= 25 else "no strong indicators"
    scan = save_scan(db,user,"email",combined,result)
    return {**serialize_scan(scan),"actions":result["actions"],"model_available":result["model_available"]}

@app.post("/api/scans/batch")
def batch_scan(data: BatchIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    out=[]
    for message in data.messages:
        result=analyze_text(message)
        scan=save_scan(db,user,"message",message,result)
        out.append({"id":scan.id,"risk_score":scan.risk_score,"risk_level":scan.risk_level,"category":scan.category,"prediction":scan.prediction})
    return {"count":len(out),"results":out}

@app.get("/api/scans")
def list_scans(q: str = "", risk: str = "", limit: int = Query(50,ge=1,le=100), offset: int = Query(0,ge=0),
               db: Session = Depends(get_db), user: User = Depends(current_user)):
    query=db.query(Scan).options(joinedload(Scan.evidence)).filter(Scan.user_id==user.id)
    if q: query=query.filter(Scan.input_text.ilike(f"%{q[:100]}%"))
    if risk: query=query.filter(Scan.risk_level==risk)
    rows=query.order_by(desc(Scan.created_at)).offset(offset).limit(limit).all()
    return {"items":[serialize_scan(x) for x in rows],"limit":limit,"offset":offset}

@app.get("/api/scans/{scan_id}")
def scan_detail(scan_id:int,db:Session=Depends(get_db),user:User=Depends(current_user)):
    scan=db.query(Scan).options(joinedload(Scan.evidence)).filter(Scan.id==scan_id,Scan.user_id==user.id).first()
    if not scan: raise HTTPException(404,"Scan not found.")
    return serialize_scan(scan)

@app.get("/api/scans/{scan_id}/report")
def scan_report(scan_id:int,db:Session=Depends(get_db),user:User=Depends(current_user)):
    scan=db.query(Scan).options(joinedload(Scan.evidence)).filter(Scan.id==scan_id,Scan.user_id==user.id).first()
    if not scan: raise HTTPException(404,"Scan not found.")
    buf=BytesIO(); pdf=canvas.Canvas(buf)
    pdf.setTitle(f"ScamShield Scan {scan.id}")
    y=800
    for line in [f"SCAMSHIELD AI - SCAN REPORT #{scan.id}",f"Date: {scan.created_at.isoformat()}",f"Type: {scan.input_type}",f"Risk: {scan.risk_level} ({scan.risk_score}/100)",f"Category: {scan.category}","", "Submitted content:"]:
        pdf.drawString(50,y,line[:110]); y-=18
    for line in scan.input_text.splitlines():
        if y<100: pdf.showPage(); y=800
        pdf.drawString(50,y,line[:110]); y-=14
    y-=12; pdf.drawString(50,y,"Evidence:"); y-=18
    for e in scan.evidence:
        if y<100: pdf.showPage(); y=800
        pdf.drawString(50,y,f"- {e.signal} [{e.severity}, {e.points}]: {e.explanation}"[:115]); y-=16
    pdf.save(); buf.seek(0)
    return StreamingResponse(buf,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="scamshield-scan-{scan.id}.pdf"'})

@app.post("/api/scans/{scan_id}/feedback")
def feedback(scan_id:int,data:FeedbackIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    scan=db.query(Scan).filter(Scan.id==scan_id,Scan.user_id==user.id).first()
    if not scan: raise HTTPException(404,"Scan not found.")
    db.add(Feedback(scan_id=scan.id,user_id=user.id,verdict=data.verdict,comment=data.comment)); db.commit()
    return {"saved":True}

@app.get("/api/dashboard/summary")
def dashboard(db:Session=Depends(get_db),user:User=Depends(current_user)):
    total=db.query(func.count(Scan.id)).filter(Scan.user_id==user.id).scalar() or 0
    high=db.query(func.count(Scan.id)).filter(Scan.user_id==user.id,Scan.risk_score>=50).scalar() or 0
    avg=db.query(func.avg(Scan.risk_score)).filter(Scan.user_id==user.id).scalar()
    recent=db.query(Scan).filter(Scan.user_id==user.id).order_by(desc(Scan.created_at)).limit(5).all()
    by_category=db.query(Scan.category,func.count(Scan.id)).filter(Scan.user_id==user.id).group_by(Scan.category).all()
    return {"total_scans":total,"high_risk_scans":high,"average_risk":round(float(avg),1) if avg is not None else None,
            "recent":[{"id":s.id,"risk_score":s.risk_score,"risk_level":s.risk_level,"category":s.category,"input_type":s.input_type,"created_at":s.created_at.isoformat()} for s in recent],
            "categories":[{"category":c,"count":n} for c,n in by_category]}

@app.get("/api/academy/lessons")
def lessons(db:Session=Depends(get_db),user:User=Depends(current_user)):
    completed={x.lesson_id for x in db.query(LessonProgress).filter(LessonProgress.user_id==user.id).all()}
    return [{"id":x["id"],"title":x["title"],"level":x["level"],"minutes":x["minutes"],"body":x["body"],"completed":x["id"] in completed} for x in LESSONS]

@app.post("/api/academy/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id:str,db:Session=Depends(get_db),user:User=Depends(current_user)):
    if lesson_id not in {x["id"] for x in LESSONS}: raise HTTPException(404,"Lesson not found.")
    row=db.query(LessonProgress).filter(LessonProgress.user_id==user.id,LessonProgress.lesson_id==lesson_id).first()
    if not row: db.add(LessonProgress(user_id=user.id,lesson_id=lesson_id)); db.commit()
    return {"completed":True,"lesson_id":lesson_id}

@app.post("/api/reports")
def create_report(data:ReportIn,db:Session=Depends(get_db),user:User=Depends(current_user)):
    row=ScamReport(user_id=user.id,category=data.category,description=data.description)
    db.add(row); db.commit(); db.refresh(row)
    return {"id":row.id,"category":row.category,"status":row.status,"created_at":row.created_at.isoformat()}

@app.get("/api/reports")
def list_reports(db:Session=Depends(get_db),user:User=Depends(current_user)):
    rows=db.query(ScamReport).filter(ScamReport.user_id==user.id).order_by(desc(ScamReport.created_at)).all()
    return [{"id":x.id,"category":x.category,"description":x.description,"status":x.status,"created_at":x.created_at.isoformat()} for x in rows]

@app.get("/api/admin/reports")
def admin_reports(db:Session=Depends(get_db),admin:User=Depends(admin_user)):
    rows=db.query(ScamReport).order_by(desc(ScamReport.created_at)).limit(200).all()
    return [{"id":x.id,"user_id":x.user_id,"category":x.category,"description":x.description,"status":x.status,"created_at":x.created_at.isoformat()} for x in rows]

@app.patch("/api/reports/{report_id}/status")
def update_report(report_id:int,data:StatusIn,db:Session=Depends(get_db),admin:User=Depends(admin_user)):
    row=db.get(ScamReport,report_id)
    if not row: raise HTTPException(404,"Report not found.")
    row.status=data.status; db.commit()
    return {"id":row.id,"status":row.status}

@app.get("/api/admin/overview")
def admin_overview(db:Session=Depends(get_db),admin:User=Depends(admin_user)):
    return {"users":db.query(func.count(User.id)).scalar() or 0,
            "scans":db.query(func.count(Scan.id)).scalar() or 0,
            "reports":db.query(func.count(ScamReport.id)).scalar() or 0,
            "open_reports":db.query(func.count(ScamReport.id)).filter(ScamReport.status.in_(["submitted","reviewing"])).scalar() or 0}
