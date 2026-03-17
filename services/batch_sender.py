
import asyncio
import polars as pl
from services.template_service import render_template
from services.email_service import send_email


async def send_bulk_emails(
    template_str: str,
    users_df: pl.DataFrame,
    concurrency: int = 10,
    batch_size: int = 50,
    queue: asyncio.Queue | None = None,
):
    semaphore = asyncio.Semaphore(concurrency)
    total = len(users_df)
    success_count = 0
    failed_count = 0
    all_results = []

    async def send_one(user: dict) -> dict:
        async with semaphore:
            try:
                if not user.get("email"):
                    raise ValueError("Missing 'email' field")
                if not user.get("subject"):
                    raise ValueError("Missing 'subject' field")
                html = render_template(template_str, user)
                await send_email(
                    to_email=user["email"],
                    subject=user["subject"],
                    html_content=html,
                )
                return {"email": user["email"], "status": "success"}
            except Exception as e:
                return {
                    "email": user.get("email", "unknown"),
                    "status": "failed",
                    "error": str(e),
                }

    try:
        for i in range(0, total, batch_size):
            chunk = users_df.slice(i, batch_size).to_dicts()
            tasks = [send_one(u) for u in chunk]
            chunk_results = await asyncio.gather(*tasks)

            for result in chunk_results:
                all_results.append(result)
                if result["status"] == "success":
                    success_count += 1
                else:
                    failed_count += 1

                if queue is not None:
                    event = {
                        "type": "progress",
                        "email": result["email"],
                        "status": result["status"],
                        "success": success_count,
                        "failed": failed_count,
                        "total": total,
                    }
                    if "error" in result:
                        event["error"] = result["error"]
                    await queue.put(event)

        if queue is not None:
            await queue.put({
                "type": "complete",
                "success": success_count,
                "failed": failed_count,
                "total": total,
            })

    except Exception as exc:
        if queue is not None:
            await queue.put({"type": "error", "detail": str(exc)})
        raise

    return all_results
