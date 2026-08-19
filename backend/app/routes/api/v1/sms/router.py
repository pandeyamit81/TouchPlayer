"""SMS API routes for the hidden cellular menu."""
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from app.services.sms import (
    ALLOWED_SMS_NUMBERS,
    delete_all_sms_messages,
    delete_sms_message,
    get_sms_network_status,
    read_sms_messages,
    restart_sms_network,
    send_sms_message,
)

router = APIRouter()


class SMSRequest(BaseModel):
    number: str = Field(min_length=6, max_length=24)
    text: str = Field(min_length=1, max_length=1600)


@router.get("/sms/network")
async def get_sms_network():
    try:
        return await get_sms_network_status()
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Unable to check cellular network: {error}") from error


@router.post("/sms/network/restart")
async def restart_sms_network_service():
    try:
        return {"success": True, **await restart_sms_network()}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Unable to restart cellular network: {error}") from error


@router.get("/sms/messages")
async def get_sms_messages():
    try:
        return {"messages": await read_sms_messages()}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Unable to read SMS messages: {error}") from error


@router.delete("/sms/messages/{message_id}")
async def delete_one_sms_message(message_id: int = Path()):
    try:
        await delete_sms_message(message_id)
        return {"success": True, "id": message_id}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Unable to delete SMS message: {error}") from error


@router.delete("/sms/messages")
async def delete_all_sms():
    try:
        await delete_all_sms_messages()
        return {"success": True}
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Unable to delete SMS messages: {error}") from error


@router.post("/sms/messages")
async def post_sms_message(request: SMSRequest):
    try:
        normalized_number = "".join(character for character in request.number if character.isdigit())
        if normalized_number.startswith("91") and len(normalized_number) == 12:
            normalized_number = normalized_number[2:]
        if normalized_number not in ALLOWED_SMS_NUMBERS:
            raise HTTPException(status_code=400, detail="SMS recipient is not in the approved contact list")
        result = await send_sms_message(normalized_number, request.text)
        return {"success": True, **result}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail=f"Unable to send SMS: {error}") from error
