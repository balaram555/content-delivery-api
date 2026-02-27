from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Response, Depends
from sqlalchemy.orm import Session
from uuid import uuid4, UUID
from datetime import datetime, timedelta, timezone
from email.utils import formatdate

from .database import Base, engine, get_db
from .models import Asset, AssetVersion, AccessToken
from .storage import s3, BUCKET, create_bucket
from .utils import generate_etag, generate_token

app = FastAPI()

Base.metadata.create_all(bind=engine)
create_bucket()

# =====================================
# UPLOAD ASSET
# =====================================
@app.post("/assets/upload", status_code=201)
async def upload_asset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    content = await file.read()
    etag = generate_etag(content)
    object_key = f"assets/{uuid4()}-{file.filename}"

    s3.put_object(
        Bucket=BUCKET,
        Key=object_key,
        Body=content,
        ContentType=file.content_type
    )

    asset = Asset(
        id=uuid4(),
        object_storage_key=object_key,
        filename=file.filename,
        mime_type=file.content_type,
        size_bytes=len(content),
        etag=etag,
        is_private=False
    )

    db.add(asset)
    db.commit()
    db.refresh(asset)

    return {
        "id": str(asset.id),
        "etag": etag
    }

# =====================================
# DOWNLOAD MUTABLE ASSET
# =====================================
@app.get("/assets/{asset_id}/download")
@app.head("/assets/{asset_id}/download")
def download_asset(
    asset_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):

    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404)

    last_modified_http = formatdate(
        asset.updated_at.timestamp(),
        usegmt=True
    )

    headers = {
        "ETag": asset.etag,
        "Last-Modified": last_modified_http,
        "Cache-Control": "public, s-maxage=3600, max-age=60"
    }

    if request.method == "HEAD":
        return Response(status_code=200, headers=headers)

    obj = s3.get_object(Bucket=BUCKET, Key=asset.object_storage_key)

    return Response(
        content=obj["Body"].read(),
        media_type=asset.mime_type,
        headers=headers
    )

# =====================================
# PUBLISH (Create Immutable Version)
# =====================================
@app.post("/assets/{asset_id}/publish")
def publish_asset(
    asset_id: UUID,
    db: Session = Depends(get_db)
):

    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404)

    version_id = uuid4()
    version_key = f"versions/{version_id}"

    s3.copy_object(
        Bucket=BUCKET,
        CopySource={"Bucket": BUCKET, "Key": asset.object_storage_key},
        Key=version_key
    )

    version = AssetVersion(
        id=version_id,
        asset_id=asset.id,
        object_storage_key=version_key,
        etag=asset.etag
    )

    db.add(version)
    db.commit()
    db.refresh(version)

    asset.current_version_id = version.id
    db.commit()

    return {"version_id": str(version.id)}

# =====================================
# PUBLIC IMMUTABLE VERSION
# =====================================
@app.api_route("/assets/public/{version_id}", methods=["GET", "HEAD"])
def get_public_version(
    version_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):

    version = db.query(AssetVersion).filter(
        AssetVersion.id == version_id
    ).first()

    if not version:
        raise HTTPException(status_code=404)

    asset = db.query(Asset).filter(
        Asset.id == version.asset_id
    ).first()

    if not asset:
        raise HTTPException(status_code=404)

    headers = {
        "ETag": version.etag,
        "Cache-Control": "public, max-age=31536000, immutable"
    }

    if request.method == "HEAD":
        return Response(status_code=200, headers=headers)

    obj = s3.get_object(
        Bucket=BUCKET,
        Key=version.object_storage_key
    )

    return Response(
        content=obj["Body"].read(),
        media_type=asset.mime_type,
        headers=headers
    )

# =====================================
# GENERATE PRIVATE TOKEN
# =====================================
@app.post("/assets/{asset_id}/generate-token")
def generate_access_token(
    asset_id: UUID,
    db: Session = Depends(get_db)
):

    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404)

    token_value = generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    token = AccessToken(
        token=token_value,
        asset_id=asset.id,
        expires_at=expires_at
    )

    db.add(token)
    db.commit()

    return {
        "token": token_value,
        "expires_at": expires_at.isoformat()
    }

# =====================================
# PRIVATE ASSET ACCESS
# =====================================
@app.get("/assets/private/{token}")
def private_asset(
    token: str,
    db: Session = Depends(get_db)
):

    access = db.query(AccessToken).filter(
        AccessToken.token == token
    ).first()

    if not access:
        raise HTTPException(status_code=401)

    if access.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=403)

    asset = db.query(Asset).filter(
        Asset.id == access.asset_id
    ).first()

    if not asset:
        raise HTTPException(status_code=404)

    obj = s3.get_object(
        Bucket=BUCKET,
        Key=asset.object_storage_key
    )

    headers = {
        "ETag": asset.etag,
        "Cache-Control": "private, no-store, no-cache, must-revalidate"
    }

    return Response(
        content=obj["Body"].read(),
        media_type=asset.mime_type,
        headers=headers
    )