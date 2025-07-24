from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.services.chat_service import chat_service
from app.utils.response import success_response
import json
from app.schemas.chat import ChatMessageRequest

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/message")
async def send_message(message_request: ChatMessageRequest):
    try:
        session_id = message_request.session_id
        user_message = message_request.user_message
        result = await chat_service.process_message(session_id, user_message)
        return success_response(data=result, message="Message processed successfully")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/session")
async def create_chat_session():
    try:
        session_id = await chat_service.create_session()
        return success_response(data={"session_id": session_id}, message="Session created")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    try:
        history = await chat_service.get_chat_history(session_id)
        return success_response(data=history)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# WebSocket endpoint for real-time chat
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            result = await chat_service.process_message(
                session_id, message_data["message"]
            )
            await websocket.send_text(json.dumps({
                "type": "bot_response",
                "data": result
            }))
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Có lỗi xảy ra, vui lòng thử lại"
        }))