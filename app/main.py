from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Response
from .database import Base, engine, SessionLocal
from .models import Asset
from .utils import generate_etag
from .storage import s3, BUCKET, create_bucket
import uuid

app = FastAPI()

Base.metadata.create_all(bind=engine)
create_bucket()

@app.post("/assets/upload")
async def upload_asset(file: UploadFile = File(...)):

    content = await file.read()
    etag = generate_etag(content)
    key = f"assets/{uuid.uuid4()}-{file.filename}"

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=content,
        ContentType=file.content_type
    )

    db = SessionLocal()
    asset = Asset(
        object_storage_key=key,
        filename=file.filename,
        mime_type=file.content_type,
        size_bytes=len(content),
        etag=etag
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    db.close()

    return {"id": str(asset.id), "etag": etag}

@app.get("/assets/{asset_id}/download")
def download_asset(asset_id: str, request: Request):

    db = SessionLocal()
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    db.close()

    if not asset:
        raise HTTPException(status_code=404)

    if_none_match = request.headers.get("if-none-match")

    if if_none_match == asset.etag:
        return Response(status_code=304)

    obj = s3.get_object(Bucket=BUCKET, Key=asset.object_storage_key)

    headers = {
        "ETag": asset.etag,
        "Cache-Control": "public, max-age=60",
    }

    return Response(
        content=obj["Body"].read(),
        media_type=asset.mime_type,
        headers=headers
    )