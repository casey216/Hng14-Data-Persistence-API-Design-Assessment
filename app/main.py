from typing import Annotated

from fastapi import FastAPI, Body, HTTPException, Request, Depends, Query, Response
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import requests

from app.models import Profile
from app.db import get_db, Base, engine
from app.schemas import ProfileResponse, ExistingProfileResponse, AllProfileResponse, FilterParams


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail
        }
    )

@app.exception_handler(RequestValidationError)
async def custom_request_validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": exc.errors()[0].get("msg")
        }
    )


def get_age_group(age: int | None) -> str:
    if age is None:
        return "unknown"
    
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"

@app.post("/api/profiles", response_model=ProfileResponse | ExistingProfileResponse, status_code=201)
async def create_profile(*, name: str = Body(None, embed=True), db: Session = Depends(get_db), response: Response): 
    if name is None or name.strip() == "":
        raise HTTPException(status_code=400, detail="Missing or empty name")

    try:
        name = name.lower().strip()
        db_profile = db.query(Profile).filter(Profile.name == name).first()
        if db_profile:
            date_to_string = db_profile.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')
            db_profile.created_at = date_to_string
            response.status_code = 200
            return {
                "status": "success",
                "message": "Profile already exists",
                "data": jsonable_encoder(db_profile)
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upstream or server failure: {str(e)}"
        )

    
    try:
        genderize_data = requests.get(f"https://api.genderize.io/?name={name}").json()
        if genderize_data.get("gender") is None or genderize_data.get("count") == 0:
            raise HTTPException(status_code=502, detail="Genderize returned an invalid response")
        
        agify_data = requests.get(f"https://api.agify.io/?name={name}").json()
        if agify_data.get("age") is None:
            raise HTTPException(status_code=502, detail="Agify returned an invalid response")
        
        nationalize_data = requests.get(f"https://api.nationalize.io/?name={name}").json()
        if nationalize_data.get("country") is None:
            raise HTTPException(status_code=502, detail="Nationalize returned an invalid response")
           
    except Exception:
        raise HTTPException(status_code=502, detail="External API error")
    
    age = agify_data.get("age")
    age_group = get_age_group(age)

    country = nationalize_data.get("country")[0]
    
    db_profile_data = Profile(
        name=name,
        gender=genderize_data.get("gender"),
        gender_probability=round(genderize_data.get("probability"), 2),
        sample_size=genderize_data.get("count"),
        age=age,
        age_group=age_group,
        country_id=country.get("country_id"),
        country_probability=round(country.get("probability"), 2),
    )
       
    db.add(db_profile_data)
    db.commit()
    db.refresh(db_profile_data)

    date_to_string = db_profile_data.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')
    db_profile_data.created_at = date_to_string
      
    return {
        "status": "success",
        "data": db_profile_data
    }
        
    
@app.get("/api/profiles/{id}", status_code=200, response_model=ProfileResponse)
async def read_name(id: str, db: Session = Depends(get_db)):
    db_profile = db.query(Profile).filter(Profile.id == id).first()
    if not db_profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found"
        )
    date_to_string = db_profile.created_at.strftime('%Y-%m-%dT%H:%M:%SZ')
    db_profile.created_at = date_to_string
    
    return {
        "status": "success",
        "data": {
            **db_profile.__dict__,
        }
    }


@app.get("/api/profiles", status_code=200, response_model=AllProfileResponse)
async def read_all_names(
    filterparams: Annotated[FilterParams, Query()],
    db: Session = Depends(get_db)
):
    query = db.query(Profile)

    if filterparams.gender:
        query = query.filter(Profile.gender == filterparams.gender.lower())

    if filterparams.country_id:
        query = query.filter(Profile.country_id == filterparams.country_id.upper())

    if filterparams.age_group:
        query = query.filter(Profile.age_group == filterparams.age_group.lower())

    db_profile_all = query.all()

    return {
        "status": "success",
        "count": len(db_profile_all),
        "data": [
            { **db_profile.__dict__, "created_at": db_profile.created_at.strftime('%Y-%m-%dT%H:%M:%SZ') }
            for db_profile in db_profile_all
        ]
    }

@app.delete("/api/profiles/{id}", status_code=204)
async def delete_name(id: str, db: Session = Depends(get_db)):
    db_profile = db.query(Profile).filter(Profile.id == id).first()
    if not db_profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found"
        )
    db.delete(db_profile)
    db.commit()


if __name__=="__main__":
    import uvicorn

    uvicorn.run(app=app, host="0.0.0.0", port=8080)