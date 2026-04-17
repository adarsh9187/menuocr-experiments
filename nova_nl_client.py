from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import boto3
from dotenv import load_dotenv
from pdf2image import convert_from_path
from PIL import Image

from nova_prompt_builder import build_nova_extraction_prompt


DEFAULT_NOVA_MODEL_ID = os.getenv(
    "NOVA_MODEL_ID",
    "arn:aws:bedrock:ap-south-1:073017371217:inference-profile/apac.amazon.nova-pro-v1:0",
)


def load_images(file_path: Path) -> List[Image.Image]:
    if file_path.suffix.lower() == ".pdf":
        return convert_from_path(str(file_path))
    return [Image.open(file_path)]


def _image_to_base64_png(image: Image.Image) -> str:
    rgb_image = image.convert("RGB")
    buffered = io.BytesIO()
    rgb_image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def _extract_json_object(text: str) -> Dict[str, Any]:
    json_start = text.find("{")
    json_end = text.rfind("}") + 1
    if json_start == -1 or json_end <= json_start:
        raise ValueError(f"No JSON object found in model response: {text[:500]}")
    return json.loads(text[json_start:json_end])


class NovaNLClient:
    def __init__(self, *, env_path: Path):
        load_dotenv(env_path)
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "ap-south-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        self.model_id = os.getenv("NOVA_MODEL_ID", DEFAULT_NOVA_MODEL_ID)

    def extract_menu(
        self,
        *,
        input_path: Path,
        schema_path: Path,
        prompt_path: Path,
        max_new_tokens: int = 8192,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        images = load_images(input_path)
        if not images:
            raise ValueError(f"No images could be loaded from {input_path}")

        prompt_text = build_nova_extraction_prompt(
            schema_path=schema_path,
            prompt_path=prompt_path,
        )

        content: List[Dict[str, Any]] = []
        for image in images:
            content.append(
                {
                    "image": {
                        "format": "png",
                        "source": {
                            "bytes": _image_to_base64_png(image),
                        },
                    }
                }
            )
        content.append({"text": prompt_text})

        body = json.dumps(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
                "inferenceConfig": {
                    "max_new_tokens": max_new_tokens,
                    "temperature": temperature,
                },
            }
        )

        response = self.client.invoke_model(
            body=body,
            modelId=self.model_id,
            accept="application/json",
            contentType="application/json",
        )
        response_body = json.loads(response.get("body").read())
        content_items = response_body["output"]["message"]["content"]
        text_parts = [item.get("text", "") for item in content_items if isinstance(item, dict)]
        raw_text = "\n".join(part for part in text_parts if part).strip()
        extracted = _extract_json_object(raw_text)
        return {
            "raw_response_text": raw_text,
            "extracted": extracted,
            "page_count": len(images),
            "model_id": self.model_id,
        }
