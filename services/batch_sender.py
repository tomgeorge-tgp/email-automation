
import asyncio
from services.template_service import render_template
from services.email_service import send_email

import polars as pl

async def send_bulk_emails(
    template_str: str,
    users_df: pl.DataFrame,
    concurrency: int = 10,
    batch_size: int = 50
):
    semaphore = asyncio.Semaphore(concurrency)
    all_results = []

    # Process in chunks to save memory
    total_rows = len(users_df)
    
    # Inner function to send one email (same logic as before)
    async def send_one(user):
        async with semaphore:
            try:
                html = render_template(template_str, user)
                
                if not user.get("email"):
                    raise ValueError("Missing 'email' field in user record")

                if not user.get("subject"):
                    raise ValueError("Missing 'subject' field in user record")

                await send_email(
                    to_email=user["email"],
                    subject=user["subject"],
                    html_content=html
                )

                return {
                    "email": user["email"],
                    "status": "success"
                }

            except Exception as e:
                return {
                    "email": user.get("email", "unknown"),
                    "status": "failed",
                    "error": str(e)
                }

    # Loop through the DataFrame in batches
    for i in range(0, total_rows, batch_size):
        # Slice the Polars DataFrame efficiently
        # .slice(offset, length) is zero-copy in Polars until we convert to python objects
        chunk_df = users_df.slice(i, batch_size)
        
        # Convert only this chunk to list of dicts for Python processing
        chunk_users = chunk_df.to_dicts()
        
        # Create tasks for this chunk
        tasks = [send_one(user) for user in chunk_users]
        
        # Run this chunk
        chunk_results = await asyncio.gather(*tasks)
        all_results.extend(chunk_results)

    return all_results
