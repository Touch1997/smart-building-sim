from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/")
def root():
    return FileResponse("static/index.html")


@router.get("/dashboard")
def page_main():
    return FileResponse("static/index.html")


@router.get("/dashboard/chiller")
def page_chiller():
    return FileResponse("static/chiller.html")


@router.get("/dashboard/air")
def page_air():
    return FileResponse("static/air.html")


@router.get("/dashboard/electrical")
def page_electrical():
    return FileResponse("static/electrical.html")
