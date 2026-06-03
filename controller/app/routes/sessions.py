from __future__ import annotations

import logging
from typing import Any

import asyncio
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
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

    @router.post("/sessions/{session_id}/speed-filter")
    async def speed_filter(session_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            await manager.get_session(session_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Unknown session") from None

        return {
            "success": True,
            "message": "Speed filter endpoint accepted. No action taken.",
        }

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

    @router.post("/sessions/{session_id}/bulk-fill")
    async def bulk_fill(
        session_id: str,
        payload: dict[str, Any],
        background_tasks: BackgroundTasks,
    ) -> dict[str, Any]:
        """
        Server-side bulk fill: runs the entire fill loop as a background task
        using the already-connected Playwright instance.
        """
        try:
            session = await manager.get_session(session_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Unknown session") from None

        blueprint = payload.get("blueprint", {})
        items = payload.get("items", [])
        global_fields = payload.get("global_fields", [])

        row_selector = blueprint.get("row_selector", "")
        input_selector = blueprint.get("input_selector", "")
        requires_click = blueprint.get("requires_click_to_edit", False)

        if not row_selector or not input_selector:
            raise HTTPException(status_code=400, detail="Blueprint must include row_selector and input_selector")
        if not items:
            raise HTTPException(status_code=400, detail="Items array is empty")

        # Initialize progress tracker in session metadata
        session.metadata["bulk_fill"] = {
            "status": "executing",
            "logs": ["🚀 Native bulk fill started"],
            "success_count": 0,
            "fail_count": 0,
            "total_count": len(items)
        }

        async def run_fill():
            page = session.page
            logs = session.metadata["bulk_fill"]["logs"]
            
            try:
                async with session.lock:
                    target_frame = page
                    rows = target_frame.locator(row_selector)
                    row_count = await rows.count()

                    # Self-heal / auto-traverse iframes if target rows are inside an iframe
                    for frame in page.frames:
                        try:
                            frame_rows = frame.locator(row_selector)
                            count = await frame_rows.count()
                            if count > row_count:
                                row_count = count
                                target_frame = frame
                                rows = frame_rows
                        except Exception:
                            pass

                    frame_name = target_frame.name or target_frame.url.split('/')[-1].split('?')[0] or "main"
                    logs.append(f"🔎 Found {row_count} rows matching {row_selector!r} in frame: {frame_name}")
                    
                    if row_count == 0:
                        session.metadata["bulk_fill"].update({
                            "status": "failed",
                            "fail_count": len(items),
                            "error": f"No rows found for selector: {row_selector}"
                        })
                        logs.append(f"❌ No rows found for selector: {row_selector}")
                        return

                    # Filter rows to only those that contain the input_selector to align index 1-to-1
                    filtered_rows = []
                    for idx in range(row_count):
                        row = rows.nth(idx)
                        if await row.locator(input_selector).count() > 0:
                            filtered_rows.append(row)
                    
                    row_count = len(filtered_rows)
                    logs.append(f"🎯 Filtered to {row_count} actual item rows containing selector {input_selector!r}")

                    if row_count == 0:
                        session.metadata["bulk_fill"].update({
                            "status": "failed",
                            "fail_count": len(items),
                            "error": f"No item rows found containing selector: {input_selector}"
                        })
                        logs.append(f"❌ No item rows found containing selector: {input_selector}")
                        return

                    # Map global fields to column indices
                    import re
                    global_field_mappings = {} # maps field_name to col_index
                    if global_fields:
                        headers_locator = target_frame.locator("th")
                        headers_count = await headers_locator.count()
                        headers_text = []
                        for h_idx in range(headers_count):
                            h_text = await headers_locator.nth(h_idx).inner_text()
                            headers_text.append(h_text.strip())
                            
                        logs.append(f"📋 Found table headers: {headers_text}")
                        
                        if not headers_text:
                            try:
                                first_row = target_frame.locator("tr").first
                                cells = first_row.locator("td")
                                for c_idx in range(await cells.count()):
                                    h_text = await cells.nth(c_idx).inner_text()
                                    headers_text.append(h_text.strip())
                                logs.append(f"📋 Fallback table headers: {headers_text}")
                            except Exception:
                                pass
                                
                        for gf in global_fields:
                            gf_name = gf.get("name", "")
                            gf_value = gf.get("value", "")
                            if not gf_name or not gf_value:
                                continue
                                
                            norm_gf = re.sub(r'[*•\s]', '', gf_name.lower())
                            matched_col_idx = -1
                            for col_idx, h_text in enumerate(headers_text):
                                norm_h = re.sub(r'[*•\s]', '', h_text.lower())
                                if norm_gf in norm_h or norm_h in norm_gf:
                                    matched_col_idx = col_idx
                                    break
                                    
                            if matched_col_idx != -1:
                                global_field_mappings[gf_name] = {
                                    "col_index": matched_col_idx,
                                    "value": gf_value
                                }
                                logs.append(f"🎯 Mapped global field {gf_name!r} to Column {matched_col_idx + 1} ({headers_text[matched_col_idx]!r})")
                            else:
                                logs.append(f"⚠️ Could not map global field {gf_name!r} to any table header.")

                    # Helper function to match codes strictly
                    import re
                    def is_code_match(label: str, ref: str) -> bool:
                        norm_label = "".join(label.lower().split())
                        norm_ref = "".join(ref.lower().split())
                        
                        if not norm_label or not norm_ref:
                            return False
                            
                        if norm_label == norm_ref:
                            return True
                            
                        # Extract structured serial number codes (e.g. "1.3", "1.3.2", "1-2")
                        label_codes = re.findall(r'\d+(?:[\.-]\d+)+', label)
                        ref_codes = re.findall(r'\d+(?:[\.-]\d+)+', ref)
                        
                        if label_codes and ref_codes:
                            for l_code in label_codes:
                                if l_code in ref_codes:
                                    return True
                            return False
                            
                        # Fallback: substring match with strict digit/dot boundary checks
                        idx = norm_ref.find(norm_label)
                        while idx != -1:
                            before_ok = True
                            if idx > 0:
                                char_before = norm_ref[idx - 1]
                                if char_before.isdigit() or char_before in '.-':
                                    before_ok = False
                            after_ok = True
                            if idx + len(norm_label) < len(norm_ref):
                                char_after = norm_ref[idx + len(norm_label)]
                                if char_after.isdigit() or char_after in '.-':
                                    after_ok = False
                                    
                            if before_ok and after_ok:
                                return True
                            idx = norm_ref.find(norm_label, idx + 1)
                        return False

                    # Build list of normalized references from page rows to anchor by item code/description
                    page_rows_info = []
                    for idx in range(row_count):
                        row = filtered_rows[idx]
                        ref_value = ""
                        
                        try:
                            # Try reading value of input fields (like ITEMREFNO or similar)
                            inputs = row.locator("input")
                            for k in range(await inputs.count()):
                                input_el = inputs.nth(k)
                                # Skip the price/rate input that we are targeted to fill
                                is_target_input = await input_el.evaluate(
                                    "(el, sel) => { try { return el.matches(sel) || (!el.readOnly && !el.disabled); } catch(e) { return !el.readOnly && !el.disabled; } }",
                                    arg=input_selector
                                )
                                if is_target_input:
                                    continue
                                
                                val = await input_el.input_value()
                                if val and val.strip():
                                    ref_value = val.strip()
                                    break
                        except Exception:
                            pass
                            
                        if not ref_value:
                            try:
                                # Get all td text cells and join them, skipping the first one if it's just the row index
                                cells = row.locator("td")
                                cell_texts = []
                                for c_idx in range(await cells.count()):
                                    cell_text = await cells.nth(c_idx).inner_text()
                                    cell_texts.append(cell_text.strip())
                                if cell_texts:
                                    if cell_texts[0].isdigit():
                                        ref_value = " ".join(cell_texts[1:])
                                    else:
                                        ref_value = " ".join(cell_texts)
                            except Exception:
                                pass

                        if not ref_value:
                            try:
                                ref_value = await row.inner_text()
                            except Exception:
                                pass
                                
                        if ref_value:
                            page_rows_info.append((row, ref_value))

                    attempted_count = 0
                    for i, item in enumerate(items):
                        label = item.get("label", f"Row {i + 1}")
                        value = item.get("value", "")

                        # Attempt to anchor BOQ item to the correct row on the page by serial number/code matching
                        matched_row = None
                        
                        for r, orig_ref in page_rows_info:
                            if is_code_match(label, orig_ref):
                                matched_row = r
                                logs.append(f"🎯 BOQ {label!r} -> Row {i+1} ({orig_ref.strip()[:40]}...)")
                                break

                        if not matched_row:
                            # Fallback to index-based mapping only if the items chunk size matches page row count
                            if len(items) == row_count and i < row_count:
                                matched_row = filtered_rows[i]
                                logs.append(f"⚠️ BOQ {label!r} fallback to index {i+1}")
                            else:
                                # If it's not found on the page, and we aren't doing index fallback,
                                # we just skip it (it's on a different page of the portal)
                                logs.append(f"⏭️ BOQ {label!r} not found on current page. Skipping.")
                                continue

                        attempted_count += 1
                        session.metadata["bulk_fill"]["total_count"] = attempted_count

                        try:
                            row = matched_row

                            # Log all input/textarea/select inside the first row to inspect layout structure
                            if attempted_count == 1:
                                try:
                                    all_inputs = row.locator("input, textarea, select")
                                    input_tags = []
                                    for idx in range(await all_inputs.count()):
                                        el = all_inputs.nth(idx)
                                        tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                                        type_attr = await el.evaluate("el => el.getAttribute('type') or ''")
                                        id_attr = await el.evaluate("el => el.getAttribute('id') or ''")
                                        class_attr = await el.evaluate("el => el.getAttribute('class') or ''")
                                        name_attr = await el.evaluate("el => el.getAttribute('name') or ''")
                                        readonly = await el.evaluate("el => el.hasAttribute('readonly')")
                                        input_tags.append(f"<{tag_name} type='{type_attr}' id='{id_attr}' class='{class_attr}' name='{name_attr}' readonly={readonly}>")
                                    logs.append(f"🔎 Row 1 inputs info: {', '.join(input_tags)}")
                                except Exception as log_ex:
                                    logs.append(f"⚠️ Failed to inspect row inputs: {log_ex}")

                            if requires_click:
                                await row.click(timeout=3000)
                                await asyncio.sleep(0.15)

                            # Find the input inside this row
                            input_el = row.locator(input_selector).first
                            input_count = await input_el.count()

                            if input_count > 0:
                                try:
                                    is_readonly = await input_el.evaluate("el => el.hasAttribute('readonly') or el.readOnly")
                                    if is_readonly:
                                        # Log all inputs in this row to inspect
                                        try:
                                            all_inputs = row.locator("input, textarea, select")
                                            input_tags = []
                                            for idx in range(await all_inputs.count()):
                                                el = all_inputs.nth(idx)
                                                tag_name = await el.evaluate("el => el.tagName.toLowerCase()")
                                                type_attr = await el.evaluate("el => el.getAttribute('type') or ''")
                                                id_attr = await el.evaluate("el => el.getAttribute('id') or ''")
                                                class_attr = await el.evaluate("el => el.getAttribute('class') or ''")
                                                name_attr = await el.evaluate("el => el.getAttribute('name') or ''")
                                                readonly = await el.evaluate("el => el.hasAttribute('readonly') or el.readOnly")
                                                input_tags.append(f"<{tag_name} type='{type_attr}' id='{id_attr}' class='{class_attr}' name='{name_attr}' readonly={readonly}>")
                                            logs.append(f"🔎 Row {i+1} inputs: {', '.join(input_tags)}")
                                        except Exception as log_err:
                                            logs.append(f"⚠️ Failed to log row inputs: {log_err}")

                                        editable_inputs = row.locator("input:not([readonly]):not([disabled]), textarea:not([readonly]):not([disabled])")
                                        if await editable_inputs.count() > 0:
                                            input_el = editable_inputs.first
                                            logs.append(f"🔄 Self-healed: targeted element was readonly, switched to editable input in row {i+1}")
                                except Exception:
                                    pass

                            if input_count == 0:
                                logs.append(f"⚠️ [{attempted_count}] Input not found in row for: {label}")
                                session.metadata["bulk_fill"]["fail_count"] += 1
                                continue

                            await input_el.scroll_into_view_if_needed(timeout=3000)
                            await input_el.click(timeout=3000)
                            await input_el.fill(value, timeout=3000)

                            # Fill global fields for this row
                            for gf_name, mapping in global_field_mappings.items():
                                col_idx = mapping["col_index"]
                                val = mapping["value"]
                                
                                cells = row.locator("td")
                                if col_idx < await cells.count():
                                    cell = cells.nth(col_idx)
                                    gf_input = cell.locator("input:not([readonly]):not([disabled]), textarea:not([readonly]):not([disabled]), select:not([readonly]):not([disabled])").first
                                    if await gf_input.count() > 0:
                                        await gf_input.scroll_into_view_if_needed(timeout=2000)
                                        await gf_input.click(timeout=2000)
                                        await gf_input.fill(val, timeout=2000)
                                    else:
                                        logs.append(f"   ⚠️ No editable input found in Column {col_idx + 1} for {gf_name!r}")

                            session.metadata["bulk_fill"]["success_count"] += 1
                            logs.append(f"✅ [{attempted_count}] {label} → {value}")

                        except Exception as row_err:
                            session.metadata["bulk_fill"]["fail_count"] += 1
                            logs.append(f"⚠️ [{attempted_count}] Failed {label}: {row_err}")

                        # Small yield to event loop
                        await asyncio.sleep(0.01)

                    logs.append(f"✅ Bulk fill done: {session.metadata['bulk_fill']['success_count']} ok, {session.metadata['bulk_fill']['fail_count']} failed out of {attempted_count}.")
                    session.metadata["bulk_fill"]["status"] = "completed"
                    if session.metadata["bulk_fill"]["fail_count"] == len(items):
                        session.metadata["bulk_fill"]["status"] = "failed"
                        session.metadata["bulk_fill"]["error"] = "All items failed to be filled. Please check selector mapping or portal state."
            except Exception as exc:
                logger.error("bulk-fill error for session %s: %s", session_id, exc)
                logs.append(f"❌ Bulk fill aborted: {exc}")
                session.metadata["bulk_fill"].update({
                    "status": "failed",
                    "error": str(exc)
                })

        background_tasks.add_task(run_fill)
        return {"status": "started", "message": "Bulk fill job started in background."}

    @router.websocket("/sessions/{session_id}/cdp")
    async def connect_raw_cdp_endpoint(websocket: WebSocket, session_id: str, token: str = ""):
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

        try:
            base_ws_url = await manager.runtime.resolve_browser_ws_endpoint()
        except Exception as e:
            logger.error("Failed to resolve browser ws endpoint: %s", e)
            await websocket.close(code=1011, reason="Failed to resolve browser ws endpoint")
            return

        import urllib.parse
        import httpx

        parsed = urllib.parse.urlparse(base_ws_url)
        hostname = parsed.hostname

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"http://{hostname}:9224/cdp-url", timeout=10.0)
                resp.raise_for_status()
                raw_cdp_ws_url = resp.text.strip()
                if not raw_cdp_ws_url:
                    raise Exception("Empty CDP URL returned")
                parsed_cdp = urllib.parse.urlparse(raw_cdp_ws_url)
                cdp_ws_url = parsed_cdp._replace(netloc=f"{hostname}:{parsed_cdp.port}").geturl()
        except Exception as e:
            logger.error("Failed to read CDP URL from port 9224: %s", e)
            await websocket.close(code=1011, reason="Failed to get CDP debugger URL")
            return

        forward_headers: dict[str, str] = {}
        user_agent = None
        subprotocols = None
        browser_name = None
        for k, v in websocket.headers.items():
            k_lower = k.lower()
            if k_lower == "user-agent":
                user_agent = v
            elif k_lower == "x-playwright-browser":
                browser_name = v
                forward_headers[k] = v
            elif k_lower == "sec-websocket-protocol":
                subprotocols = [p.strip() for p in v.split(",")]
            elif k_lower not in (
                "host",
                "connection",
                "upgrade",
                "sec-websocket-key",
                "sec-websocket-version",
                "sec-websocket-extensions",
            ):
                forward_headers[k] = v

        if browser_name and f"browserName={browser_name}" not in cdp_ws_url:
            sep = "&" if "?" in cdp_ws_url else "?"
            cdp_ws_url = f"{cdp_ws_url}{sep}browserName={browser_name}"

        session.gateway_attached = True
        logger.info("Session %s CDP gateway attached. Proxying to %s", session_id, cdp_ws_url)

        ws_kwargs = {
            "ping_interval": 20,
            "ping_timeout": 10,
            "max_size": 2**24,
            "user_agent_header": user_agent,
            "subprotocols": subprotocols,
        }
        import websockets
        ws_version = getattr(websockets, "__version__", "0")
        if int(ws_version.split(".")[0]) >= 14:
            ws_kwargs["additional_headers"] = forward_headers
        else:
            ws_kwargs["extra_headers"] = forward_headers

        try:
            async with websockets.connect(cdp_ws_url, **ws_kwargs) as backend_ws:
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
                        logger.error("Error CDP client_to_backend: %s", e)

                async def backend_to_client():
                    try:
                        async for message in backend_ws:
                            if isinstance(message, str):
                                await websocket.send_text(message)
                            else:
                                await websocket.send_bytes(message)
                    except Exception as e:
                        logger.error("Error CDP backend_to_client: %s", e)

                client_task = asyncio.create_task(client_to_backend())
                backend_task = asyncio.create_task(backend_to_client())
                done, pending = await asyncio.wait(
                    [client_task, backend_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
        except Exception as e:
            logger.error("CDP WebSocket proxy error for session %s: %s", session_id, e)
        finally:
            session.gateway_attached = False
            logger.info("Session %s CDP gateway detached", session_id)
            try:
                await websocket.close(code=1000)
            except Exception:
                pass

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
        user_agent = None
        subprotocols = None
        browser_name = None
        for k, v in websocket.headers.items():
            k_lower = k.lower()
            if k_lower == 'user-agent':
                user_agent = v
            elif k_lower == 'x-playwright-browser':
                browser_name = v
                forward_headers[k] = v
            elif k_lower == 'sec-websocket-protocol':
                subprotocols = [p.strip() for p in v.split(',')]
            elif k_lower not in ("host", "connection", "upgrade", "sec-websocket-key", "sec-websocket-version", "sec-websocket-extensions"):
                forward_headers[k] = v

        # Force browserName into the query string as a fallback for header-stripping environments
        if browser_name and f"browserName={browser_name}" not in cdp_ws_url:
            sep = "&" if "?" in cdp_ws_url else "?"
            cdp_ws_url = f"{cdp_ws_url}{sep}browserName={browser_name}"

        session.gateway_attached = True
        logger.info("Session %s gateway attached. Proxying to %s", session_id, cdp_ws_url)

        # Handle version-specific kwargs for websockets library
        ws_kwargs = {
            "user_agent_header": user_agent,
            "subprotocols": subprotocols
        }
        
        import websockets
        ws_version = getattr(websockets, "__version__", "0")
        if int(ws_version.split(".")[0]) >= 14:
            ws_kwargs["additional_headers"] = forward_headers
        else:
            ws_kwargs["extra_headers"] = forward_headers

        try:
            async with websockets.connect(cdp_ws_url, **ws_kwargs) as backend_ws:
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
