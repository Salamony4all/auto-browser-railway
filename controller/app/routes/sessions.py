from __future__ import annotations

import logging
from typing import Any

import asyncio
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
import websockets

from ..approvals import ApprovalRequiredError
from ..models import (
    ClickRequest,
    CreateSessionRequest,
    ExecuteActionRequest,
    HoverRequest,
    HumanTakeoverRequest,
    NavigateRequest,
    ObserveRequest,
    OpenTabRequest,
    PressRequest,
    ScreenshotRequest,
    ScrollRequest,
    SelectOptionRequest,
    TabIndexRequest,
    TypeRequest,
    UploadRequest,
    WaitRequest,
)
from ._utils import internal_error

logger = logging.getLogger(__name__)


def create_sessions_router(*, manager: Any) -> APIRouter:
    router = APIRouter()

    @router.get("/sessions")
    async def list_sessions() -> list[dict[str, Any]]:
        return await manager.list_sessions()

    @router.post("/sessions")
    async def create_session(payload: CreateSessionRequest) -> dict[str, Any]:
        try:
            return await manager.create_session(
                name=payload.name,
                start_url=payload.start_url,
                storage_state_path=payload.storage_state_path,
                auth_profile=payload.auth_profile,
                memory_profile=payload.memory_profile,
                proxy_persona=payload.proxy_persona,
                request_proxy_server=payload.proxy_server,
                request_proxy_username=payload.proxy_username,
                request_proxy_password=payload.proxy_password,
                user_agent=payload.user_agent,
                protection_mode=payload.protection_mode,
                totp_secret=payload.totp_secret,
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request") from None
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Not found") from None
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except ApprovalRequiredError:
            raise
        except RuntimeError:
            raise HTTPException(status_code=409, detail="Conflict") from None
        except Exception:
            raise internal_error(logger, "create session failed") from None

    @router.get("/sessions/{session_id}")
    async def get_session(session_id: str) -> dict[str, Any]:
        return await manager.get_session_record(session_id)

    @router.get("/sessions/{session_id}/observe")
    async def observe(session_id: str, limit: int = 40, preset: str = "normal") -> dict[str, Any]:
        try:
            return await manager.observe(session_id, limit=limit, preset=preset)
        except KeyError:
            raise HTTPException(status_code=404, detail="Unknown session") from None
        except Exception:
            raise internal_error(logger, "observe failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/observe")
    async def observe_post(session_id: str, payload: ObserveRequest) -> dict[str, Any]:
        try:
            return await manager.observe(session_id, limit=payload.limit, preset=payload.preset)
        except KeyError:
            raise HTTPException(status_code=404, detail="Unknown session") from None
        except Exception:
            raise internal_error(logger, "observe failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/screenshot")
    async def capture_screenshot(session_id: str, payload: ScreenshotRequest) -> dict[str, Any]:
        return await manager.capture_screenshot(session_id, label=payload.label)

    @router.get("/sessions/{session_id}/downloads")
    async def list_downloads(session_id: str) -> list[dict[str, Any]]:
        return await manager.list_downloads(session_id)

    @router.get("/sessions/{session_id}/tabs")
    async def list_tabs(session_id: str) -> list[dict[str, Any]]:
        return await manager.list_tabs(session_id)

    @router.post("/sessions/{session_id}/tabs/activate")
    async def activate_tab(session_id: str, payload: TabIndexRequest) -> dict[str, Any]:
        try:
            return await manager.activate_tab(session_id, payload.index)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request") from None

    @router.post("/sessions/{session_id}/tabs/close")
    async def close_tab(session_id: str, payload: TabIndexRequest) -> dict[str, Any]:
        try:
            return await manager.close_tab(session_id, payload.index)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request") from None

    @router.post("/sessions/{session_id}/tabs/open")
    async def open_tab(session_id: str, payload: OpenTabRequest) -> dict[str, Any]:
        try:
            return await manager.open_tab(session_id, payload.url, payload.activate)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request") from None

    @router.post("/sessions/{session_id}/actions/navigate")
    async def navigate(session_id: str, payload: NavigateRequest) -> dict[str, Any]:
        try:
            return await manager.navigate(session_id, payload.url)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except ApprovalRequiredError:
            raise
        except Exception:
            raise internal_error(logger, "navigate failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/actions/click")
    async def click(session_id: str, payload: ClickRequest) -> dict[str, Any]:
        try:
            return await manager.click(
                session_id,
                selector=payload.selector,
                element_id=payload.element_id,
                x=payload.x,
                y=payload.y,
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request") from None
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except ApprovalRequiredError:
            raise
        except Exception:
            raise internal_error(logger, "click failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/actions/type")
    async def type_text(session_id: str, payload: TypeRequest) -> dict[str, Any]:
        try:
            return await manager.type(
                session_id,
                selector=payload.selector,
                element_id=payload.element_id,
                text=payload.text,
                clear_first=payload.clear_first,
                sensitive=payload.sensitive,
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request") from None
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except ApprovalRequiredError:
            raise
        except Exception:
            raise internal_error(logger, "type failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/actions/press")
    async def press_key(session_id: str, payload: PressRequest) -> dict[str, Any]:
        try:
            return await manager.press(session_id, payload.key)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except ApprovalRequiredError:
            raise
        except Exception:
            raise internal_error(logger, "press failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/actions/scroll")
    async def scroll(session_id: str, payload: ScrollRequest) -> dict[str, Any]:
        try:
            return await manager.scroll(session_id, payload.delta_x, payload.delta_y)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except Exception:
            raise internal_error(logger, "scroll failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/actions/execute")
    async def execute_action(session_id: str, payload: ExecuteActionRequest) -> dict[str, Any]:
        try:
            return await manager.execute_decision(
                session_id,
                payload.action,
                approval_id=payload.approval_id,
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request") from None
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except ApprovalRequiredError:
            raise
        except Exception:
            raise internal_error(logger, "execute action failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/actions/upload")
    async def upload(session_id: str, payload: UploadRequest) -> dict[str, Any]:
        try:
            return await manager.upload(
                session_id,
                selector=payload.selector,
                element_id=payload.element_id,
                file_path=payload.file_path,
                approved=payload.approved,
                approval_id=payload.approval_id,
            )
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Not found") from None
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except ApprovalRequiredError:
            raise
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request") from None
        except Exception:
            raise internal_error(logger, "upload failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/actions/hover")
    async def hover(session_id: str, payload: HoverRequest) -> dict[str, Any]:
        try:
            return await manager.hover(
                session_id,
                selector=payload.selector,
                element_id=payload.element_id,
                x=payload.x,
                y=payload.y,
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request") from None
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except ApprovalRequiredError:
            raise
        except Exception:
            raise internal_error(logger, "hover failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/actions/select-option")
    async def select_option(session_id: str, payload: SelectOptionRequest) -> dict[str, Any]:
        try:
            return await manager.select_option(
                session_id,
                selector=payload.selector,
                element_id=payload.element_id,
                value=payload.value,
                label=payload.label,
                index=payload.index,
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid request") from None
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except ApprovalRequiredError:
            raise
        except Exception:
            raise internal_error(logger, "select option failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/actions/wait")
    async def wait(session_id: str, payload: WaitRequest) -> dict[str, Any]:
        try:
            return await manager.wait(session_id, payload.wait_ms)
        except KeyError:
            raise HTTPException(status_code=404, detail="Unknown session") from None
        except Exception:
            raise internal_error(logger, "wait failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/actions/reload")
    async def reload(session_id: str) -> dict[str, Any]:
        try:
            return await manager.reload(session_id)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except ApprovalRequiredError:
            raise
        except Exception:
            raise internal_error(logger, "reload failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/actions/go-back")
    async def go_back(session_id: str) -> dict[str, Any]:
        try:
            return await manager.go_back(session_id)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except ApprovalRequiredError:
            raise
        except Exception:
            raise internal_error(logger, "go back failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/actions/go-forward")
    async def go_forward(session_id: str) -> dict[str, Any]:
        try:
            return await manager.go_forward(session_id)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Not permitted") from None
        except ApprovalRequiredError:
            raise
        except Exception:
            raise internal_error(logger, "go forward failed for session %s", session_id) from None

    @router.post("/sessions/{session_id}/takeover")
    async def request_human_takeover(session_id: str, payload: HumanTakeoverRequest) -> dict[str, Any]:
        return await manager.request_human_takeover(session_id, payload.reason)

    @router.delete("/sessions/{session_id}")
    async def close_session(session_id: str) -> dict[str, Any]:
        return await manager.close_session(session_id)

    @router.post("/sessions/{session_id}/fork")
    async def fork_session(session_id: str, name: str | None = None, start_url: str | None = None) -> dict[str, Any]:
        try:
            return await manager.fork_session(session_id, name=name, start_url=start_url)
        except RuntimeError:
            raise HTTPException(status_code=409, detail="Conflict") from None

    @router.websocket("/sessions/{session_id}/connect")
    async def connect_cdp(websocket: WebSocket, session_id: str, token: str = ""):
        await websocket.accept()
        
        expected_token = manager.settings.browser_gateway_token
        if expected_token and token != expected_token:
            await websocket.close(code=1008, reason="Invalid token")
            return

        try:
            session = await manager.get_session(session_id)
        except KeyError:
            await websocket.close(code=1004, reason="Session not found")
            return

        if session.runtime and session.runtime.ws_endpoint:
            cdp_ws_url = session.runtime.ws_endpoint
        else:
            try:
                cdp_ws_url = await manager.runtime.resolve_browser_ws_endpoint()
            except Exception as e:
                logger.error("Failed to resolve browser ws endpoint: %s", e)
                await websocket.close(code=1011, reason="Failed to resolve browser ws endpoint")
                return

        query_string = websocket.scope.get("query_string", b"").decode("utf-8")
        if query_string:
            sep = "&" if "?" in cdp_ws_url else "?"
            cdp_ws_url = f"{cdp_ws_url}{sep}{query_string}"

        forward_headers = {}
        for k, v in websocket.headers.items():
            if k.lower() not in ("host", "connection", "upgrade", "sec-websocket-key", "sec-websocket-version", "sec-websocket-extensions"):
                forward_headers[k] = v

        session.gateway_attached = True
        logger.info("Session %s gateway attached. Proxying to %s", session_id, cdp_ws_url)

        try:
            async with websockets.connect(cdp_ws_url, extra_headers=forward_headers) as backend_ws:
                async def client_to_backend():
                    try:
                        while True:
                            message = await websocket.receive()
                            if message["type"] == "websocket.receive":
                                if "text" in message and message["text"] is not None:
                                    await backend_ws.send(message["text"])
                                elif "bytes" in message and message["bytes"] is not None:
                                    await backend_ws.send(message["bytes"])
                            elif message["type"] == "websocket.disconnect":
                                break
                    except Exception as e:
                        logger.error("Error client_to_backend: %s", e)

                async def backend_to_client():
                    try:
                        async for message in backend_ws:
                            if isinstance(message, str):
                                await websocket.send_text(message)
                            else:
                                await websocket.send_bytes(message)
                    except Exception as e:
                        logger.error("Error backend_to_client: %s", e)

                client_task = asyncio.create_task(client_to_backend())
                backend_task = asyncio.create_task(backend_to_client())
                done, pending = await asyncio.wait(
                    [client_task, backend_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
        except Exception as e:
            logger.error("WebSocket proxy error for session %s: %s", session_id, e)
        finally:
            session.gateway_attached = False
            logger.info("Session %s gateway detached", session_id)
            try:
                await websocket.close(code=1000)
            except Exception:
                pass

    return router
