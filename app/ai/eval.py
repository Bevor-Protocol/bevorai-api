import os

import replicate
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.types import EvalBody

input_template = {
    "min_tokens": 512,
    "max_tokens": 3000,
    "system_prompt": (
        "You are a helpful assistant, specializing in smart contract auditing"
    ),
    "prompt_template": """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>

    {system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>

    {prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
    """,
}


async def stream_iterator(iterator):
    try:
        async for value in iterator:

            yield str(value).encode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def process_evaluation(data: EvalBody) -> StreamingResponse:
    contract = data.contract
    prompt = data.prompt

    if not contract or not prompt:
        raise HTTPException(status_code=400, detail="Must provide input")

    # Insert the code text into the audit prompt
    audit_prompt = prompt.replace("<{prompt}>", contract)

    input_data = {**input_template, "prompt": audit_prompt}
    try:
        # Initialize Replicate client
        client = replicate.Client(api_token=os.getenv("REPLICATE_API_KEY"))

        # Start the streaming prediction
        iterator = await client.async_stream(
            "meta/meta-llama-3-70b-instruct", input=input_data
        )

        return StreamingResponse(
            stream_iterator(iterator),
            media_type="text/event-stream",
            headers={"Access-Control-Allow-Origin": "app.certaik.xyz"},
        )

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
