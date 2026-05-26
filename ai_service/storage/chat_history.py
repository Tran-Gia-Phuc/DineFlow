from storage.chat_history import get_token_usage, clear_history

@app.get("/chat/{session_id}/usage")
async def get_usage(
    session_id: str,
    api_key: str = Depends(verify_api_key),
):
    """Xem số token đã dùng của 1 session."""
    return await get_token_usage(session_id)


@app.delete("/chat/{session_id}")
async def delete_history(
    session_id: str,
    api_key: str = Depends(verify_api_key),
):
    """Xóa lịch sử chat của 1 session."""
    await clear_history(session_id)
    return {"success": True, "message": f"Đã xóa history của session {session_id}"}