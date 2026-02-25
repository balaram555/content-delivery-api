import boto3
import os
from dotenv import load_dotenv

load_dotenv()

s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("S3_ENDPOINT"),
    aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
)

BUCKET = os.getenv("S3_BUCKET")

def create_bucket():
    try:
        s3.create_bucket(Bucket=BUCKET)
    except:
        pass